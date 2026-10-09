#!/usr/bin/env python3
import importlib.util,sqlite3,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('db_operations',ROOT/'tools'/'db_operations.py');ops=importlib.util.module_from_spec(spec);spec.loader.exec_module(ops)
class DatabaseOperationsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.source=self.root/'source.db'
  c=sqlite3.connect(self.source);c.executescript('PRAGMA foreign_keys=ON; CREATE TABLE parent(id INTEGER PRIMARY KEY, name TEXT); CREATE TABLE child(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id)); INSERT INTO parent VALUES(1,"demo"); INSERT INTO child VALUES(1,1);');c.commit();c.close()
 def tearDown(self):self.tmp.cleanup()
 def test_online_backup_and_restore_roundtrip(self):
  backup=self.root/'backups'/'snapshot.db';manifest=ops.backup_database(self.source,backup);self.assertEqual(manifest['status'],'BACKUP_VERIFIED');self.assertEqual(ops.validate_database(backup)['integrity_check'],'ok')
  restored=self.root/'restored.db';result=ops.restore_database(backup,restored);self.assertEqual(result['status'],'RESTORE_VERIFIED');c=sqlite3.connect(restored);self.assertEqual(c.execute('SELECT name FROM parent WHERE id=1').fetchone()[0],'demo');self.assertEqual(c.execute('SELECT count(*) FROM child').fetchone()[0],1);c.close()
 def test_refuses_existing_backup_or_restore_target(self):
  backup=self.root/'snapshot.db';ops.backup_database(self.source,backup)
  with self.assertRaises(FileExistsError):ops.backup_database(self.source,backup)
  with self.assertRaises(FileExistsError):ops.restore_database(backup,self.source)
 def test_detects_corrupt_or_empty_file(self):
  bad=self.root/'bad.db';bad.write_bytes(b'not sqlite')
  with self.assertRaises((ValueError,sqlite3.Error)):ops.validate_database(bad)
 def test_foreign_key_violations_block_backup(self):
  bad=self.root/'fk.db';c=sqlite3.connect(bad);c.executescript('CREATE TABLE parent(id INTEGER PRIMARY KEY); CREATE TABLE child(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id)); INSERT INTO child VALUES(1,999);');c.commit();c.close()
  with self.assertRaises(ValueError):ops.backup_database(bad,self.root/'bad-backup.db')
  self.assertFalse((self.root/'bad-backup.db').exists())
if __name__=='__main__':unittest.main(verbosity=2)
