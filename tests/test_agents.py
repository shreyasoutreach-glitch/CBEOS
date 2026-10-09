"""Agent workflow persistence, tenant boundaries and safety tests."""
import hashlib, json, os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
TMP=tempfile.TemporaryDirectory(prefix='cbeos-agents-');os.environ['CBAM_DB_PATH']=str(Path(TMP.name)/'agents.db');os.environ['CBAM_ADMIN_EMAIL']='agents@example.test';os.environ['CBAM_ADMIN_PASSWORD']='test-not-production';os.environ.pop('CBAM_LLM_API_KEY',None);os.environ.pop('CBAM_LLM_MODEL',None)
from app import db as dbm,agents,engine,util
class AgentWorkflowTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):dbm.init()
 def setUp(self):
  self.c=dbm.db();self.tid=self.c.execute('SELECT id FROM tenants LIMIT 1').fetchone()[0];self.uid=self.c.execute('SELECT id FROM users WHERE tenant_id=? LIMIT 1',(self.tid,)).fetchone()[0];t=util.now();self.c.execute('INSERT INTO cases(tenant_id,company,case_name,period,sector,status,created,updated,notes) VALUES(?,?,?,?,?,?,?,?,?)',(self.tid,'Synthetic Importer','Agent Test Case','2026','iron_steel','working',t,t,''));self.cid=self.c.execute('SELECT last_insert_rowid()').fetchone()[0];engine.sync_requirements(self.c,self.tid,self.cid);self.c.commit()
 def tearDown(self):self.c.close()
 def test_model_is_off_by_default(self):self.assertFalse(agents.llm_configured())
 def test_retrieval_is_empty_without_curated_index(self):
  # Raw source corpus is deliberately not published. No synthetic citations may be invented.
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'knowledge').mkdir();idx=p/'knowledge'/'index.json';idx.write_text(json.dumps({'pages':[]}));man=p/'knowledge'/'manifest.json';man.write_text(json.dumps({'index_sha256':hashlib.sha256(idx.read_bytes()).hexdigest()}))
   with patch.object(agents,'ROOT',p),patch.object(agents,'INDEX_PATH',idx),patch.object(agents,'MANIFEST_PATH',man):self.assertEqual(agents.retrieve_sources('CBAM iron steel emissions',4),[])
 def test_workflow_persists_hash_chained_read_only_run(self):
  result=agents.run_case_workflow(self.c,self.tid,self.cid,self.uid);self.c.commit();self.assertEqual(result['summary']['status'],'COMPLETED');self.assertEqual(result['summary']['readiness']['verdict'],'BLOCKED');ok,where=agents.verify_message_chain(self.c,self.tid,self.cid,result['run_id']);self.assertTrue(ok,where);row=self.c.execute('SELECT status FROM agent_runs WHERE id=?',(result['run_id'],)).fetchone();self.assertEqual(row['status'],'COMPLETED');self.assertFalse(result['summary']['next_actions']==[])
 def test_unknown_case_is_rejected_for_other_tenant(self):
  self.c.execute('INSERT INTO tenants(name,slug,created) VALUES(?,?,?)',('Other','other-agent',util.now()));other=self.c.execute('SELECT last_insert_rowid()').fetchone()[0]
  with self.assertRaises(ValueError):agents.run_case_workflow(self.c,other,self.cid,self.uid)
if __name__=='__main__':unittest.main(verbosity=2)
