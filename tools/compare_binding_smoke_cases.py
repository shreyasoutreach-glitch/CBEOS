#!/usr/bin/env python3
"""Compare curated official-EUR-Lex smoke cases to staged workbooks. Not full reconciliation."""
import json,sys
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'staging'/'output'
cases=json.loads((ROOT/'staging'/'binding_annex_smoke_cases.json').read_text())
def load_jsonl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def norm(x):return ''.join(ch for ch in str(x) if ch.isdigit())
def d(x):return Decimal(str(x))
defs=load_jsonl(OUT/'default_values_staged.jsonl');bms=load_jsonl(OUT/'benchmarks_staged.jsonl');results=[]
for x in cases['default_cases']:
 matches=[r for r in defs if r['record_type']=='annex_i_default' and r.get('country')==x['country'] and r.get('sector')==x['sector'] and norm(r['code'])==x['code']];ok=len(matches)==1
 if ok:
  r=matches[0];ok=r['value_state']=='numeric' and d(r['total_tco2e_per_t'])==d(x['expected_total']) and r.get('route')==x['expected_route']
 results.append({'type':'default','case':x['code'],'passed':bool(ok),'matches':len(matches),'expected_total':x['expected_total'],'expected_route':x['expected_route']})
for x in cases['benchmark_cases']:
 matches=[r for r in bms if r.get('sector')==x['sector'] and norm(r['code'])==x['code'] and not r.get('is_continuation')];ok=len(matches)==1
 if ok:
  r=matches[0];ok=r['column_a_state']=='numeric' and r['column_b_state']=='numeric' and d(r['column_a_bmg_tco2e_per_t'])==d(x['expected_a']) and d(r['column_b_bmg_tco2e_per_t'])==d(x['expected_b'])
 results.append({'type':'benchmark','case':x['code'],'passed':bool(ok),'matches':len(matches),'expected_a':x['expected_a'],'expected_b':x['expected_b']})
report={'status':'PASS' if all(x['passed'] for x in results) else 'FAIL','passed':sum(x['passed'] for x in results),'total':len(results),'cases':results,'scope_note':'Curated spot checks only; full row-level legal reconciliation remains pending.'}
(OUT/'binding_annex_smoke_results.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if not all(x['passed'] for x in results):sys.exit(1)
