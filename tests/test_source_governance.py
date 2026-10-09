"""Guardrails for source hierarchy and release status."""
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SourceGovernanceTests(unittest.TestCase):
 def test_binding_source_hierarchy_mentions_corrective_act_and_separate_rules(self):
  doc=(ROOT/'docs'/'REGULATORY_SOURCE_HIERARCHY.md').read_text(encoding='utf-8')
  for marker in ('32026R1740','32025R2621','32025R2620','32025R2547'):self.assertIn(marker,doc)
  self.assertIn('informational purposes only',doc);self.assertIn('total emissions',doc);self.assertIn('staged_unverified',doc)
 def test_release_status_does_not_claim_deployment_or_legal_reconciliation(self):
  status=json.loads((ROOT/'RELEASE_STATUS.json').read_text(encoding='utf-8'))
  self.assertFalse(status['production_deployed']);self.assertTrue(status['github_published']);self.assertFalse(status['complete_source_tree_published']);self.assertFalse(status['legal_data_promoted'])
  self.assertFalse(status['full_binding_annex_reconciliation_complete']);self.assertFalse(status['antigravity_verification_complete'])
if __name__=='__main__':unittest.main(verbosity=2)
