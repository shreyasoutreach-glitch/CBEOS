"""Adversarial authentication, CSRF, tenant-isolation and upload checks."""
import json, os, re, sys, tempfile, threading, unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
TMP=tempfile.TemporaryDirectory(prefix='cbeos-security-')
os.environ['CBAM_DB_PATH']=str(Path(TMP.name)/'security.db');os.environ['CBAM_ADMIN_EMAIL']='security@example.test';os.environ['CBAM_ADMIN_PASSWORD']='security-test-password'
from app import db as dbm,engine,security,util
from app.server import Handler
class SecurityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  dbm.init();cls.c=dbm.db();cls.tid=cls.c.execute('SELECT id FROM tenants LIMIT 1').fetchone()[0];cls.uid=cls.c.execute('SELECT id FROM users LIMIT 1').fetchone()[0];t=util.now();cls.c.execute("INSERT INTO tenants(name,slug,created) VALUES(?,?,?)",('Other tenant','other',t));cls.other=cls.c.execute('SELECT last_insert_rowid()').fetchone()[0];cls.c.execute("INSERT INTO users(tenant_id,email,password_hash,role,created) VALUES(?,?,?,?,?)",(cls.other,'other@example.test',security.password_hash('other-password'),'admin',t));cls.other_uid=cls.c.execute('SELECT last_insert_rowid()').fetchone()[0];cls.c.commit();cls.c.close();cls.srv=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.port=cls.srv.server_address[1];cls.thread=threading.Thread(target=cls.srv.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.srv.shutdown();cls.srv.server_close();TMP.cleanup()
 def req(self,method,path,body=None,cookie=None,raw=None,ctype=None,headers=None):
  import http.client,urllib.parse
  c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=8);h=dict(headers or {});h['Origin']=f'http://127.0.0.1:{self.port}'
  if cookie:h['Cookie']=cookie
  data=raw
  if body is not None:data=urllib.parse.urlencode(body);h['Content-Type']='application/x-www-form-urlencoded'
  if ctype:h['Content-Type']=ctype
  c.request(method,path,data,h);r=c.getresponse();out=(r.status,dict(r.getheaders()),r.read().decode('utf-8','replace'));c.close();return out
 def login(self,email='security@example.test',password='security-test-password'):
  security.clear_attempts(f'127.0.0.1:{email}')
  s,h,b=self.req('POST','/login',{'email':email,'password':password});self.assertEqual(s,303,b);return h['Set-Cookie'].split(';')[0]
 def csrf(self,body):
  m=re.search(r'name="csrf" value="([^"]+)"',body);return m.group(1) if m else ''
 def test_password_hash_uses_unique_salt_and_constant_time_compare(self):
  a=security.password_hash('secret');b=security.password_hash('secret');self.assertNotEqual(a,b);self.assertTrue(security.password_ok('secret',a));self.assertFalse(security.password_ok('wrong',a))
 def test_upload_scanner_rejects_spoof_and_executable(self):
  self.assertFalse(security.scan_upload('x.exe',b'MZ')[0]);self.assertFalse(security.scan_upload('invoice.pdf',b'MZnotpdf')[0]);self.assertFalse(security.scan_upload('invoice.pdf',b'%PDF- X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR')[0])
 def test_http_security_headers_and_health(self):
  s,h,b=self.req('GET','/healthz');self.assertEqual(s,200);self.assertEqual(json.loads(b),{'ok':True});self.assertEqual(h.get('Cache-Control'),'no-store');self.assertEqual(h.get('X-Frame-Options'),'DENY');self.assertIn("frame-ancestors 'none'",h.get('Content-Security-Policy',''))
 def test_missing_csrf_and_cross_tenant_ids_are_rejected(self):
  cookie=self.login();t=util.now();c=dbm.db();c.execute("INSERT INTO cases(tenant_id,company,case_name,period,sector,status,created,updated) VALUES(?,?,?,?,?,?,?,?)",(self.other,'Other','SECRET CASE','2026','steel','working',t,t));other_case=c.execute('SELECT last_insert_rowid()').fetchone()[0];c.commit();c.close()
  s,h,b=self.req('GET','/case/new',cookie=cookie);csrf=self.csrf(b);self.assertTrue(csrf)
  s,h,b=self.req('POST','/case/create',{'company':'bad','case_name':'bad','period':'2026','sector':'iron_steel'},cookie);self.assertEqual(s,403)
  s,h,b=self.req('GET',f'/case/{other_case}',cookie=cookie);self.assertEqual(s,404);self.assertNotIn('SECRET CASE',b)
  s,h,b=self.req('GET','/document/99999/download',cookie=cookie);self.assertEqual(s,404)
 def test_rate_limit_is_bounded(self):
  key='unit-test-key';security.clear_attempts(key)
  for _ in range(security.LOGIN_MAX_ATTEMPTS):security.record_attempt(key)
  self.assertTrue(security.rate_limited(key));security.clear_attempts(key);self.assertFalse(security.rate_limited(key))
if __name__=='__main__':unittest.main(verbosity=2)
