"""Run all CBEOS test suites, fail non-zero if any suite fails."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITES = [
    'test_unit.py',
    'test_integration.py',
    'test_security.py',
    'test_regulatory_import.py',
    'test_agents.py',
    'test_provider_contract.py',
    'test_demo_render_regression.py',
    'test_dashboard_http_journey.py',
    'test_full_workflow_http.py',
    'test_render_runtime.py',
    'test_supplier_delivery.py',
    'test_legal_data_pipeline.py',
    'test_eurlex_table_extraction.py',
    'test_source_governance.py',
    'test_db_operations.py',
    'test_ops_readiness.py',
    'test_integration_probes.py',
    'test_recovery_report.py',
    'test_storage.py',
]
results = []
for suite in SUITES:
    print(f'\n===== {suite} =====', flush=True)
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([str(ROOT), str(ROOT/'tools'), env.get('PYTHONPATH','')])
    p = subprocess.run([sys.executable, str(ROOT/'tests'/suite)], cwd=ROOT, env=env)
    results.append((suite, p.returncode))
print('\n===== SUMMARY =====')
for suite, rc in results:
    print(f'{"PASS" if rc == 0 else "FAIL"} {suite} (exit {rc})')
raise SystemExit(1 if any(rc for _, rc in results) else 0)
