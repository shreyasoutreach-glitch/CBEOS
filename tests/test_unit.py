"""Core deterministic unit regression suite."""
import json, os, sys, tempfile, unittest
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import db as dbm, engine, util

class UnitTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();dbm.DB_PATH=os.path.join(self.tmp.name,'test.db');dbm.UP=os.path.join(self.tmp.name,'uploads');os.makedirs(dbm.UP,exist_ok=True);dbm.init();self.c=dbm.db();self.tid=self.c.execute('SELECT id FROM tenants LIMIT 1').fetchone()['id'];self.uid=self.c.execute('SELECT id FROM users LIMIT 1').fetchone()['id'];t=util.now();self.c.execute("INSERT INTO cases(tenant_id,company,case_name,period,sector,status,created,updated) VALUES(?,?,?,?,?,?,?,?)",(self.tid,'Acme','CASE-001','2026','iron_steel','working',t,t));self.cid=self.c.execute('SELECT last_insert_rowid()').fetchone()[0]
 def tearDown(self):self.c.close();self.tmp.cleanup()
 def test_scoped_requirements_and_missing_evidence(self):
  sid=engine.create_supplier(self.c,self.tid,'Supplier A','India');iid=engine.create_installation(self.c,self.tid,sid,'Plant 1','India');lid=engine.create_import_line(self.c,self.tid,self.cid,supplier_id=sid,installation_id=iid,cn_code='72081000',quantity='10');engine.sync_requirements(self.c,self.tid,self.cid);scopes={r[0] for r in self.c.execute('SELECT DISTINCT scope_type FROM evidence_requirements WHERE case_id=?',(self.cid,))};self.assertEqual(scopes,{'case','supplier','installation','import_line'});self.assertGreater(len(engine.missing_requirements(self.c,self.tid,self.cid)),0)
  self.c.execute("INSERT INTO evidence(tenant_id,case_id,name,category,status,scope_type,scope_id,updated) VALUES(?,?,?,?,?,?,?,?)",(self.tid,self.cid,'Commercial invoice','commercial','complete','import_line',lid,util.now()));engine.sync_requirements(self.c,self.tid,self.cid);self.assertEqual(self.c.execute("SELECT status FROM evidence_requirements WHERE case_id=? AND name='Commercial invoice' AND scope_type='import_line' AND scope_id=?",(self.cid,lid)).fetchone()[0],'complete')
 def test_manual_scenario_and_input_snapshot(self):
  lid=engine.create_import_line(self.c,self.tid,self.cid,cn_code='72081000',quantity='100');self.c.execute("UPDATE cases SET period='2026-Q2' WHERE id=?",(self.cid,));result,err=engine.compute_import_line_calculation(self.c,self.tid,self.uid,self.cid,lid,{'specific_embedded_emissions':'2','free_allocation_adjustment':'20','carbon_price_credit_eur':'100'});self.assertIsNone(err);self.assertEqual(result['gross_embedded_emissions_tco2e'],'200.0000');self.assertEqual(result['net_after_free_allocation_tco2e'],'180.0000');self.assertEqual(result['status'],'SCENARIO_ONLY');row=self.c.execute('SELECT input_snapshot FROM calculation_runs WHERE import_line_id=?',(lid,)).fetchone();self.assertEqual(json.loads(row[0])['emissions_source']['type'],'manual_override')
 def test_nonofficial_default_blocks_calculation(self):
  lid=engine.create_import_line(self.c,self.tid,self.cid,cn_code='72081000',quantity='10');result,err=engine.compute_import_line_calculation(self.c,self.tid,self.uid,self.cid,lid,{});self.assertIsNone(result);self.assertIn('official dataset',err.lower())
 def test_invalid_calculations_do_not_persist(self):
  lid=engine.create_import_line(self.c,self.tid,self.cid,cn_code='72081000',quantity='10');before=self.c.execute('SELECT COUNT(*) FROM calculation_runs').fetchone()[0]
  for form in ({'quantity':'-10'},{'quantity':'0'},{'quantity':'NaN'},{'quantity':'10','specific_embedded_emissions':'NaN'},{'quantity':'10','free_allocation_adjustment':'999999'}):
   result,err=engine.compute_import_line_calculation(self.c,self.tid,self.uid,self.cid,lid,form);self.assertIsNone(result);self.assertTrue(err)
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM calculation_runs').fetchone()[0],before)
 def test_missing_actual_and_default_never_become_zero(self):
  lid=engine.create_import_line(self.c,self.tid,self.cid,cn_code='99999999',quantity='10');result,err=engine.compute_import_line_calculation(self.c,self.tid,self.uid,self.cid,lid,{});self.assertIsNone(result);self.assertIn('blocked',err.lower())
 def test_exception_state_machine_and_audit_chain(self):
  eid=engine.create_exception(self.c,self.tid,self.cid,'Test exception','general','high',detail='test');ok,_=engine.transition_exception(self.c,self.tid,eid,self.uid,'ACCEPTED_WITH_RISK',resolution='Risk accepted by reviewer');self.assertTrue(ok);self.assertEqual(self.c.execute('SELECT closed_by FROM exceptions WHERE id=?',(eid,)).fetchone()[0],self.uid);engine.audit(self.c,self.tid,self.cid,self.uid,'test_action','detail');self.c.commit();self.assertTrue(engine.verify_audit_chain(self.c,self.tid)[0])
 def test_verification_readiness_starts_blocked(self):
  sid=engine.create_supplier(self.c,self.tid,'Supplier A','India');iid=engine.create_installation(self.c,self.tid,sid,'Plant 1','India');rd=engine.verification_readiness(self.c,self.tid,iid);self.assertEqual(rd['status'],'NOT_READY');self.assertIn('Production route documented',[x[0] for x in rd['checklist'] if not x[1]])
if __name__=='__main__':unittest.main(verbosity=2)
