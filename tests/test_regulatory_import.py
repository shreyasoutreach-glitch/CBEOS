"""Sprint 1 guard tests: legacy workbook promotion must remain disabled."""
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
class RegulatoryPromotionGuardTests(unittest.TestCase):
 def test_importer_fails_closed_before_database_or_file_access(self):
  from app.regulatory_import import import_workbook,BLOCK_MESSAGE
  with self.assertRaisesRegex(RuntimeError,'promotion is disabled'): import_workbook('/this/path/does/not/need/to/exist.xlsx','test')
  self.assertIn('No database changes were made',BLOCK_MESSAGE)
 def test_legacy_cli_cannot_promote_workbooks(self):
  from app import regulatory_import
  with self.assertRaisesRegex(SystemExit,'promotion is disabled'): regulatory_import.main()
 def test_staging_pipeline_remains_separate_from_runtime_importer(self):
  from app import regulatory_import
  self.assertFalse(hasattr(regulatory_import,'activate_rule_set'));self.assertTrue(callable(regulatory_import.import_workbook))
if __name__=='__main__':unittest.main(verbosity=2)
