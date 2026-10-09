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
        self.table_depth=0
        self.table_no=0
        self.row_no=0
        self.in_row=False
        self.in_cell=False
        self.cell_parts=[]
        self.cells=[]
        self.rows=[]
        self.tables={}
    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        if tag=='table':
            self.table_depth+=1
            if self.table_depth==1:
                self.table_no+=1
                self.row_no=0
                self.tables[self.table_no]=0
        elif self.table_depth and tag=='tr' and self.table_depth==1:
            self.in_row=True;self.row_no+=1;self.cells=[]
        elif self.in_row and self.table_depth==1 and tag in ('td','th'):
            self.in_cell=True;self.cell_parts=[]
    def handle_data(self,data):
        if self.in_cell:
            value=' '.join(data.split())
            if value:self.cell_parts.append(value)
    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag in ('td','th') and self.in_cell and self.table_depth==1:
            self.cells.append(' '.join(self.cell_parts).strip())
            self.cell_parts=[];self.in_cell=False
        elif tag=='tr' and self.in_row and self.table_depth==1:
            if any(self.cells):
                self.rows.append({'table_no':self.table_no,'row_no':self.row_no,'cells':self.cells[:]})
                self.tables[self.table_no]=self.tables.get(self.table_no,0)+1
            self.in_row=False;self.cells=[]
        elif tag=='table' and self.table_depth:
            self.table_depth-=1
            if self.table_depth==0:
                self.in_row=False;self.in_cell=False;self.cells=[];self.cell_parts=[]

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
    manifest={'status':'EXTRACTED_UNREVIEWED','promotion_performed':False,'sources':results,'limits':['HTML table extraction only; narrative provisions may exist outside tables.','No legal keys or values are approved by this script.','A qualified reviewer must validate table structure, annex identity, code/country/route, units, effective dates and completeness.']}
    (out_dir/'extraction_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path('staging/official_sources'));p.add_argument('--out',type=Path,default=Path('staging/official_sources/extracted_tables'));a=p.parse_args()
    manifest=extract(a.input,a.out);print(json.dumps(manifest,indent=2))
    if manifest['status']!='EXTRACTED_UNREVIEWED':raise SystemExit(2)
if __name__=='__main__':main()
