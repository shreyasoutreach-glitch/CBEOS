#!/usr/bin/env python3
"""Conservative row-level comparison of staged CBAM workbooks to extracted EUR-Lex tables.

Inputs: extracted_tables/*.jsonl from the official-source acquisition artifact and
staging/output/*_staged.jsonl from stage_cbam_workbooks.py. This never approves or
promotes a record; extracted HTML remains unreviewed legal source material.
"""
import argparse, csv, json, re, hashlib
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

def jl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
def code(x):
    return "".join(ch for ch in str(x or "") if ch.isdigit())
def txt(x):
    return " ".join(str(x or "").strip().casefold().replace("’", "'").replace("&", "and").split())
def country(x):
    s=txt(x)
    return {"_other countries and territorie":"other countries and territories",
            "other countries and territories":"other countries and territories"}.get(s,s)
def sector(x):
    s=txt(x)
    return {"iron and steel":"iron_steel","fertilisers":"fertilisers","fertilizers":"fertilisers"}.get(s,s.replace(" ","_"))
def route(x):
    return "".join(re.findall(r"\([A-Za-z0-9]+\)",str(x or ""))).casefold()
def dec(x):
    s=str(x or "").strip().replace("\u00a0","").replace(" ","")
    if s in ("","-","—","–","N/A","n/a"): return None
    try:
        d=Decimal(s.replace(",","."))
        return d if d.is_finite() else None
    except InvalidOperation: return None
def state(x):
    s=str(x or "").strip()
    if dec(x) is not None:return "numeric"
    if s in ("-","—","–","N/A","n/a"):return "fallback_required"
    if not s:return "blank_review"
    return "non_numeric_review"
