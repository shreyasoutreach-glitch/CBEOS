#!/usr/bin/env python3
"""Acquire official EUR-Lex HTML sources for full legal reconciliation.
Raw retrieval is not legal interpretation or canonical data approval.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen
SOURCES={
 "defaults_consolidated":"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02025R2621-20260101",
 "defaults_base":"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025R2621",
 "defaults_correction":"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32026R1740",
 "benchmarks":"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025R2620",
 "emissions_methodology":"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025R2547"}
class TextExtractor(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style','noscript'):self.skip+=1
  if tag in ('tr','p','div','br','h1','h2','h3','li'):self.parts.append('\n')
 def handle_endtag(self,tag):
  if tag in ('script','style','noscript') and self.skip:self.skip-=1
  if tag in ('tr','p','div','h1','h2','h3','li'):self.parts.append('\n')
 def handle_data(self,data):
  if not self.skip:
   s=' '.join(data.split())
   if s:self.parts.append(s+' ')
def acquire(out:Path,timeout:int=30,retries:int=2):
 out.mkdir(parents=True,exist_ok=True);rows=[]
 for name,url in SOURCES.items():
  entry={'name':name,'url':url,'attempted_at_utc':datetime.now(timezone.utc).isoformat(),'status':'FETCH_FAILED','http_status':None,'sha256':None,'bytes':0,'error':None,'approval_status':'NOT_APPROVED'}
  last=None
  for attempt in range(retries+1):
   try:
    req=Request(url,headers={'User-Agent':'CBEOS-Legal-Source-Acquisition/1.0','Accept':'text/html,application/xhtml+xml'})
    with urlopen(req,timeout=timeout) as resp:body=resp.read();status=getattr(resp,'status',200);ctype=resp.headers.get('Content-Type','')
    if status<200 or status>=300:raise RuntimeError(f'Unexpected HTTP status {status}')
    if not body or b'<html' not in body[:10000].lower():raise RuntimeError(f'Unexpected/non-HTML response content-type={ctype}')
    (out/f'{name}.html').write_bytes(body);parser=TextExtractor();parser.feed(body.decode('utf-8',errors='replace'))
    text='\n'.join(x.strip() for x in ''.join(parser.parts).splitlines() if x.strip());(out/f'{name}.txt').write_text(text,encoding='utf-8')
    entry.update(status='FETCHED_RAW_UNREVIEWED',http_status=status,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),content_type=ctype,raw_file=f'{name}.html',text_file=f'{name}.txt',error=None);break
   except Exception as e:
    last=f'{type(e).__name__}: {e}'
    if attempt<retries:time.sleep(1+attempt)
  if entry['status']=='FETCH_FAILED':entry['error']=last
  rows.append(entry)
 manifest={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'status':'FETCHED_UNREVIEWED' if all(x['status']=='FETCHED_RAW_UNREVIEWED' for x in rows) else 'SOURCE_ACQUISITION_INCOMPLETE','sources':rows,'important_limits':['Raw source retrieval is not legal interpretation.','No canonical rows are generated or approved.','Annex tables still require structured extraction, source locators, full reconciliation, and independent review.','Supersession and effective-date relationships must be checked.']}
 (out/'acquisition_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');return manifest
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',default='staging/official_sources');p.add_argument('--timeout',type=int,default=30);p.add_argument('--retries',type=int,default=2);a=p.parse_args()
 m=acquire(Path(a.out),a.timeout,a.retries);print(json.dumps(m,indent=2))
 if m['status']!='FETCHED_UNREVIEWED':raise SystemExit(2)
if __name__=='__main__':main()
