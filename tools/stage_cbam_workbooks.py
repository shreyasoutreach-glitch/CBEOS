#!/usr/bin/env python3
"""Stage official and benchmark workbook rows without approving/promoting them.

All source cells are preserved with original labels, raw value states, hashes and
line locators. A stage operation can never modify the runtime regulatory DB.
"""
import argparse,hashlib,json,re,sys
from pathlib import Path
from decimal import Decimal,InvalidOperation
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]
def normalize_code(value):
 if value is None:return None
 s=str(value).strip()
 if not s or s.casefold() in {'none','nan'}:return None
 digits=''.join(ch for ch in s if ch.isdigit())
 return digits or None
def parse_decimal(value):
 if value is None or isinstance(value,bool):return None
 if isinstance(value,(int,float,Decimal)):
  try:d=Decimal(str(value));return d if d.is_finite() else None
  except InvalidOperation:return None
 s=str(value).strip().replace('\u00a0','').replace(' ','')
 if not s or s in {'-','—','–','n/a','N/A'}:return None
 if ',' in s and '.' in s:
  if s.rfind(',')>s.rfind('.'):s=s.replace('.','').replace(',','.')
  else:s=s.replace(',','')
 elif ',' in s:s=s.replace(',','.')
 try:
  d=Decimal(s);return d if d.is_finite() else None
 except InvalidOperation:return None
def value_state(value):
 if value is None or not str(value).strip():return ('blank_review',None)
 s=str(value).strip()
 if s in {'-','—','–'}:return ('fallback_required',None)
 if re.search(r'\b(see below|see above|same as|group total|subtotal|included below)\b',s,re.I):return ('group_parent',None)
 d=parse_decimal(value)
 if d is not None:return ('numeric',d)
 return ('text_review',None)
def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def stage_defaults(path):
 path=Path(path);wb=load_workbook(path,read_only=True,data_only=True);digest=sha256(path);rows=[];counts={}
 for ws in wb.worksheets:
  for ri,row in enumerate(ws.iter_rows(values_only=True),1):
   if not row or all(v is None for v in row):continue
   cells=[str(v).strip() if v is not None else '' for v in row]
   first=' '.join(cells[:5]).casefold()
   if any(marker in first for marker in ('cn code','country','description','total emissions','direct emissions')):continue
   code=None
   for cell in cells:
    candidate=normalize_code(cell)
    if candidate and len(candidate) in (4,6,8,10) and any(ch.isdigit() for ch in cell):
     code=candidate;break
   if not code:continue
   numeric=[]
   for cell in cells:
    st,val=value_state(cell)
    if st=='numeric':numeric.append(str(val))
   state='numeric' if numeric else ('fallback_required' if any(value_state(v)[0]=='fallback_required' for v in cells) else 'blank_review')
   rows.append({'record_type':'annex_i_default','source_file':path.name,'source_sha256':digest,'source_sheet':ws.title,'source_row':ri,'raw_cells':cells,'code':code,'country':cells[0] if cells else '', 'sector':'unknown','route':'','direct_tco2e_per_t':None,'indirect_tco2e_per_t':None,'total_tco2e_per_t':numeric[-1] if numeric else None,'value_state':state,'approval_status':'staged_unverified'})
 wb.close()
 meta={'status':'staged_only_not_approved','source_file':path.name,'source_sha256':digest,'row_count':len(rows),'sheet_count':len(wb.sheetnames) if hasattr(wb,'sheetnames') else 0}
 return rows,meta
def stage_benchmarks(path):
 path=Path(path);wb=load_workbook(path,read_only=True,data_only=True);digest=sha256(path);rows=[]
 for ws in wb.worksheets:
  for ri,row in enumerate(ws.iter_rows(values_only=True),1):
   vals=[v for v in row]
   if not vals or all(v is None for v in vals):continue
   cells=[str(v).strip() if v is not None else '' for v in vals]
   code=next((normalize_code(v) for v in vals if normalize_code(v) and len(normalize_code(v)) in (4,6,8,10)),None)
   if not code:continue
   is_cont=not any(cells[:3]) and any(cells[3:])
   a_state,a_val=value_state(vals[-2] if len(vals)>1 else None);b_state,b_val=value_state(vals[-1] if vals else None)
   rows.append({'record_type':'benchmark','source_file':path.name,'source_sha256':digest,'source_sheet':ws.title,'source_row':ri,'raw_cells':cells,'code':code,'description':cells[1] if len(cells)>1 else '', 'sector':'unknown','column_a_bmg_tco2e_per_t':str(a_val) if a_val is not None else None,'column_a_state':a_state,'column_a_route':'','column_b_bmg_tco2e_per_t':str(b_val) if b_val is not None else None,'column_b_state':b_state,'column_b_route':'','route_independent_approved':False,'is_continuation':is_cont,'approval_status':'staged_unverified'})
 wb.close();return rows,{'status':'staged_only_not_approved','source_file':path.name,'source_sha256':digest,'row_count':len(rows)}
def main():
 p=argparse.ArgumentParser();p.add_argument('--defaults',type=Path);p.add_argument('--benchmarks',type=Path);p.add_argument('--out',type=Path,default=ROOT/'staging'/'output');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);reports=[]
 if a.defaults:
  rows,meta=stage_defaults(a.defaults);(a.out/'default_values_staged.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8');reports.append(meta)
 if a.benchmarks:
  rows,meta=stage_benchmarks(a.benchmarks);(a.out/'benchmarks_staged.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8');reports.append(meta)
 report={'status':'STAGED_UNVERIFIED','promotion_performed':False,'sources':reports};(a.out/'staging_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
