"""HTTP integration coverage. This suite exercises the actual server routes in-process."""
import http.client,json,os,re,sys,tempfile,threading,time,unittest
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import ThreadingHTTPServer
from app import db as dbm,util,security
from app.server import Handler
class IntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=tempfile.TemporaryDirectory(prefix='cbeos-integ-');dbm.DB_PATH=os.path.join(cls.root.name,'test.db');dbm.UP=os.path.join(cls.root.name,'uploads');os.makedirs(dbm.UP,exist_ok=True);os.environ['CBAM_ADMIN_PASSWORD']='integration-pass';dbm.init();cls.srv=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.port=cls.srv.server_address[1];cls.th=threading.Thread(target=cls.srv.serve_forever,daemon=True);cls.th.start();time.sleep(.05)
 @classmethod
 def tearDownClass(cls):cls.srv.shutdown();cls.srv.server_close();cls.root.cleanup()
 def req(self,method,path,body=None,cookie=None,headers=None,raw_body=None,content_type=None):
  conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=8);h=dict(headers or {});h.update({'Origin':f'http://127.0.0.1:{self.port}'})
  if cookie:h['Cookie']=cookie
  data=raw_body
  if body is not None:data='&'.join(f'{k}={__import__("urllib.parse",fromlist=["quote_plus"]).quote_plus(str(v))}' for k,v in body.items());h['Content-Type']='application/x-www-form-urlencoded'
  if content_type:h['Content-Type']=content_type
  conn.request(method,path,data,h);r=conn.getresponse();out=(r.status,dict(r.getheaders()),r.read().decode('utf-8','replace'));conn.close();return out
 def csrf(self,body):
  m=re.search(r'name="csrf" value="([^"]+)"',body);return m.group(1) if m else ''
 def login(self):
  security.clear_attempts('127.0.0.1:admin@example.com')
  s,h,b=self.req('POST','/login',{'email':'admin@example.com','password':'integration-pass'});self.assertEqual(s,303);return h['Set-Cookie'].split(';')[0]
 def test_health_login_security_headers_and_case_create(self):
  s,h,b=self.req('GET','/healthz');self.assertEqual((s,json.loads(b)),(200,{'ok':True}))
  s,h,b=self.req('GET','/readyz');self.assertEqual((s,json.loads(b)),(200,{'ready':True}))
  s,h,b=self.req('GET','/login');self.assertEqual(h.get('Cache-Control'),'no-store');self.assertIn("frame-ancestors 'none'",h.get('Content-Security-Policy',''))
  cookie=self.login();s,h,b=self.req('GET','/case/new',cookie=cookie);csrf=self.csrf(b);self.assertTrue(csrf)
  s,h,b=self.req('POST','/case/create',{'company':'Synthetic Metals','case_name':'INTEG-1','period':'2026','sector':'iron_steel','notes':'','csrf':csrf},cookie);self.assertEqual(s,303);cid=h['Location'].rsplit('/',1)[-1]
  s,h,b=self.req('GET',f'/case/{cid}',cookie=cookie);self.assertIn('INTEG-1',b);self.assertIn('csrf',b)
 def test_missing_csrf_rejected(self):
  cookie=self.login();s,h,b=self.req('POST','/case/create',{'company':'X','case_name':'Y','period':'2026','sector':'iron_steel','notes':''},cookie);self.assertEqual(s,403)
 def test_tenant_scoped_download_does_not_disclose_unknown_documents(self):
  cookie=self.login();s,h,b=self.req('GET','/document/999999/download',cookie=cookie);self.assertEqual(s,404)
 def test_login_lockout(self):
  for _ in range(8):self.req('POST','/login',{'email':'admin@example.com','password':'wrong-password'})
  s,h,b=self.req('POST','/login',{'email':'admin@example.com','password':'wrong-password'});self.assertEqual(s,429)
if __name__=='__main__':unittest.main(verbosity=2)
