#!/usr/bin/env python3
"""Run offline golden retrieval evaluation."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.agents import retrieve_sources
def main():
 benchmark=json.loads((ROOT/'knowledge'/'retrieval_eval.json').read_text(encoding='utf-8'));cases=benchmark.get('cases',[])
 if not cases:print('FAIL: retrieval benchmark is empty');return 2
 failures=[]
 for item in cases:
  query=str(item['query']);expected=str(item['expected_filename']);results=retrieve_sources(query,top_k=4);names=[x['filename'] for x in results];passed=expected in names
  print(f"{'PASS' if passed else 'FAIL'} | {query} | expected={expected} | returned={names}")
  if not passed:failures.append(query)
 hit=(len(cases)-len(failures))/len(cases);print(f'RETRIEVAL_HIT_RATE_AT_4={hit:.1%} ({len(cases)-len(failures)}/{len(cases)})');return 1 if failures else 0
if __name__=='__main__':raise SystemExit(main())
