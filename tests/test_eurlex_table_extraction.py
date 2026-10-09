"""Regression tests for source-locator-preserving HTML table extraction."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from extract_eurlex_tables import extract,TableExtractor
class EurLexTableExtractionTests(unittest.TestCase):
 def test_table_rows_keep_source_locators_and_raw_cells(self):
  html='<html><table><tr><th>Country</th><th>CN code</th></tr><tr><td>Exampleland</td><td>7208 10 00</td></tr></table></html>'
  parser=TableExtractor();parser.feed(html)
  self.assertEqual(parser.table_no,1);self.assertEqual(len(parser.rows),2)
  self.assertEqual(parser.rows[1]['table_no'],1);self.assertEqual(parser.rows[1]['row_no'],2)
  self.assertEqual(parser.rows[1]['cells'],['Exampleland','7208 10 00'])
 def test_nested_tables_are_preserved_as_separate_locators(self):
  html='<table><tr><td>outer<table><tr><td>nested code</td></tr></table></td></tr></table>'
  parser=TableExtractor();parser.feed(html)
  self.assertEqual(parser.table_no,2)
  self.assertTrue(any(r['table_no']==2 and 'nested code' in r['cells'][0] for r in parser.rows))
 def test_extraction_manifest_never_approves_or_promotes(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);src=root/'input';out=root/'out';src.mkdir()
   (src/'official.html').write_text('<html><table><tr><td>row one</td></tr><tr><td>row two</td></tr></table></html>',encoding='utf-8')
   manifest=extract(src,out)
   self.assertEqual(manifest['status'],'EXTRACTED_UNREVIEWED');self.assertFalse(manifest['promotion_performed'])
   self.assertEqual(manifest['sources'][0]['table_rows_extracted'],2);self.assertEqual(manifest['sources'][0]['approval_status'],'NOT_APPROVED')
   rows=[json.loads(x) for x in (out/'official_tables.jsonl').read_text(encoding='utf-8').splitlines()]
   self.assertEqual([r['review_status'] for r in rows],['EXTRACTED_UNREVIEWED']*2)
   self.assertTrue(all(r['source_sha256'] for r in rows))
if __name__=='__main__':unittest.main(verbosity=2)
