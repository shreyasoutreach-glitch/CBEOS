"""HTTP integration coverage. This suite exercises the actual server routes in-process."""
import http.client,json,os,re,sys,tempfile,threading,time,unittest
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import ThreadingHTTPServer
from app import db as dbm,util,security,engine,agents
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

 def test_seeded_case_provenance_exception_audit_and_agent_handoff(self):
  # Deterministic synthetic journey at the domain boundary: source document -> candidate fact
  # -> exception state transition -> verified audit chain -> persisted read-only agent hand-off.
  c=dbm.db()
  try:
   tenant=c.execute('SELECT id FROM tenants LIMIT 1').fetchone()['id']
   uid=c.execute('SELECT id FROM users WHERE tenant_id=? LIMIT 1',(tenant,)).fetchone()['id']
   t=util.now()
   c.execute("INSERT INTO cases(tenant_id,company,case_name,period,sector,status,created,updated,notes) VALUES(?,?,?,?,?,?,?,?,?)",
             (tenant,'Synthetic Metals','PROVENANCE-001','2026','iron_steel','working',t,t,'synthetic test only'))
   cid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
   lid=engine.create_import_line(c,tenant,cid,cn_code='72081000',quantity='10',invoice_ref='SYNTH-INV-001')
   payload=b'SYNTHETIC SUPPLIER DECLARATION: direct intensity 1.25 tCO2e/t'
   digest=util.sha256_bytes(payload)
   c.execute("INSERT INTO documents(tenant_id,case_id,import_line_id,filename,stored_name,mime,doc_type,size_bytes,sha256,uploaded,uploaded_by,extracted_text,meta_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
             (tenant,cid,lid,'synthetic-declaration.txt',digest+'.txt','text/plain','supplier_declaration',len(payload),digest,t,uid,payload.decode(),json.dumps({'synthetic':True})))
   did=c.execute('SELECT last_insert_rowid()').fetchone()[0]
   c.execute("INSERT INTO facts(tenant_id,case_id,document_id,import_line_id,field,value,numeric_value,unit,location,source_excerpt,confidence,status,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
             (tenant,cid,did,lid,'direct_intensity','1.25','1.25','tCO2e/t','line 1','direct intensity 1.25 tCO2e/t','high','candidate',t,t))
   fid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
   linked=c.execute("SELECT f.status,f.source_excerpt,f.location,d.sha256,d.filename FROM facts f JOIN documents d ON d.id=f.document_id WHERE f.id=? AND f.tenant_id=?",(fid,tenant)).fetchone()
   self.assertEqual(linked['status'],'candidate')
   self.assertIn('1.25',linked['source_excerpt'])
   self.assertEqual(linked['location'],'line 1')
   self.assertEqual(linked['sha256'],digest)
   self.assertEqual(linked['filename'],'synthetic-declaration.txt')
   eid=engine.create_exception(c,tenant,cid,'Candidate fact requires review','review_required','medium',
                               affected_entity_type='import_line',affected_entity_id=lid,
                               detail='Synthetic candidate must be human-reviewed.',source='test_fixture')
   ok,err=engine.transition_exception(c,tenant,eid,uid,'UNDER_REVIEW',resolution='Assigned to reviewer')
   self.assertTrue(ok,err)
   status=c.execute('SELECT status FROM exceptions WHERE id=? AND tenant_id=?',(eid,tenant)).fetchone()['status']
   self.assertEqual(status,'UNDER_REVIEW')
   handoff=agents.run_case_workflow(c,tenant,cid,uid)
   self.assertEqual(handoff['summary']['status'],'COMPLETED')
   self.assertEqual(handoff['summary']['readiness']['verdict'],'BLOCKED')
   self.assertTrue(agents.verify_message_chain(c,tenant,cid,handoff['run_id'])[0])
   actions=[r['action'] for r in c.execute('SELECT action FROM audit WHERE tenant_id=? AND case_id=?',(tenant,cid)).fetchall()]
   self.assertIn('exception_transition',actions)
   self.assertTrue(engine.verify_audit_chain(c,tenant)[0])
   # Tampering with a persisted audit payload must be detected, never reported as a valid chain.
   c.execute("UPDATE audit SET detail='tampered' WHERE tenant_id=? AND case_id=? AND action='exception_transition'",(tenant,cid))
   self.assertFalse(engine.verify_audit_chain(c,tenant)[0])
  finally:
   c.rollback()
   c.close()

if __name__=='__main__':unittest.main(verbosity=2)
