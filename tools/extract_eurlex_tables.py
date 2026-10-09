#!/usr/bin/env python3
"""Extract HTML table rows from official EUR-Lex pages without approving values.

Output is a review aid only. It preserves source file/hash, table number, row
number, and every cell's extracted text. It does not normalize legal keys or
promote data to the runtime regulatory dataset.
"""
import argparse,hashlib,json
from html.parser import HTMLParser
from pathlib import Path

class TableExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.table_stack=[]
        self.table_no=0
        self.rows=[]
        self.tables={}
    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        if tag=='table':
            self.table_no+=1
            self.tables[self.table_no]=0
            self.table_stack.append({'table_no':self.table_no,'row_no':0,'in_row':False,'in_cell':False,'cell_parts':[],'cells':[]})
            return
        if not self.table_stack:return
        ctx=self.table_stack[-1]
        if tag=='tr':
            ctx['in_row']=True;ctx['row_no']+=1;ctx['cells']=[]
        elif tag in ('td','th') and ctx['in_row']:
            ctx['in_cell']=True;ctx['cell_parts']=[]
    def handle_data(self,data):
        value=' '.join(data.split())
        if not value:return
        # Nested-table text belongs to its own cell and is also part of the
        # parent cell's text. Each row keeps its own table/row locator.
        for ctx in self.table_stack:
            if ctx['in_cell']:ctx['cell_parts'].append(value)
    def handle_endtag(self,tag):
        tag=tag.lower()
        if not self.table_stack:return
        ctx=self.table_stack[-1]
        if tag in ('td','th') and ctx['in_cell']:
            ctx['cells'].append(' '.join(ctx['cell_parts']).strip())
            ctx['cell_parts']=[];ctx['in_cell']=False
        elif tag=='tr' and ctx['in_row']:
            if any(ctx['cells']):
                self.rows.append({'table_no':ctx['table_no'],'row_no':ctx['row_no'],'cells':ctx['cells'][:]})
                self.tables[ctx['table_no']]=self.tables.get(ctx['table_no'],0)+1
            ctx['in_row']=False;ctx['cells']=[]
        elif tag=='table':
            self.table_stack.pop()

def file_hash(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def extract(input_dir:Path,out_dir:Path):
    out_dir.mkdir(parents=True,exist_ok=True);results=[]
    for source in sorted(input_dir.glob('*.html')):
        parser=TableExtractor()
        with source.open('r',encoding='utf-8',errors='replace') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),''):parser.feed(chunk)
        digest=file_hash(source);target=out_dir/(source.stem+'_tables.jsonl')
        with target.open('w',encoding='utf-8') as stream:
            for row in parser.rows:
                stream.write(json.dumps({'source_file':source.name,'source_sha256':digest,'approval_status':'NOT_APPROVED','review_status':'EXTRACTED_UNREVIEWED',**row},ensure_ascii=False)+'\n')
        results.append({'source_file':source.name,'source_sha256':digest,'tables_detected':parser.table_no,'table_rows_extracted':len(parser.rows),'output_file':target.name,'approval_status':'NOT_APPROVED'})
    manifest={'status':'EXTRACTED_UNREVIEWED','promotion_performed':False,'sources':results,'limits':['HTML table extraction only; narrative provisions may exist outside tables.','Nested tables are preserved as separate table locators; parent cell text may include nested text.','No legal keys or values are approved by this script.','A qualified reviewer must validate table structure, annex identity, code/country/route, units, effective dates and completeness.']}
    (out_dir/'extraction_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path('staging/official_sources'));p.add_argument('--out',type=Path,default=Path('staging/official_sources/extracted_tables'));a=p.parse_args()
    manifest=extract(a.input,a.out);print(json.dumps(manifest,indent=2))
    if manifest['status']!='EXTRACTED_UNREVIEWED':raise SystemExit(2)
if __name__=='__main__':main()
