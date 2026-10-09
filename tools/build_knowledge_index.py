#!/usr/bin/env python3
"""Build a page-level, source-hashed local retrieval index from supplied CBAM PDFs."""
import hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SOURCE_DIR=ROOT/'knowledge'/'sources';OUT=ROOT/'knowledge'/'index.json';MANIFEST=ROOT/'knowledge'/'manifest.json'
def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 pages=[];docs=[]
 for path in sorted(SOURCE_DIR.glob('*.pdf')):
  digest=sha256(path);reader=PdfReader(str(path),strict=True)
  if reader.is_encrypted:raise ValueError(f'Encrypted PDF cannot be indexed: {path.name}')
  docs.append({'filename':path.name,'sha256':digest,'pages':len(reader.pages),'bytes':path.stat().st_size})
  for i,page in enumerate(reader.pages,1):
   text=re.sub(r'\s+',' ',page.extract_text() or '').strip()
   if text:pages.append({'filename':path.name,'sha256':digest,'page':i,'text':text})
 if not docs or not pages:raise ValueError('No readable PDF pages found; refusing to write an empty index')
 OUT.write_text(json.dumps({'schema_version':1,'documents':docs,'pages':pages},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 digest=sha256(OUT);MANIFEST.write_text(json.dumps({'schema_version':1,'source_count':len(docs),'indexed_page_count':len(pages),'index_sha256':digest,'documents':docs},ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'Indexed {len(docs)} PDFs and {len(pages)} text-bearing pages');print(f'Index: {OUT} ({OUT.stat().st_size:,} bytes)');print(f'Manifest: {MANIFEST}')
if __name__=='__main__':main()
