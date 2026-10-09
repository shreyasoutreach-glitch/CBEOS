"""Legal workbook parser, staged-data and rule-gate tests; source workbooks remain external."""
import sys, unittest
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from stage_cbam_workbooks import parse_decimal,value_state,normalize_code,stage_defaults,stage_benchmarks
from cbam_rules import markup_percent,calculate_default_total,choose_benchmark,ValidationBlocked
class ParserTests(unittest.TestCase):
 def test_decimal_comma_not_thousands(self):
  self.assertEqual(parse_decimal('0,870'),Decimal('0.870'));self.assertEqual(parse_decimal('1,300'),Decimal('1.300'));self.assertEqual(parse_decimal('1.234,56'),Decimal('1234.56'));self.assertEqual(parse_decimal('1,234.56'),Decimal('1234.56'))
 def test_dash_blank_parent_not_zero(self):
  self.assertEqual(value_state('-'),('fallback_required',None));self.assertEqual(value_state(None),('blank_review',None));self.assertEqual(value_state('see below'),('group_parent',None))
 def test_code_levels_preserved(self):
  self.assertEqual(normalize_code('3102'),'3102');self.assertEqual(normalize_code('7202 11'),'720211');self.assertEqual(normalize_code('2523 10 00 10'),'2523100010');self.assertIsNone(normalize_code('Cement'))
class SourceWorkbookTests(unittest.TestCase):
 def setUp(self):
  self.d=ROOT/'staging'/'DV correcting act_final update_06.08.xlsx';self.b=ROOT/'staging'/'CBAM Benchmarks_20260206.xlsx'
  if not self.d.exists() or not self.b.exists():self.skipTest('Source workbooks are supplied separately and are not committed to the public repository.')
 def test_default_workbook_staging_preserves_expected_structure(self):
  rows,meta=stage_defaults(self.d);annex1=[r for r in rows if r['record_type']=='annex_i_default'];annex4=[r for r in rows if r['record_type']=='annex_iv_precursor_default'];self.assertEqual(len(annex1),12540);self.assertEqual(len(annex4),283);self.assertEqual(sum(r['value_state']=='fallback_required' for r in annex1),760);self.assertEqual(sum(r['value_state']=='group_parent' for r in annex1),870);self.assertEqual(meta['status'],'staged_only_not_approved');self.assertTrue(all(r['approval_status']=='staged_unverified' for r in rows))
 def test_benchmark_continuations_preserved(self):
  rows,meta=stage_benchmarks(self.b);self.assertEqual(len(rows),1804);self.assertEqual(sum(r['is_continuation'] for r in rows),1234);self.assertTrue(all(r['code'] for r in rows));self.assertEqual(meta['status'],'staged_only_not_approved')
class RuleTests(unittest.TestCase):
 def test_markup_schedule_and_aliases(self):
  for s in ('cement','iron_steel','iron and steel','iron & steel','aluminium','hydrogen'):
   self.assertEqual(markup_percent(s,2026),Decimal('10'));self.assertEqual(markup_percent(s,2027),Decimal('20'));self.assertEqual(markup_percent(s,2028),Decimal('30'))
  for s in ('fertilisers','fertilizers'):
   for y in (2026,2027,2028,2035):self.assertEqual(markup_percent(s,y),Decimal('1'))
 def test_invalid_years_fail_closed(self):
  for y in (2025,0,-1,True,False,'2026',2026.0,None):
   with self.subTest(year=y),self.assertRaises(ValidationBlocked):markup_percent('cement',y)
 def test_unknown_sector_blocks(self):
  with self.assertRaises(ValidationBlocked):markup_percent('electricity',2026)
 def test_unapproved_row_blocks(self):
  row={'approval_status':'staged_unverified','value_state':'numeric','total_tco2e_per_t':'0.93','sector':'cement'}
  with self.assertRaises(ValidationBlocked):calculate_default_total(row,2026)
 def test_total_column_is_used_not_components(self):
  row={'approval_status':'approved','value_state':'numeric','total_tco2e_per_t':'0.93','direct_tco2e_per_t':'0.9','indirect_tco2e_per_t':'0.03','sector':'cement','source_sha256':'abc'}
  r=calculate_default_total(row,2026);self.assertEqual(r['marked_total_tco2e_per_t'],'1.023000');self.assertEqual(r['base_total_tco2e_per_t'],'0.93')
 def test_fallback_state_requires_reconciled_unique_candidate(self):
  row={'approval_status':'approved','value_state':'fallback_required','fallback_candidate_total':'1.23','fallback_source_country':'Other countries','fallback_candidate_unique':True,'sector':'cement','source_sha256':'abc'}
  self.assertEqual(calculate_default_total(row,2026)['marked_total_tco2e_per_t'],'1.353000');row['fallback_candidate_unique']=False
  with self.assertRaises(ValidationBlocked):calculate_default_total(row,2026)
 def test_benchmark_column_explicit_and_route_validated(self):
  row={'approval_status':'approved','column_a_state':'numeric','column_b_state':'numeric','column_a_bmg_tco2e_per_t':'0.666','column_b_bmg_tco2e_per_t':'0.859','column_a_route':'BF-BOF','column_b_route':'EAF','source_sha256':'abc'}
  self.assertEqual(choose_benchmark(row,'a','BF-BOF'),Decimal('0.666'))
  with self.assertRaises(ValidationBlocked):choose_benchmark(row,'b','BF-BOF')
if __name__=='__main__':unittest.main(verbosity=2)
