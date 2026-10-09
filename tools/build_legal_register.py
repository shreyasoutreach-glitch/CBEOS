#!/usr/bin/env python3
"""Build explicit legal authority register and per-row reconciliation queue."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'staging'/'output'
AUTHORITIES=[
 {'authority_id':'EU-2025-2621-CONS-2026-01-01','title':'Commission Implementing Regulation (EU) 2025/2621, consolidated 1 January 2026','celex':'02025R2621-20260101','url':'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02025R2621-20260101','scope':'Default values; Annexes I-IV','status':'official_consolidated_text; confirm authentic Official Journal text for legal sign-off'},
 {'authority_id':'EU-2026-1740','title':'Commission Implementing Regulation (EU) 2026/1740 correcting Annexes I and IV','celex':'32026R1740','url':'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32026R1740','scope':'Corrected Annex I defaults and Annex IV precursor defaults; applies from 2026-01-01','status':'binding_amending_act'},
 {'authority_id':'EU-2025-2620','title':'Commission Implementing Regulation (EU) 2025/2620 on CBAM benchmarks / SEFA','celex':'32025R2620','url':'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025R2620','scope':'CBAM benchmarks and free-allocation adjustment methodology','status':'binding_act; annex-level reconciliation required'},
 {'authority_id':'EU-2025-2547','title':'Commission Implementing Regulation (EU) 2025/2547 on emissions embedded in goods','celex':'32025R2547','url':'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025R2547','scope':'Actual-emissions methodology and complex goods/precursors','status':'binding_act; separate calculation path'}]
(OUT/'legal_authority_register.json').write_text(json.dumps({'status':'authority_map_not_legal_signoff','authorities':AUTHORITIES},indent=2),encoding='utf-8')
rows=[]
for name in ('default_values_staged.jsonl','benchmarks_staged.jsonl'):
 for line in (OUT/name).read_text(encoding='utf-8').splitlines():
  r=json.loads(line);typ=r.get('record_type','');aid='EU-2025-2620' if typ=='benchmark' else 'EU-2025-2621-CONS-2026-01-01 + EU-2026-1740';annex='benchmark table' if typ=='benchmark' else ('Annex IV' if typ=='annex_iv_precursor_default' else 'Annex I')
  rows.append({'reconciliation_id':f"{typ}:{r.get('source_sheet')}:{r.get('source_row')}:{r.get('code')}",'record_type':typ,'source_file':r.get('source_file'),'source_sha256':r.get('source_sha256'),'source_sheet':r.get('source_sheet'),'source_row':r.get('source_row'),'country':r.get('country'),'sector':r.get('sector'),'code':r.get('code'),'description':r.get('description'),'route':r.get('route') or r.get('column_a_route') or r.get('column_b_route'),'authority_id':aid,'annex_or_table':annex,'legal_match_status':'PENDING_BINDING_ANNEX_MATCH','reviewer':'','reviewed_at':'','notes':'Do not promote until exact legal annex value/code/route/units are verified.'})
with (OUT/'row_level_legal_reconciliation_queue.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
print(json.dumps({'authorities':len(AUTHORITIES),'reconciliation_rows':len(rows),'status':'PENDING_BINDING_ANNEX_MATCH','promotion_performed':False},indent=2))
