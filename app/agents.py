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


def _bound_contex