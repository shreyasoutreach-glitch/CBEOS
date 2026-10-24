"""Demo bootstrap and view renderer smoke test using synthetic data only."""
import os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
TMP=tempfile.TemporaryDirectory(prefix='cbeos-render-')
os.environ['CBAM_DB_PATH']=str(Path(TMP.name)/'render.db');os.environ['CBAM_ADMIN_EMAIL']='render@example.test';os.environ['CBAM_ADMIN_PASSWORD']='test-only-password'
from app import db as dbm,engine,views
class DemoRenderTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):dbm.init();cls.c=dbm.db();cls.tid=cls.c.execute('SELECT id FROM tenants LIMIT 1').fetchone()['id'];cls.uid=cls.c.execute('SELECT id FROM users LIMIT 1').fetchone()['id'];cls.t=cls.c.execute('SELECT * FROM users WHERE id=?',(cls.uid,)).fetchone();cls.actor=dict(cls.t)
 @classmethod
 def tearDownClass(cls):cls.c.close();TMP.cleanup()
 def test_dashboard_and_case_views_render(self):
  t=__import__('app.util',fromlist=['now']).now();self.c.execute('INSERT INTO cases(tenant_id,company,case_name,period,sector,status,created,updated) VALUES(?,?,?,?,?,?,?,?)',(self.tid,'Synthetic Metals GmbH','Synthetic Demo Case','2026','iron_steel','working',t,t));cid=self.c.execute('SELECT last_insert_rowid()').fetchone()[0];case=self.c.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone();engine.sync_requirements(self.c,self.tid,cid)
  self.assertIn('Control Tower',views.dashboard(self.c,self.actor));dashboard=views.dashboard(self.c,self.actor);self.assertIn('Sandbox mode',dashboard);self.assertIn('Client outcome view',dashboard);self.assertIn('href="/cases"',dashboard);self.assertIn('href="/suppliers"',dashboard);self.assertIn('href="/exceptions"',dashboard);self.assertIn('href="/verification"',dashboard);self.assertIn('not a legal liability or filing figure',dashboard);self.assertIn('Synthetic Demo Case',views.case_detail(self.c,self.actor,case,'csrf-test'));self.assertIn('Operational workspaces',views.case_list(self.c,self.actor));self.assertIn('Regulatory source governance',views.sources_view(self.c,self.actor));self.assertIn('Append-only, hash-chained',views.audit_view(self.c,self.actor))
if __name__=='__main__':unittest.main(verbosity=2)