def write_csv(path,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def build_defaults(src):
    allrows=jl(Path(src)/"defaults_correction_tables.jsonl"); tables=defaultdict(list)
    for r in allrows:tables[int(r["table_no"])].append(r)
    annex1=[]; annex4=[]; idx=defaultdict(list); ividx=defaultdict(list)
    for tn in range(29,151):
        tr=tables.get(tn,[]); country=(tr[0].get("cells") or [""])[0]
        sec=""
        for r in tr:
            c=r.get("cells") or []; first=str(c[0] if c else "").strip()
            if sector(first) in ("cement","hydrogen","fertilisers","iron_steel","aluminium","electricity"):
                sec=sector(first);continue
            cd=code(first)
            if len(cd) not in (4,6,8,10) or len(c)<5:continue
            x={"country":txt(country),"sector":sec,"code":cd,"route":route(c[5] if len(c)>5 else ""),
               "direct":dec(c[2]),"indirect":dec(c[3]),"total":dec(c[4]),
               "direct_raw":c[2],"indirect_raw":c[3],"total_raw":c[4],"table":tn,"row":r.get("row_no"),
               "source_sha256":r.get("source_sha256","")}
            annex1.append(x);idx[(country(x["country"]),sec,cd,x["route"])].append(x)
    sec=""
    for r in tables.get(162,[]):
        c=r.get("cells") or []
        if len(c)<3:continue
        first=str(c[0]).strip()
        if sector(first) in ("cement","hydrogen","fertilisers","iron_steel","aluminium","electricity"):
            sec=sector(first);continue
        cd=code(first)
        if len(cd) not in (4,6,8,10):continue
        x={"sector":sec,"code":cd,"value":dec(c[2]),"raw":c[2],"table":162,"row":r.get("row_no"),"source_sha256":r.get("source_sha256","")}
        annex4.append(x);ividx[(sec,cd)].append(x)
    return annex1,idx,annex4,ividx
def build_benchmarks(src):
    rows=jl(Path(src)/"benchmarks_tables.jsonl"); out=[]; idx=defaultdict(list); sec=""
    pat=re.compile(r"([0-9]+(?:[,.][0-9]+)?)(?:\s*((?:\([A-Za-z0-9]+\)\s*)*))")
    for r in rows:
        if int(r.get("table_no",-1))!=62:continue
        c=r.get("cells") or []
        if len(c)<4:continue
        first=str(c[0]).strip()
        if sector(first) in ("cement","hydrogen","fertilisers","iron_steel","aluminium","electricity"):
            sec=sector(first);continue
        cd=code(first)
        if len(cd) not in (4,6,8,10):continue
        for col,ci in (("a",2),("b",3)):
            for m in pat.finditer(str(c[ci] or "")):
                v=dec(m.group(1))
                if v is None:continue
                x={"sector":sec,"code":cd,"column":col,"route":route(m.group(2)),"value":v,
                   "source_row":r.get("row_no"),"source_sha256":r.get("source_sha256","")}
                out.append(x);idx[(sec,cd,col,x["route"])].append(x)
    return out,idx
def run(src,out):
    src=Path(src);out=Path(out)
    defs,didx,iv,ividx=build_defaults(src); bm,bidx=build_benchmarks(src)
    drows=[];counts=Counter()
    for r in jl(out/"default_values_staged.jsonl"):
        kind=r.get("record_type"); s=sector(r.get("sector")); cd=code(r.get("code"));issues=[];canon=None
        if kind=="annex_i_default":
            key=(country(r.get("country")),s,cd,route(r.get("route")) );m=didx.get(key,[])
            if len(m)!=1: status="SOURCE_ROW_NOT_UNIQUE";issues=[f"source_matches={len(m)}"]
            else:
                canon=m[0]
                if r.get("value_state")=="numeric":
                    for name,field in (("direct","direct_tco2e_per_t"),("indirect","indirect_tco2e_per_t"),("total","total_tco2e_per_t")):
                        if dec(r.get(field))!=canon[name]:issues.append(name.upper()+"_MISMATCH")
                elif r.get("value_state") in ("fallback_required","blank_review"):
                    if r.get("value_state")!=state(canon[name+"_raw"] if (name:="total") else ""):issues.append("VALUE_STATE_MISMATCH")
                elif r.get("value_state")=="group_parent":
                    if any(canon[x] is not None for x in ("direct","indirect","total")):issues.append("GROUP_PARENT_NUMERIC")
                else:issues.append("UNSUPPORTED_STATE")
                if route(r.get("route"))!=canon["route"]:issues.append("ROUTE_MISMATCH")
                status="SOURCE_MATCH_EXTRACTED_UNREVIEWED" if not issues else "SOURCE_VALUE_MISMATCH_REVIEW_REQUIRED"
        elif kind=="annex_iv_precursor_default":
            m=ividx.get((s,cd),[])
            if len(m)!=1:status="ANNEX_IV_SOURCE_ROW_NOT_UNIQUE";issues=[f"source_matches={len(m)}"]
            else:
                canon=m[0]
                if dec(r.get("value_tco2e_per_t"))!=canon["value"]:issues.append("VALUE_MISMATCH")
                if r.get("value_state")!=state(canon["raw"]):issues.append("VALUE_STATE_MISMATCH")
                status="ANNEX_IV_SOURCE_MATCH_EXTRACTED_UNREVIEWED" if not issues else "ANNEX_IV_VALUE_MISMATCH_REVIEW_REQUIRED"
        else:continue
        counts[status]+=1
        drows.append({"record_type":kind,"status":status,"issues":"|".join(issues),"country":r.get("country") or "",
          "sector":s,"code":r.get("code") or "","route":r.get("route") or "",
          "staged_value_state":r.get("value_state") or "","staged_direct":r.get("direct_tco2e_per_t") or "",
          "staged_indirect":r.get("indirect_tco2e_per_t") or "","staged_total":r.get("total_tco2e_per_t") or r.get("value_tco2e_per_t") or "",
          "source_direct":str(canon.get("direct")) if canon and canon.get("direct") is not None else "",
          "source_indirect":str(canon.get("indirect")) if canon and canon.get("indirect") is not None else "",
          "source_total":str(canon.get("total",canon.get("value"))) if canon and canon.get("total",canon.get("value")) is not None else "",
          "eurlex_table_no":canon.get("table","") if canon else "","eurlex_row_no":canon.get("row","") if canon else "",
          "eurlex_source_sha256":canon.get("source_sha256","") if canon else "","promotion_status":"NOT_APPROVED_NO_PROMOTION"})
    brows=[];bc=Counter()
    for r in jl(out/"benchmarks_staged.jsonl"):
        issues=[];sources=[]
        for col in ("a","b"):
            val=dec(r.get(f"column_{col}_bmg_tco2e_per_t"));st=r.get(f"column_{col}_state")
            if st!="numeric" or val is None:continue
            key=(sector(r.get("sector")),code(r.get("code")),col,route(r.get(f"column_{col}_route")))
            m=bidx.get(key,[])
            if not m and key[3]:m=bidx.get((key[0],key[1],col,""),[])
            if len(m)!=1:issues.append(f"COLUMN_{col.upper()}_SOURCE_MATCHES_{len(m)}")
            else:
                sources.extend(m)
                if val!=m[0]["value"]:issues.append(f"COLUMN_{col.upper()}_VALUE_MISMATCH")
        status="BENCHMARK_SOURCE_MATCH_EXTRACTED_UNREVIEWED" if not issues else "BENCHMARK_SOURCE_MISMATCH_REVIEW_REQUIRED"
        bc[status]+=1
        brows.append({"record_type":"benchmark","status":status,"issues":"|".join(issues),"sector":r.get("sector") or "",
          "code":r.get("code") or "","description":r.get("description") or "","is_continuation":r.get("is_continuation",False),
          "source_sheet":r.get("source_sheet") or "","source_row":r.get("source_row") or "",
          "staged_column_a":r.get("column_a_bmg_tco2e_per_t") or "","staged_column_a_route":r.get("column_a_route") or "",
          "staged_column_b":r.get("column_b_bmg_tco2e_per_t") or "","staged_column_b_route":r.get("column_b_route") or "",
          "eurlex_source_rows":"|".join(str(x["source_row"]) for x in sources),"promotion_status":"NOT_APPROVED_NO_PROMOTION"})
    write_csv(out/"row_level_legal_source_reconciliation.csv",drows)
    write_csv(out/"row_level_benchmark_source_reconciliation.csv",brows)
    summary={"status":"MACHINE_RECONCILIATION_COMPLETE_SOURCE_REVIEW_OPEN","promotion_performed":False,
      "annex_i_and_iv_status_counts":dict(sorted(counts.items())),"benchmark_status_counts":dict(sorted(bc.items())),
      "staged_rows_total":len(drows)+len(brows),"extracted_source_rows":{"annex_i":len(defs),"annex_iv":len(iv),"benchmark_values":len(bm)},
      "limitations":["Source HTML is extracted but not legally approved.","A match proves extracted-cell agreement, not complete legal interpretation.","No promotion or live filing is authorized."]}
    (out/"acquired_source_reconciliation_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source-dir",required=True);p.add_argument("--out",required=True);a=p.parse_args();run(a.source_dir,a.out)
