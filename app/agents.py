"""CBEOS multi-agent workflow.

The policy and accounting facts are deterministic and remain authoritative.
An optional OpenAI-compatible model may critique/summarize each agent's work,
but its prose can never verify evidence, close exceptions, alter calculations,
or approve a case. Every hand-off is persisted with structured payloads.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from datetime import date
from decimal import Decimal, InvalidOperation

from . import engine, util

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / 'knowledge' / 'index.json'
MANIFEST_PATH = ROOT / 'knowledge' / 'manifest.json'
AUTHORITY_REGISTER_PATH = ROOT / 'knowledge' / 'authority_register.json'
MAX_LLM_TIMEOUT = 10
AGENT_ORDER = [
    ('orchestrator', 'Intake & Scope Agent'), ('intake', 'Intake & Scope Agent'),
    ('evidence', 'Evidence Quality Agent'), ('supplier_ops', 'Supplier Operations Agent'),
    ('reconciliation', 'Reconciliation Agent'), ('regulatory', 'Regulatory Research Agent'),
    ('calculation_auditor', 'Calculation Integrity Agent'), ('commercial_exposure', 'Commercial Exposure Agent'),
    ('verification', 'Verifier Readiness Agent'), ('declaration_qa', 'Declaration Package QA Agent'),
    ('orchestrator', 'Control Tower Orchestrator'),
]
AGENT_INSTRUCTIONS = {
    'Intake & Scope Agent': 'Establish the operational baseline from stored records. Flag missing scope and distinguish candidate from verified facts.',
    'Evidence Quality Agent': 'Find missing requirements, weak provenance and unreviewed facts. A document being present does not prove it is sufficient evidence.',
    'Supplier Operations Agent': 'Triage supplier requests, deadlines and overdue evidence. Recommend follow-ups but never send messages or mark a supplier response validated.',
    'Reconciliation Agent': 'Challenge cross-source conflicts and prioritize exceptions. Never close, waive or accept risk on an exception.',
    'Regulatory Research Agent': 'Return exact source-page citations and explain uncertainty. Retrieval is not legal interpretation and guidance does not supersede binding law.',
    'Calculation Integrity Agent': 'Audit source authority, reporting period, units and scenario status. Never invent or recalculate legal liability.',
    'Commercial Exposure Agent': 'Summarize recorded exception impacts and existing scenario-only estimates separately. Never represent either as verified CBAM liability.',
    'Verifier Readiness Agent': 'Combine blockers transparently. An operational score is not compliance, verification or approval.',
    'Declaration Package QA Agent': 'Verify the stored package hash and compare its snapshot with current case data. Never generate, approve or submit a package.',
}
STOPWORDS = {'the','and','for','with','from','that','this','into','are','was','were','has','have','not','but','can','may','must','shall','should','about','which','what','when','where','how','all','any','each','per','of','to','in','on','by','as','at','or','an','a','is','be','it','its','their','they','will','than','then','also','under','over'}


def llm_configured() -> bool:
    return bool(os.getenv('CBAM_LLM_API_KEY') and os.getenv('CBAM_LLM_MODEL'))


def _tokens(text: str) -> list[str]:
    return [x for x in re.findall(r'[a-z0-9]{2,}', (text or '').lower()) if x not in STOPWORDS]


def _bound_context(value, depth=0):
    """Bound untrusted context while preserving valid JSON structure."""
    if depth > 6:
        return '[nested context omitted]'
    if isinstance(value, str):
        return value if len(value) <= 900 else value[:900] + '…[truncated]'
    if isinstance(value, dict):
        items = list(value.items())[:50]
        result = {str(k)[:100]: _bound_context(v, depth+1) for k,v in items}
        if len(value) > len(items): result['_truncated_keys'] = len(value)-len(items)
        return result
    if isinstance(value, (list, tuple)):
        items = list(value)[:20]
        result = [_bound_context(v, depth+1) for v in items]
        if len(value) > len(items): result.append(f'[{len(value)-len(items)} additional items omitted]')
        return result
    if value is None or isinstance(value, (int,float,bool)):
        return value
    return str(value)[:300]


def retrieve_sources(query: str, top_k: int = 4) -> list[dict]:
    """BM25-style page retrieval with title relevance, source hashes and page citations.

    Results are diversified across documents so repeated pages from one long PDF do
    not crowd out a relevant sector guide. This is retrieval, not legal authority ranking.
    """
    if not INDEX_PATH.exists():
        return []
    try:
        index_bytes = INDEX_PATH.read_bytes()
        manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
        expected_index_hash = manifest.get('index_sha256', '')
        if not expected_index_hash or hashlib.sha256(index_bytes).hexdigest() != expected_index_hash:
            return []  # fail closed if the page index and manifest do not match
        index = json.loads(index_bytes.decode('utf-8'))
        pages = index.get('pages', [])
        terms = list(dict.fromkeys(_tokens(query)))
        if not terms or not isinstance(pages, list):
            return []

        # Document-frequency weighting reduces the dominance of generic terms such
        # as "CBAM", "emissions", "calculation" and "guidance".
        tokenized = []
        df = {}
        total_length = 0
        for page in pages:
            text = str(page.get('text', ''))
            toks = re.findall(r'[a-z0-9]{2,}', text.lower())
            freq = {}
            for token in toks:
                if token not in STOPWORDS:
                    freq[token] = freq.get(token, 0) + 1
            for token in freq:
                df[token] = df.get(token, 0) + 1
            total_length += sum(freq.values())
            tokenized.append((page, freq, sum(freq.values())))
        n_pages = max(1, len(tokenized))
        avgdl = max(1.0, total_length / n_pages)
        scored = []
        query_phrase = ' '.join(terms)
        for page, freq, doc_len in tokenized:
            score = 0.0
            for term in terms:
                tf = freq.get(term, 0)
                if not tf:
                    continue
                idf = max(0.0, math.log(1 + (n_pages - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5)))
                score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * doc_len / avgdl))
            filename = str(page.get('filename', ''))
            title_tokens = set(re.findall(r'[a-z0-9]{2,}', filename.lower()))
            title_hits = sum(1 for term in terms if term in title_tokens)
            score += title_hits * 3.0
            page_text = str(page.get('text', '')).lower()
            if query_phrase and query_phrase in page_text:
                score += 2.0
            if score > 0:
                scored.append((score, page))
        scored.sort(key=lambda item: (-item[0], str(item[1].get('filename', '')).lower(), int(item[1].get('page', 0) or 0)))

        results = []
        seen_pages = set()
        per_document = {}
        verified_source_hashes = {}
        source_root = (ROOT / 'knowledge' / 'sources').resolve()
        limit = max(1, min(int(top_k), 8))
        for score, page in scored:
            filename = str(page.get('filename', ''))
            try:
                page_number = int(page.get('page', 0))
            except (ValueError, TypeError):
                continue
            identity = (filename, page_number)
            if identity in seen_pages or page_number < 1 or per_document.get(filename, 0) >= 2:
                continue
            # Basename-only paths prevent a corrupted index from escaping sources/.
            if not filename or Path(filename).name != filename:
                continue
            source_path = (source_root / filename).resolve()
            if source_path.parent != source_root or not source_path.is_file():
                continue
            if filename not in verified_source_hashes:
                digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
                verified_source_hashes[filename] = digest
            if verified_source_hashes[filename] != page.get('sha256'):
                continue
            text = str(page.get('text', ''))
            low = text.lower()
            positions = [low.find(term) for term in terms if low.find(term) >= 0]
            start = max(0, min(positions or [0]) - 180)
            excerpt = text[start:start+900].strip()
            results.append({'filename': filename, 'page': page_number,
                            'sha256': page['sha256'], 'score': round(score, 4), 'excerpt': excerpt})
            seen_pages.add(identity)
            per_document[filename] = per_document.get(filename, 0) + 1
            if len(results) >= limit:
                break
        return results
    except (OSError, ValueError, TypeError, KeyError):
        return []


def _llm_commentary(agent_name: str, case: dict, deterministic_result: dict,
                    previous_messages: list[dict], sources: list[dict]) -> dict:
    """Optional narrative critique. Any failure safely falls back to deterministic mode."""
    if not llm_configured():
        return {'status': 'not_configured', 'text': ''}
    api_key = os.getenv('CBAM_LLM_API_KEY', '')
    base = os.getenv('CBAM_LLM_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    model = os.getenv('CBAM_LLM_MODEL', '')
    parsed_base = urlparse(base)
    local_http_hosts = {'localhost','127.0.0.1','::1'}
    if not parsed_base.hostname or parsed_base.username or parsed_base.password or not (parsed_base.scheme == 'https' or (parsed_base.scheme == 'http' and parsed_base.hostname.lower() in local_http_hosts)):
        return {'status': 'blocked_invalid_endpoint', 'text': ''}
    context = {
        'case': {'case_name': case.get('case_name'), 'period': case.get('period'), 'sector': case.get('sector')},
        'deterministic_findings': deterministic_result,
        'prior_agent_handoffs': [{'from':m['from_agent'],'to':m['to_agent'],'body':m['body'][:900]} for m in previous_messages[-4:]],
        'regulatory_source_excerpts': [{'citation':f"{x['filename']} p.{x['page']} sha256:{x['sha256']}",'excerpt':x['excerpt'][:500]} for x in sources[:3]],
    }
    role_inst