"""Schema + connection layer.

Design rules carried over from v1.0 and extended:
 - Every tenant-owned table carries tenant_id and every query that touches it
   filters by tenant_id. This is enforced at the access layer (engine.py /
   server.py), not just by convention -- see tests/test_security.py for the
   adversarial cross-tenant checks.
 - Nothing here decides *whether* a value is authoritative. That is the
   evidence-state machine in engine.py. This module only stores rows.
"""
import os
import re
import sqlite3
from decimal import Decimal

from . import util

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'data')
UP = os.getenv('CBAM_UPLOAD_DIR', os.path.join(DATA, 'uploads'))
DB_PATH = os.getenv('CBAM_DB_PATH', os.path.join(DATA, 'cbam.db'))
os.makedirs(UP, exist_ok=True)
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)

SCHEMA = '''
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS tenants(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, created TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, email TEXT NOT NULL,
  password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'reviewer', active INTEGER NOT NULL DEFAULT 1,
  created TEXT NOT NULL, UNIQUE(tenant_id,email),
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, csrf TEXT NOT NULL, expires TEXT NOT NULL,
  created TEXT NOT NULL, ip TEXT DEFAULT '',
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);

-- Operational workspace: a bounded unit of evidence + review for one importer/period.
CREATE TABLE IF NOT EXISTS cases(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, company TEXT NOT NULL, case_name TEXT NOT NULL,
  period TEXT NOT NULL, sector TEXT DEFAULT '', status TEXT DEFAULT 'working',
  created TEXT NOT NULL, updated TEXT NOT NULL, approved_at TEXT DEFAULT '', notes TEXT DEFAULT '',
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS reporting_periods(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, code TEXT NOT NULL, start_date TEXT DEFAULT '',
  end_date TEXT DEFAULT '', declaration_deadline TEXT DEFAULT '', status TEXT DEFAULT 'open',
  created TEXT NOT NULL, UNIQUE(tenant_id,code),
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS suppliers(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, name TEXT NOT NULL, country TEXT DEFAULT '',
  contact_name TEXT DEFAULT '', contact_email TEXT DEFAULT '', external_ref TEXT DEFAULT '',
  status TEXT DEFAULT 'active', notes TEXT DEFAULT '', created TEXT NOT NULL, updated TEXT NOT NULL,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS installations(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, supplier_id INTEGER, name TEXT NOT NULL,
  country TEXT DEFAULT '', unlocode TEXT DEFAULT '', production_route TEXT DEFAULT '',
  monitoring_plan_status TEXT DEFAULT 'unknown', status TEXT DEFAULT 'active',
  created TEXT NOT NULL, updated TEXT NOT NULL,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS cn_reference(
  code TEXT PRIMARY KEY, description TEXT NOT NULL, sector TEXT NOT NULL, aggregated_category TEXT DEFAULT '');

CREATE TABLE IF NOT EXISTS products(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, cn_code TEXT NOT NULL, description TEXT DEFAULT '',
  sector TEXT DEFAULT '', created TEXT NOT NULL, updated TEXT NOT NULL, UNIQUE(tenant_id,cn_code),
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE);

-- One "import" = one customs consignment/declaration header; it groups import lines.
CREATE TABLE IF NOT EXISTS imports(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL, reference TEXT DEFAULT '',
  mode TEXT DEFAULT 'sea', arrival_date TEXT DEFAULT '', customs_office TEXT DEFAULT '',
  status TEXT DEFAULT 'open', created TEXT NOT NULL, updated TEXT NOT NULL,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS import_lines(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL, import_id INTEGER,
  product_id INTEGER, supplier_id INTEGER, installation_id INTEGER, reporting_period_id INTEGER,
  invoice_ref TEXT DEFAULT '', cn_code TEXT DEFAULT '', description TEXT DEFAULT '',
  origin_country TEXT DEFAULT '', quantity TEXT DEFAULT '', quantity_unit TEXT DEFAULT 't',
  customs_value TEXT DEFAULT '', customs_ref TEXT DEFAULT '', production_route TEXT DEFAULT '',
  applicability TEXT DEFAULT 'needs_review', status TEXT DEFAULT 'candidate',
  created TEXT NOT NULL, updated TEXT NOT NULL,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
  FOREIGN KEY(import_id) REFERENCES imports(id) ON DELETE SET NULL,
  FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL,
  FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
  FOREIGN KEY(installation_id) REFERENCES installations(id) ON DELETE SET NULL,
  FOREIGN KEY(reporting_period_id) REFERENCES reporting_periods(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL,
  import_line_id INTEGER, supplier_id INTEGER, installation_id INTEGER,
  filename TEXT NOT NULL, stored_name TEXT NOT NULL, mime TEXT DEFAULT '', doc_type TEXT DEFAULT 'other',
  size_bytes INTEGER DEFAULT 0, sha256 TEXT NOT NULL, version INTEGER DEFAULT 1, superseded_by INTEGER,
  uploaded TEXT NOT NULL, uploaded_by INTEGER, extracted_text TEXT DEFAULT '', meta_json TEXT DEFAULT '{}',
  status TEXT DEFAULT 'processed', scan_status TEXT DEFAULT 'clean',
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
  FOREIGN KEY(import_line_id) REFERENCES import_lines(id) ON DELETE SET NULL,
  FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
  FOREIGN KEY(installation_id) REFERENCES installations(id) ON DELETE SET NULL,
  UNIQUE(case_id,sha256));

CREATE TABLE IF NOT EXISTS facts(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL, document_id INTEGER NOT NULL,
  import_line_id INTEGER, supplier_id INTEGER, installation_id INTEGER,
  field TEXT NOT NULL, value TEXT NOT NULL, numeric_value TEXT DEFAULT '', unit TEXT DEFAULT '',
  normalized_value TEXT DEFAULT '', unit_normalized TEXT DEFAULT '', conversion_note TEXT DEFAULT '',
  location TEXT DEFAULT '', source_excerpt TEXT DEFAULT '', confidence TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'candidate', verified_by INTEGER, verified_at TEXT DEFAULT '',
  created TEXT NOT NULL, updated TEXT NOT NULL,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
  FOREIGN KEY(import_line_id) REFERENCES import_lines(id) ON DELETE SET NULL,
  FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
  FOREIGN KEY(installation_id) REFERENCES installations(id) ON DELETE SET NULL,
  FOREIGN KEY(verified_by) REFERENCES users(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS evidence(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL, name TEXT NOT NULL,
  category TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'missing', document_id INTEGER,
  scope_type TEXT DEFAULT 'case', scope_id INTEGER,
  owner TEXT DEFAULT '', source TEXT DEFAULT '', note TEXT DEFAULT '', expires_at TEXT DEFAULT '',
  updated TEXT NOT NULL,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS evidence_links(
  id INTEGER PRIMARY KEY, evidence_id INTEGER NOT NULL, fact_id INTEGER, entity_type TEXT DEFAULT '',
  entity_id INTEGER, note TEXT DEFAULT '',
  FOREIGN KEY(evidence_id) REFERENCES evidence(id) ON DELETE CASCADE,
  FOREIGN KEY(fact_id) REFERENCES facts(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS evidence_requirements(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL, name TEXT NOT NULL,
  category TEXT NOT NULL, applicability TEXT DEFAULT 'operational', status TEXT DEFAULT 'missing',
  scope_type TEXT DEFAULT 'case', scope_id INTEGER DEFAULT 0, reason TEXT DEFAULT '',
  created TEXT NOT NULL, updated TEXT NOT NULL, UNIQUE(case_id,name,scope_type,scope_id),
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE);

-- Exception queue: the operational product. Status machine documented in engine.py.
CREATE TABLE IF NOT EXISTS exceptions(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL, title TEXT NOT NULL,
  category TEXT DEFAULT 'general', severity TEXT NOT NULL, status TEXT DEFAULT 'OPEN',
  affected_entity_type TEXT DEFAULT '', affected_entity_id INTEGER,
  detail TEXT DEFAULT '', field TEXT DEFAULT '', supporting_evidence TEXT DEFAULT '',
  conflicting_evidence TEXT DEFAULT '', recommended_action TEXT DEFAULT '',
  financial_impact_eur TEXT DEFAULT '',
  owner TEXT DEFAULT '', deadline TEXT DEFAULT '', resolution TEXT DEFAULT '',
  reviewer_id INTEGER, source TEXT DEFAULT '', created TEXT NOT NULL, updated TEXT NOT NULL,
  closed_by INTEGER,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
  FOREIGN KEY(reviewer_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY(closed_by) REFERENCES users(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS supplier_requests(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL, supplier_id INTEGER NOT NULL,
  requirement_name TEXT DEFAULT '', title TEXT NOT NULL, draft TEXT DEFAULT '',
  status TEXT DEFAULT 'DRAFT', deadline TEXT DEFAULT '', sent_at TEXT DEFAULT '',
  responded_at TEXT DEFAULT '', escalation_level INTEGER DEFAULT 0,
  created_by INTEGER, created TEXT NOT NULL, updated TEXT NOT NULL,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
  FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS methodologies(
  id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, kind TEXT NOT NULL,
  description TEXT DEFAULT '', source_id INTEGER);

CREATE TABLE IF NOT EXISTS emissions_data(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, installation_id INTEGER NOT NULL,
  reporting_period_id INTEGER, methodology_id INTEGER,
  direct_intensity TEXT DEFAULT '', indirect_intensity TEXT DEFAULT '', unit TEXT DEFAULT 'tCO2e/t',
  source_fact_id INTEGER, status TEXT DEFAULT 'candidate', created TEXT NOT NULL, updated TEXT NOT NULL,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(installation_id) REFERENCES installations(id) ON DELETE CASCADE,
  FOREIGN KEY(methodology_id) REFERENCES methodologies(id) ON DELETE SET NULL,
  FOREIGN KEY(source_fact_id) REFERENCES facts(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS regulatory_sources(
  id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, title TEXT NOT NULL, effective_date TEXT DEFAULT '',
  url TEXT DEFAULT '', status TEXT DEFAULT 'active', notes TEXT DEFAULT '', created TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS rule_sets(
  id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, version TEXT NOT NULL, effective_from TEXT NOT NULL,
  source_id INTEGER, description TEXT NOT NULL, status TEXT DEFAULT 'active', created TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES regulatory_sources(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS default_values(
  id INTEGER PRIMARY KEY, rule_set_id INTEGER NOT NULL, sector TEXT NOT NULL, cn_prefix TEXT DEFAULT '',
  production_route TEXT DEFAULT '', country TEXT DEFAULT '',
  direct_default TEXT NOT NULL, indirect_default TEXT DEFAULT '0', total_default TEXT DEFAULT '', unit TEXT DEFAULT 'tCO2e/t',
  confidence TEXT DEFAULT 'illustrative', markup_note TEXT DEFAULT '', source_id INTEGER,
  FOREIGN KEY(rule_set_id) REFERENCES rule_sets(id) ON DELETE CASCADE,
  FOREIGN KEY(source_id) REFERENCES regulatory_sources(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS default_value_markups(
  id INTEGER PRIMARY KEY, rule_set_id INTEGER NOT NULL, sector TEXT NOT NULL, year INTEGER NOT NULL,
  markup_pct TEXT NOT NULL, source_id INTEGER, UNIQUE(rule_set_id,sector,year),
  FOREIGN KEY(rule_set_id) REFERENCES rule_sets(id) ON DELETE CASCADE,
  FOREIGN KEY(source_id) REFERENCES regulatory_sources(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS free_allocation_schedule(
  id INTEGER PRIMARY KEY, rule_set_id INTEGER NOT NULL, year INTEGER NOT NULL,
  cbam_factor_pct TEXT NOT NULL, free_allocation_remaining_pct TEXT NOT NULL, source_id INTEGER,
  UNIQUE(rule_set_id,year),
  FOREIGN KEY(rule_set_id) REFERENCES rule_sets(id) ON DELETE CASCADE,
  FOREIGN KEY(source_id) REFERENCES regulatory_sources(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS cbam_benchmarks(
  id INTEGER PRIMARY KEY, rule_set_id INTEGER NOT NULL, sector TEXT NOT NULL, production_route TEXT NOT NULL,
  benchmark_tco2e_per_t TEXT NOT NULL, confidence TEXT DEFAULT 'illustrative', source_id INTEGER,
  UNIQUE(rule_set_id,production_route),
  FOREIGN KEY(rule_set_id) REFERENCES rule_sets(id) ON DELETE CASCADE,
  FOREIGN KEY(source_id) REFERENCES regulatory_sources(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS certificate_prices(
  id INTEGER PRIMARY KEY, rule_set_id INTEGER, period TEXT NOT NULL, price_eur TEXT NOT NULL,
  source_id INTEGER, observed_at TEXT NOT NULL,
  FOREIGN KEY(rule_set_id) REFERENCES rule_sets(id) ON DELETE SET NULL,
  FOREIGN KEY(source_id) REFERENCES regulatory_sources(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS calculation_runs(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL, import_line_id INTEGER,
  rule_set_id INTEGER NOT NULL, methodology_id INTEGER, run_type TEXT NOT NULL,
  created TEXT NOT NULL, created_by INTEGER, input_snapshot TEXT NOT NULL, result_json TEXT NOT NULL,
  status TEXT DEFAULT 'scenario', review_status TEXT DEFAULT 'unreviewed',
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
  FOREIGN KEY(import_line_id) REFERENCES import_lines(id) ON DELETE SET NULL,
  FOREIGN KEY(rule_set_id) REFERENCES rule_sets(id) ON DELETE RESTRICT);

CREATE TABLE IF NOT EXISTS verification_records(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, installation_id INTEGER NOT NULL,
  reporting_period_id INTEGER, readiness_score INTEGER DEFAULT 0, checklist_json TEXT DEFAULT '[]',
  status TEXT DEFAULT 'NOT_READY', computed_at TEXT NOT NULL,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(installation_id) REFERENCES installations(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS declaration_packages(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL,
  generated_at TEXT NOT NULL, generated_by INTEGER, manifest_json TEXT NOT NULL, sha256 TEXT NOT NULL,
  status TEXT DEFAULT 'draft',
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS regulatory_updates(
  id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, title TEXT NOT NULL, announced_date TEXT NOT NULL,
  effective_date TEXT DEFAULT '', source_id INTEGER, affected_scope TEXT DEFAULT '', impact TEXT DEFAULT '',
  product_implication TEXT DEFAULT '', status TEXT DEFAULT 'WATCH', created TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES regulatory_sources(id) ON DELETE SET NULL);

CREATE TABLE IF NOT EXISTS approvals(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL, decision TEXT NOT NULL,
  comment TEXT DEFAULT '', created TEXT NOT NULL, actor_id INTEGER,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
  FOREIGN KEY(actor_id) REFERENCES users(id) ON DELETE SET NULL);

-- Append-only, hash-chained per tenant. Never UPDATE/DELETE rows here.
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY, tenant_id INTEGER, case_id INTEGER, actor_id INTEGER, action TEXT NOT NULL,
  detail TEXT DEFAULT '', created TEXT NOT NULL, prev_hash TEXT DEFAULT '', hash TEXT NOT NULL,
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE SET NULL,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE SET NULL,
  FOREIGN KEY(actor_id) REFERENCES users(id) ON DELETE SET NULL);

-- Durable, inspectable multi-agent workflow runs and agent-to-agent messages.
CREATE TABLE IF NOT EXISTS agent_runs(
  id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, case_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'RUNNING', provider TEXT DEFAULT 'rules-only',
  started_at TEXT NOT NULL, finished_at TEXT DEFAULT '', summary_json TEXT DEFAULT '{}', error_code TEXT DEFAULT '',
  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_agent_runs_case ON agent_runs(tenant_id,case_id,id);
CREATE TABLE IF NOT EXISTS agent_messages(
  id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL, sequence_no INTEGER NOT NULL,
  from_agent TEXT NOT NULL, to_agent TEXT NOT NULL, message_type TEXT NOT NULL DEFAULT 'handoff',
  body TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
  prev_hash TEXT DEFAULT '', message_hash TEXT NOT NULL DEFAULT '',
  UNIQUE(run_id,sequence_no),
  FOREIGN KEY(run_id) REFERENCES agent_runs(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_agent_messages_run ON agent_messages(run_id,sequence_no);

CREATE INDEX IF NOT EXISTS idx_cases_tenant ON cases(tenant_id);
CREATE INDEX IF NOT EXISTS idx_docs_case ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_facts_case ON facts(case_id);
CREATE INDEX IF NOT EXISTS idx_facts_line ON facts(import_line_id);
CREATE INDEX IF NOT EXISTS idx_lines_case ON import_lines(case_id);
CREATE INDEX IF NOT EXISTS idx_lines_supplier ON import_lines(supplier_id);
CREATE INDEX IF NOT EXISTS idx_lines_installation ON import_lines(installation_id);
CREATE INDEX IF NOT EXISTS idx_exceptions_case ON exceptions(case_id);
CREATE INDEX IF NOT EXISTS idx_exceptions_status ON exceptions(tenant_id,status);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit(tenant_id,id);
CREATE INDEX IF NOT EXISTS idx_reqs_case ON evidence_requirements(case_id);
'''

# Defense-in-depth tenant relationship checks. Application-layer scoping remains
# required, but cross-tenant parent references must also fail if a route is ever
# missed or a direct SQL write is attempted. INSERT and UPDATE are both guarded.
TENANT_RELATION_CHECKS = {
    'installations': "NEW.supplier_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM suppliers WHERE id=NEW.supplier_id AND tenant_id=NEW.tenant_id)",
    'imports': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id)",
    'import_lines': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id) OR (NEW.import_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM imports WHERE id=NEW.import_id AND tenant_id=NEW.tenant_id AND case_id=NEW.case_id)) OR (NEW.product_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM products WHERE id=NEW.product_id AND tenant_id=NEW.tenant_id)) OR (NEW.supplier_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM suppliers WHERE id=NEW.supplier_id AND tenant_id=NEW.tenant_id)) OR (NEW.installation_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM installations WHERE id=NEW.installation_id AND tenant_id=NEW.tenant_id AND (NEW.supplier_id IS NULL OR supplier_id IS NULL OR supplier_id=NEW.supplier_id))) OR (NEW.reporting_period_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM reporting_periods WHERE id=NEW.reporting_period_id AND tenant_id=NEW.tenant_id))",
    'documents': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id) OR (NEW.import_line_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM import_lines WHERE id=NEW.import_line_id AND tenant_id=NEW.tenant_id AND case_id=NEW.case_id)) OR (NEW.supplier_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM suppliers WHERE id=NEW.supplier_id AND tenant_id=NEW.tenant_id)) OR (NEW.installation_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM installations WHERE id=NEW.installation_id AND tenant_id=NEW.tenant_id AND (NEW.supplier_id IS NULL OR supplier_id IS NULL OR supplier_id=NEW.supplier_id))) OR (NEW.uploaded_by IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.uploaded_by AND tenant_id=NEW.tenant_id))",
    'facts': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id) OR NOT EXISTS (SELECT 1 FROM documents WHERE id=NEW.document_id AND tenant_id=NEW.tenant_id AND case_id=NEW.case_id) OR (NEW.import_line_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM import_lines WHERE id=NEW.import_line_id AND tenant_id=NEW.tenant_id AND case_id=NEW.case_id)) OR (NEW.supplier_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM suppliers WHERE id=NEW.supplier_id AND tenant_id=NEW.tenant_id)) OR (NEW.installation_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM installations WHERE id=NEW.installation_id AND tenant_id=NEW.tenant_id)) OR (NEW.verified_by IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.verified_by AND tenant_id=NEW.tenant_id))",
    'evidence': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id) OR (NEW.document_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM documents WHERE id=NEW.document_id AND tenant_id=NEW.tenant_id AND case_id=NEW.case_id))",
    'evidence_requirements': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id)",
    'exceptions': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id) OR (NEW.reviewer_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.reviewer_id AND tenant_id=NEW.tenant_id)) OR (NEW.closed_by IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.closed_by AND tenant_id=NEW.tenant_id))",
    'supplier_requests': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id) OR NOT EXISTS (SELECT 1 FROM suppliers WHERE id=NEW.supplier_id AND tenant_id=NEW.tenant_id) OR (NEW.created_by IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.created_by AND tenant_id=NEW.tenant_id))",
    'emissions_data': "NOT EXISTS (SELECT 1 FROM installations WHERE id=NEW.installation_id AND tenant_id=NEW.tenant_id) OR (NEW.reporting_period_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM reporting_periods WHERE id=NEW.reporting_period_id AND tenant_id=NEW.tenant_id)) OR (NEW.source_fact_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM facts WHERE id=NEW.source_fact_id AND tenant_id=NEW.tenant_id))",
    'calculation_runs': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id) OR (NEW.import_line_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM import_lines WHERE id=NEW.import_line_id AND tenant_id=NEW.tenant_id AND case_id=NEW.case_id)) OR (NEW.created_by IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.created_by AND tenant_id=NEW.tenant_id))",
    'verification_records': "NOT EXISTS (SELECT 1 FROM installations WHERE id=NEW.installation_id AND tenant_id=NEW.tenant_id) OR (NEW.reporting_period_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM reporting_periods WHERE id=NEW.reporting_period_id AND tenant_id=NEW.tenant_id))",
    'declaration_packages': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id) OR (NEW.generated_by IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.generated_by AND tenant_id=NEW.tenant_id))",
    'approvals': "NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id) OR (NEW.actor_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.actor_id AND tenant_id=NEW.tenant_id))",
    'audit': "(NEW.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants WHERE id=NEW.tenant_id)) OR (NEW.case_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id)) OR (NEW.actor_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.actor_id AND tenant_id=NEW.tenant_id))",
}
TENANT_TRIGGERS = '\n'.join(
    f"CREATE TRIGGER IF NOT EXISTS trg_{table}_tenant_{event.lower()} "
    f"BEFORE {event} ON {table} WHEN ({condition}) "
    "BEGIN SELECT RAISE(ABORT, 'tenant relationship mismatch'); END;"
    for table, condition in TENANT_RELATION_CHECKS.items()
    for event in ('INSERT', 'UPDATE')
)

# Evidence-requirement catalogue. `applicability` starting value is a default;
# a reviewer can mark a requirement not_applicable for a given case with a reason
# (see engine.set_requirement_applicability). scope determines whether the
# requirement is evaluated once per case, or once per supplier/installation/import_line.
REQS = [
    ('Commercial invoice', 'commercial', 'operational', 'import_line',
     'Establishes the commercial transaction, price and quantity for this shipment.'),
    ('Packing list', 'shipping', 'operational', 'import_line',
     'Independent confirmation of quantity/weight -- the primary cross-check against the invoice.'),
    ('Bill of lading / transport document', 'shipping', 'operational', 'import_line',
     'Confirms the shipment actually moved, and the route/carrier, independent of the commercial paperwork.'),
    ('Product / CN classification support', 'classification', 'CBAM', 'import_line',
     'CN code determines CBAM applicability and which default values/benchmarks apply.'),
    ('Import line / customs data', 'customs', 'CBAM', 'import_line',
     'Customs declaration data (MRN, customs value) is what the CBAM declaration is ultimately reconciled against.'),
    ('Producer / installation identity', 'installation', 'CBAM', 'installation',
     'CBAM requires embedded emissions to be attributed to a specific, identifiable installation, not just "the supplier".'),
    ('Production quantity / activity data', 'activity', 'CBAM', 'installation',
     'The activity-level data any actual-emissions figure must be derivable from.'),
    ('Embedded emissions data', 'emissions', 'CBAM', 'installation',
     'The direct/indirect specific emissions figure itself -- without this the calculation falls back to a (more expensive) regulatory default.'),
    ('Methodology / calculation support', 'methodology', 'CBAM', 'installation',
     'How the emissions figure was derived -- what a verifier checks first.'),
    ('Carbon price already paid evidence', 'carbon_price', 'CBAM', 'installation',
     'A verified carbon price paid at origin can be deducted from the certificate obligation.'),
    ('Free allocation / benchmark inputs', 'free_allocation', 'CBAM', 'case',
     'Confirms which CBAM benchmark/production route applies for the free-allocation adjustment (SEFA).'),
    ('Verification report / verifier evidence', 'verification', 'CBAM', 'installation',
     'The accredited-verifier sign-off a declaration ultimately needs.'),
    ('Supplier declaration / upstream evidence', 'supplier', 'operational', 'supplier',
     "The supplier's own attestation of the data they have provided."),
]
REQ_WHY = {name: why for name, _, _, _, why in REQS}

EVIDENCE_QUALITY_STATES = ['INSUFFICIENT', 'EXTRACTED', 'SOURCE_SUPPORTED', 'CONFLICTING',
                            'RECONCILED', 'HUMAN_REVIEWED', 'APPROVED', 'STALE']
EVIDENCE_QUALITY_ORDER = {s: i for i, s in enumerate(EVIDENCE_QUALITY_STATES)}

NUMERIC_FIELDS = {'eu_tonnes', 'direct_intensity', 'indirect_intensity'}
NORMALIZED_TEXT_FIELDS = {'supplier', 'origin_country', 'installation'}
RECONCILE_TOLERANCE = {
    'eu_tonnes': (0.005, 0.05), 'direct_intensity': (0.01, 0.01), 'indirect_intensity': (0.01, 0.01),
}
UNIT_CONVERSIONS = {
    'eu_tonnes': {'t': (Decimal(1), 't'), 'tonnes': (Decimal(1), 't'), 'tonne': (Decimal(1), 't'),
                   'kg': (Decimal('0.001'), 't'), 'lb': (Decimal('0.000453592'), 't'),
                   'lbs': (Decimal('0.000453592'), 't')},
    'direct_intensity': {'tco2e/t': (Decimal(1), 'tCO2e/t'), 'kgco2e/t': (Decimal('0.001'), 'tCO2e/t'),
                           'tco2e/kg': (Decimal(1000), 'tCO2e/t')},
    'indirect_intensity': {'tco2e/t': (Decimal(1), 'tCO2e/t'), 'kgco2e/t': (Decimal('0.001'), 'tCO2e/t'),
                             'tco2e/kg': (Decimal(1000), 'tCO2e/t')},
}

FIELD_LABELS = {
    'eu_tonnes': 'Import quantity', 'direct_intensity': 'Direct specific emissions',
    'indirect_intensity': 'Indirect specific emissions', 'cn_code': 'CN code',
    'invoice_number': 'Invoice number', 'supplier': 'Supplier / producer',
    'shipment_reference': 'Shipment reference', 'installation': 'Installation',
    'origin_country': 'Country of origin',
}

ROLES = ['admin', 'manager', 'reviewer', 'viewer']
# Permission -> minimum role rank required (index into ROLES, lower index = more privileged
# since ROLES is ordered most- to least-privileged). A role satisfies a permission if its
# rank is <= the permission's required rank.
ROLE_RANK = {r: i for i, r in enumerate(ROLES)}
PERMISSIONS = {
    'view': 'viewer', 'upload': 'reviewer', 'review_fact': 'reviewer',
    'manage_evidence': 'reviewer', 'manage_exceptions': 'reviewer',
    'manage_suppliers': 'manager', 'run_calculation': 'manager',
    'approve_case': 'manager', 'generate_declaration': 'manager',
    'accept_risk': 'manager', 'waive_exception': 'manager',
    'manage_users': 'admin', 'manage_settings': 'admin',
}


def has_permission(role: str, perm: str) -> bool:
    need = PERMISSIONS.get(perm, 'admin')
    return ROLE_RANK.get(role, 99) <= ROLE_RANK.get(need, 0)


def _split_sql_statements(sql):
    """Split simple DDL scripts without treating semicolons in strings/comments as delimiters."""
    statements, current = [], []
    single = double = line_comment = block_comment = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ''
        if line_comment:
            current.append(ch)
            if ch == '\n':
                line_comment = False
        elif block_comment:
            current.append(ch)
            if ch == '*' and nxt == '/':
                current.append(nxt)
                i += 1
                block_comment = False
        elif single:
            current.append(ch)
            if ch == "'" and nxt == "'":
                current.append(nxt)
                i += 1
            elif ch == "'":
                single = False
        elif double:
            current.append(ch)
            if ch == '"' and nxt == '"':
                current.append(nxt)
                i += 1
            elif ch == '"':
                double = False
        elif ch == '-' and nxt == '-':
            current.extend([ch, nxt])
            i += 1
            line_comment = True
        elif ch == '/' and nxt == '*':
            current.extend([ch, nxt])
            i += 1
            block_comment = True
        elif ch == "'":
            current.append(ch)
            single = True
        elif ch == '"':
            current.append(ch)
            double = True
        elif ch == ';':
            statement = ''.join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(ch)
        i += 1
    tail = ''.join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def _translate_postgres_sql(statement):
    """Translate the small, intentional SQLite SQL subset used by the application."""
    statement = str(statement).strip()
    ignore_conflict = bool(re.match(r'INSERT\s+OR\s+IGNORE\s+INTO\b', statement, re.I))
    if ignore_conflict:
        statement = re.sub(r'^INSERT\s+OR\s+IGNORE\s+INTO\b', 'INSERT INTO', statement, count=1, flags=re.I)
        statement = statement.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
    return statement.replace('?', '%s'), ignore_conflict


class _PostgresConnection:
    """Small psycopg2 compatibility layer for the app's existing sqlite-style SQL."""
    is_postgres = True

    def __init__(self, url):
        import psycopg2
        from psycopg2.extras import DictCursor
        self._psycopg2 = psycopg2
        self._conn = psycopg2.connect(url, sslmode='require', cursor_factory=DictCursor)
        self._last_insert_table = None

    def execute(self, sql, params=()):
        statement = str(sql).strip()
        table_info = re.match(r'PRAGMA\s+table_info\((\w+)\)', statement, re.I)
        if re.match(r'PRAGMA\s+(foreign_keys|journal_mode)', statement, re.I):
            cur = self._conn.cursor()
            cur.execute('SELECT 1 AS ok')
            return cur
        if table_info:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT column_name AS name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
                (table_info.group(1).lower(),),
            )
            return cur
        if re.match(r'SELECT\s+last_insert_rowid\s*\(\s*\)', statement, re.I):
            cur = self._conn.cursor()
            if not self._last_insert_table:
                cur.execute('SELECT NULL::bigint AS lastrowid')
            else:
                cur.execute(
                    "SELECT currval(pg_get_serial_sequence(%s, 'id')::regclass) AS lastrowid",
                    ('public.' + self._last_insert_table,),
                )
            return cur

        statement, _ignore_conflict = _translate_postgres_sql(statement)
        insert = re.match(r'INSERT\s+INTO\s+([a-z_][a-z0-9_]*)', statement, re.I)
        if insert:
            self._last_insert_table = insert.group(1).lower()
        cur = self._conn.cursor()
        try:
            cur.execute(statement, params if params else None)
        except self._psycopg2.IntegrityError as exc:
            # Preserve the app's existing exception handling contract.
            raise sqlite3.IntegrityError(str(exc)) from exc
        return cur

    def executescript(self, script):
        # SQLite trigger scripts contain internal semicolons; PostgreSQL equivalents are installed separately.
        if re.search(r'CREATE\s+TRIGGER\b', script, re.I):
            return
        for statement in _split_sql_statements(script):
            clean = statement.lstrip()
            if not clean or re.match(r'PRAGMA\b', clean, re.I):
                continue
            # SQLite trigger definitions are replaced with equivalent PL/pgSQL triggers below.
            if re.match(r'CREATE\s+TRIGGER\b', clean, re.I):
                continue
            statement = re.sub(
                r'\b([a-z_][a-z0-9_]*)\s+INTEGER\s+PRIMARY\s+KEY\b',
                r'\1 BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY',
                statement,
                flags=re.I,
            )
            self.execute(statement)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _install_postgres_tenant_guards(c):
    """Recreate SQLite tenant guards as PostgreSQL row triggers."""
    for table, condition in TENANT_RELATION_CHECKS.items():
        function_name = 'cbeos_guard_' + table
        c.execute(
            f"CREATE OR REPLACE FUNCTION public.{function_name}() RETURNS trigger "
            "LANGUAGE plpgsql SET search_path=pg_catalog,public AS $cbeos$ "
            f"BEGIN IF ({condition}) THEN RAISE EXCEPTION 'tenant relationship mismatch'; "
            "END IF; RETURN NEW; END $cbeos$"
        )
        c.execute(f'DROP TRIGGER IF EXISTS trg_{table}_tenant_guard ON public.{table}')
        c.execute(
            f'CREATE TRIGGER trg_{table}_tenant_guard BEFORE INSERT OR UPDATE ON public.{table} '
            f'FOR EACH ROW EXECUTE FUNCTION public.{function_name}()'
        )
    c.execute(
        "CREATE OR REPLACE FUNCTION public.cbeos_guard_agent_run_case() RETURNS trigger "
        "LANGUAGE plpgsql SET search_path=pg_catalog,public AS $cbeos$ "
        "BEGIN IF NOT EXISTS (SELECT 1 FROM public.cases "
        "WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id) "
        "THEN RAISE EXCEPTION 'agent run tenant/case mismatch'; END IF; "
        "RETURN NEW; END $cbeos$"
    )
    for event in ('insert', 'update'):
        c.execute(f'DROP TRIGGER IF EXISTS agent_runs_tenant_{event} ON public.agent_runs')
    c.execute(
        'CREATE TRIGGER agent_runs_tenant_insert BEFORE INSERT ON public.agent_runs '
        'FOR EACH ROW EXECUTE FUNCTION public.cbeos_guard_agent_run_case()'
    )
    c.execute(
        'CREATE TRIGGER agent_runs_tenant_update BEFORE UPDATE OF tenant_id,case_id ON public.agent_runs '
        'FOR EACH ROW EXECUTE FUNCTION public.cbeos_guard_agent_run_case()'
    )


def db():
    database_url = (os.getenv('CBAM_DATABASE_URL') or os.getenv('DATABASE_URL') or '').strip()
    mode = os.getenv('CBAM_CUSTOMER_DATA_MODE', 'sandbox').strip().lower()
    if mode == 'production' and not database_url:
        raise RuntimeError('Production mode requires CBAM_DATABASE_URL; refusing to use ephemeral SQLite.')
    if database_url:
        return _PostgresConnection(database_url)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA journal_mode=WAL')
    return c


def init():
    c = db()
    c.executescript(SCHEMA)
    c.executescript(TENANT_TRIGGERS)
    if getattr(c, 'is_postgres', False):
        _install_postgres_tenant_guards(c)
    c.executescript("""
    CREATE TRIGGER IF NOT EXISTS agent_runs_tenant_insert
    BEFORE INSERT ON agent_runs
    WHEN NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id)
    BEGIN SELECT RAISE(ABORT, 'agent run tenant/case mismatch'); END;
    CREATE TRIGGER IF NOT EXISTS agent_runs_tenant_update
    BEFORE UPDATE OF tenant_id,case_id ON agent_runs
    WHEN NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND tenant_id=NEW.tenant_id)
    BEGIN SELECT RAISE(ABORT, 'agent run tenant/case mismatch'); END;
    """)
    # Forward-compatible additive migrations for existing local databases.
    message_cols = {row['name'] for row in c.execute('PRAGMA table_info(agent_messages)').fetchall()}
    if 'prev_hash' not in message_cols:
        c.execute("ALTER TABLE agent_messages ADD COLUMN prev_hash TEXT DEFAULT ''")
    if 'message_hash' not in message_cols:
        c.execute("ALTER TABLE agent_messages ADD COLUMN message_hash TEXT NOT NULL DEFAULT ''")
    # One-time backfill for runs created by early v2.5 development builds.
    import hashlib
    for run_row in c.execute('SELECT DISTINCT run_id FROM agent_messages ORDER BY run_id').fetchall():
        previous = ''
        for msg in c.execute('SELECT * FROM agent_messages WHERE run_id=? ORDER BY sequence_no', (run_row['run_id'],)).fetchall():
            if msg['message_hash']:
                previous = msg['message_hash']
                continue
            body = f"{msg['run_id']}|{msg['sequence_no']}|{msg['from_agent']}|{msg['to_agent']}|{msg['message_type']}|{msg['body']}|{msg['payload_json']}|{msg['created_at']}|{previous}"
            digest = util.sha256_text(body)
            c.execute('UPDATE agent_messages SET prev_hash=?,message_hash=? WHERE id=?', (previous,digest,msg['id']))
            previous = digest
    default_cols = {row['name'] for row in c.execute('PRAGMA table_info(default_values)').fetchall()}
    if 'total_default' not in default_cols:
        c.execute("ALTER TABLE default_values ADD COLUMN total_default TEXT DEFAULT ''")
    # Legacy rows did not store the legally relevant total separately. Preserve
    # their existing component-derived value for traceability; their confidence
    # remains non-authoritative and the engine will refuse to use it for a client
    # calculation until the official dataset is imported.
    c.execute("UPDATE default_values SET total_default = CAST(COALESCE(direct_default,'0') AS REAL) + CAST(COALESCE(indirect_default,'0') AS REAL) WHERE total_default IS NULL OR total_default='' ")
    t = c.execute('SELECT id FROM tenants LIMIT 1').fetchone()
    if not t:
        ts = util.now()
        c.execute('INSERT INTO tenants(name,slug,created) VALUES(?,?,?)', ('Demo Importer', 'demo', ts))
        tid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
        email = os.getenv('CBAM_ADMIN_EMAIL', 'admin@example.com')
        pw = os.getenv('CBAM_ADMIN_PASSWORD', 'change-me-now')
        c.execute('INSERT INTO users(tenant_id,email,password_hash,role,created) VALUES(?,?,?,?,?)',
                   (tid, email, util.password_hash(pw), 'admin', ts))
    seed_regulatory(c)
    seed_cn_reference(c)
    c.commit()
    c.close()


def seed_regulatory(c):
    """Regulatory source registry. Kept separate from tenant evidence and updated
    deliberately (never silently) -- see /sources in the UI. Every parameter below
    that is treated as authoritative (markup schedule, free-allocation/CBAM-factor
    schedule, certificate prices) is corroborated by the Commission's own published
    figures via at least one primary or Commission-quoting source as of Sep 2026;
    every parameter that is NOT independently confirmed (sector default emission
    values themselves, which require the actual Annex I/IV dataset) is explicitly
    marked confidence='illustrative' and never presented as authoritative in the UI.
    Treat this table, not the code around it, as the place regulatory updates get applied.
    """
    sources = [
        ('EU-CBAM-REGULATION', 'Regulation (EU) 2023/956 establishing CBAM', '2023-05-17',
         'https://eur-lex.europa.eu/eli/reg/2023/956/oj', 'Base CBAM Regulation.'),
        ('EU-CBAM-OMNIBUS', 'Regulation (EU) 2025/2083 (CBAM Omnibus simplification)', '2025-12-01',
         'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025R2083',
         'Introduces the binding 50 tonnes/year de minimis exemption (replacing the former €150 '
         'consignment-value threshold) and authorised-declarant simplifications.'),
        ('EU-CBAM-DEFAULTS-2025-2621', 'Implementing Regulation (EU) 2025/2621 (default values, definitive period)',
         '2026-01-01', 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025R2621',
         'Sets the definitive-period country/CN/production-route default emission values (Annex I), '
         'indirect-emissions electricity factors (Annex II), and default-value mark-up mechanism.'),
        ('EU-CBAM-DEFAULTS-CORR-2026-1740', 'Commission Implementing Regulation (EU) 2026/1740 (targeted correction)',
         '2026-07-31', 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R1740',
         'Replaces Annex I and Annex IV of IR 2025/2621 in full; corrects erroneous values and moves to '
         '10-digit TARIC-level granularity for some goods. Applies retrospectively from 1 Jan 2026. '
         'REGULATORY REVIEW REQUIRED: this product does not yet ingest the corrected Annex I/IV dataset '
         'itself -- see default_values.confidence.'),
        ('EU-CBAM-BENCHMARKS-2025-2620', 'Implementing Regulation (EU) 2025/2620 (CBAM benchmarks / SEFA methodology)',
         '2026-01-01', 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025R2620',
         'Defines the CBAM benchmarks (production-route-specific) and the Specific Embedded Free '
         'Allocation (SEFA) methodology used to compute the free-allocation adjustment.'),
        ('EU-CBAM-VERIFICATION-GUIDANCE', 'Commission guidance on CBAM verification and accreditation',
         '2026-08-24', 'https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-verification_en',
         'Published 24 Aug 2026. Verifiers may register in the CBAM Registry from 1 Sep 2026; first '
         'verification reports are issuable in the Registry from Jan 2027.'),
        ('EU-CBAM-REGISTRY', 'CBAM Registry and reporting', '2026-01-01',
         'https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-declarant-portal_en',
         'Official reporting/declaration channel. This product prepares declaration-ready evidence; '
         'it does not submit to the Registry.'),
        ('EU-CBAM-PRICES', 'CBAM certificate prices', '2026-01-01',
         'https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/price-cbam-certificates_en',
         'Certificate price = quarterly average (2026) / weekly average (from 2027) of EU ETS auction '
         'clearing prices, published by the Commission in the first week after the relevant quarter ends. '
         'No certificate purchases occur until Feb 2027 despite 2026 liability accruing.'),
        ('EU-ETS-FREE-ALLOCATION-PHASEOUT', 'EU ETS free-allocation phase-out / CBAM factor schedule (Art. 31, Reg. 2023/956)',
         '2026-01-01', 'https://www.eeas.europa.eu/sites/default/files/documents/2023/Carbon%20Border%20Adjustment%20Mechanism.pdf',
         'Official EEAS schedule: CBAM factor (phased-in share of certificates owed) rises 2.5% (2026), '
         '5% (2027), 10% (2028), 22.5% (2029), 48.5% (2030), 61% (2031), 73.5% (2032), 86% (2033), 100% '
         '(2034); free allocation remaining is the complement. WATCH ITEM: a pending proposal, COM(2026) '
         '616 of 17 Jul 2026 (ETS Phase 5 revision), would reintroduce 15% free allocation from 2028 and '
         'extend the phase-out to 2038 -- NOT adopted as of this build; not applied here.'),
        ('EU-CBAM-DEFAULT-MARKUP', 'CBAM default-value mark-up mechanism (Art. 7(2)/(7), Reg. 2023/956)',
         '2026-01-01', 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R0956',
         'Mark-up applied to default-value embedded emissions when used in place of actual data: 10% '
         '(2026), 20% (2027), 30% (2028 onward) for iron & steel, aluminium, cement and hydrogen; a flat '
         '1% for fertilisers from 2026. Since the IR 2026/1740 correction the mark-up is applied in the '
         'CBAM Registry to the total-emissions figure, not baked into the Annex table -- this product '
         'mirrors that: the mark-up is always a separate, visible line item, never pre-applied.'),
    ]
    for code, title, eff, url, notes in sources:
        c.execute('INSERT OR IGNORE INTO regulatory_sources(code,title,effective_date,url,notes,created) '
                   'VALUES(?,?,?,?,?,?)', (code, title, eff, url, notes, util.now()))

    # Product-facing regulatory watch. These are deliberately explicit records, not
    # hidden assumptions in calculation code. They make the control tower explain
    # what changed, when it applies, and what product surface must react.
    updates = [
        ('CBAM-2026-Q3-PRICE', 'Q3 2026 CBAM certificate price published at €82.32/tCO2e', '2026-10-05', '2026-10-05',
         'EU-CBAM-PRICES', 'pricing / finance', 'Q3 price is 9.36% above Q2; exposure and pass-through views must use the published quarterly price for Q3 imports.',
         'Update financial exposure and price-sensitivity outputs; preserve historical run prices.', 'ACTIVE'),
        ('CBAM-2026-VERIFIER-REGISTRY', 'CBAM verifier Registry workflow is operational', '2026-09-28', '2026-09-01',
         'EU-CBAM-VERIFICATION-GUIDANCE', 'verification / evidence', 'Verifier registration, Registry access procedures and training resources are now live; first reports can be issued from Jan 2027.',
         'Evidence readiness should be framed around verifier review, source support, conflicts and missing documentation.', 'ACTIVE'),
        ('CBAM-2026-DEFAULT-CORRECTION', 'Corrected CBAM default-value dataset applies retroactively from 1 Jan 2026', '2026-07-31', '2026-01-01',
         'EU-CBAM-DEFAULTS-CORR-2026-1740', 'defaults / methodology', 'Production-route indicators, units, CN/TARIC granularity and erroneous/omitted values were corrected; the Registry applies mark-ups to total emissions.',
         'Default-value inputs must be versioned, source-linked and replaceable without mutating historical calculation runs.', 'ACTIVE'),
        ('CBAM-2026-OPERATOR-GUIDANCE', 'Ten definitive-period operator guidance documents published', '2026-08-14', '2026-08-14',
         'EU-CBAM-DEFAULTS-2025-2621', 'MRV / operator workflow', 'Steel and adjacent sector guidance now provides implementation detail for non-EU installation operators.',
         'Expand plant-data intake and verification checklists around installation-level evidence, not only importer declarations.', 'ACTIVE'),
    ]
    for code,title,announced,effective,src_code,scope,impact,implication,status in updates:
        src = c.execute('SELECT id FROM regulatory_sources WHERE code=?',(src_code,)).fetchone()
        c.execute('INSERT OR IGNORE INTO regulatory_updates(code,title,announced_date,effective_date,source_id,affected_scope,impact,product_implication,status,created) '
                  'VALUES(?,?,?,?,?,?,?,?,?,?)', (code,title,announced,effective,src['id'] if src else None,scope,impact,implication,status,util.now()))

    rules_src = c.execute('SELECT id FROM regulatory_sources WHERE code=?', ('EU-CBAM-REGULATION',)).fetchone()['id']
    c.execute('INSERT OR IGNORE INTO rule_sets(code,version,effective_from,source_id,description,created) '
              'VALUES(?,?,?,?,?,?)',
              ('CBAM-2026-DEFINITIVE', '2.1.0', '2026-01-01', rules_src,
               'Definitive-regime rule set. Calculation logic is deterministic and versioned; every run '
               'snapshots this rule set id so historical results stay reproducible after the rules change. '
               'Sector-specific liability edge cases (precursor adjustments, complex goods) are intentionally '
               'out of scope for v1 and must be independently validated before being relied upon.',
               util.now()))
    rs = c.execute('SELECT id FROM rule_sets WHERE code=?', ('CBAM-2026-DEFINITIVE',)).fetchone()['id']

    price_src = c.execute('SELECT id FROM regulatory_sources WHERE code=?', ('EU-CBAM-PRICES',)).fetchone()['id']
    # Official Commission prices. Q3 was published 5 Oct 2026. Keep the price table
    # append-only so historical calculations retain the exact market input used.
    for period, price in [('2026-Q1', '75.36'), ('2026-Q2', '75.28'), ('2026-Q3', '82.32')]:
        c.execute('INSERT OR IGNORE INTO certificate_prices(rule_set_id,period,price_eur,source_id,observed_at) '
                   'VALUES(?,?,?,?,?)', (rs, period, price, price_src, util.now()))

    markup_src = c.execute('SELECT id FROM regulatory_sources WHERE code=?', ('EU-CBAM-DEFAULT-MARKUP',)).fetchone()['id']
    if not c.execute('SELECT 1 FROM default_value_markups LIMIT 1').fetchone():
        for sector in ('iron_steel', 'aluminium', 'cement', 'hydrogen'):
            for year, pct in ((2026, '10'), (2027, '20'), (2028, '30')):
                c.execute('INSERT INTO default_value_markups(rule_set_id,sector,year,markup_pct,source_id) '
                           'VALUES(?,?,?,?,?)', (rs, sector, year, pct, markup_src))
    # Ensure existing databases also receive the legally continuing 30% markup
    # from 2028 onwards for cement, iron/steel, aluminium and hydrogen. A
    # table-level 'has any rows' check alone would skip this migration.
    for sector in ('iron_steel', 'aluminium', 'cement', 'hydrogen'):
        for year, pct in ((2026, '10'), (2027, '20'), *((y, '30') for y in range(2028, 2041))):
            c.execute('INSERT OR IGNORE INTO default_value_markups(rule_set_id,sector,year,markup_pct,source_id) '
                      'VALUES(?,?,?,?,?)', (rs, sector, year, pct, markup_src))
    # Ensure existing databases also receive the legally continuing 1% fertilizer
    # schedule. A table-level 'has any rows' check alone would skip this migration.
    for year in range(2026, 2041):
        c.execute('INSERT OR IGNORE INTO default_value_markups(rule_set_id,sector,year,markup_pct,source_id) '
                  'VALUES(?,?,?,?,?)', (rs, 'fertilisers', year, '1', markup_src))

    schedule_src = c.execute('SELECT id FROM regulatory_sources WHERE code=?', ('EU-ETS-FREE-ALLOCATION-PHASEOUT',)).fetchone()['id']
    if not c.execute('SELECT 1 FROM free_allocation_schedule LIMIT 1').fetchone():
        for year, factor in ((2026, '2.5'), (2027, '5'), (2028, '10'), (2029, '22.5'), (2030, '48.5'),
                               (2031, '61'), (2032, '73.5'), (2033, '86'), (2034, '100')):
            remaining = str(Decimal('100') - Decimal(factor))
            c.execute('INSERT INTO free_allocation_schedule(rule_set_id,year,cbam_factor_pct,'
                       'free_allocation_remaining_pct,source_id) VALUES(?,?,?,?,?)',
                       (rs, year, factor, remaining, schedule_src))

    benchmark_src = c.execute('SELECT id FROM regulatory_sources WHERE code=?', ('EU-CBAM-BENCHMARKS-2025-2620',)).fetchone()['id']
    if not c.execute('SELECT 1 FROM cbam_benchmarks LIMIT 1').fetchone():
        for route, val in [('Blast furnace - basic oxygen furnace (BF-BOF)', '1.370'),
                             ('DRI-EAF', '0.481'), ('Scrap-EAF', '0.072'),
                             ('Electric arc furnace (EAF)', '0.072')]:
            c.execute('INSERT OR IGNORE INTO cbam_benchmarks(rule_set_id,sector,production_route,'
                       'benchmark_tco2e_per_t,confidence,source_id) VALUES(?,?,?,?,?,?)',
                       (rs, 'iron_steel', route, val, 'secondary_sourced', benchmark_src))

    defaults_src = c.execute('SELECT id FROM regulatory_sources WHERE code=?',
                              ('EU-CBAM-DEFAULTS-CORR-2026-1740',)).fetchone()['id']
    if not c.execute('SELECT 1 FROM default_values LIMIT 1').fetchone():
        rows = [
            (rs, 'iron_steel', '7208', '', 'India', '4.280', '0', 'tCO2e/t', 'secondary_sourced',
             'Secondary-sourced total-emissions figure for India / CN heading 7208 quoted from '
             'commentary on the corrected Annex I; verify against the primary Commission dataset.'),
            (rs, 'cement', '2523', '', 'Turkiye', '1.584', '0', 'tCO2e/t', 'secondary_sourced',
             'Secondary-sourced default value for Turkish Portland cement quoted from commentary '
             'on IR 2025/2621; verify against the primary Commission dataset.'),
            (rs, 'iron_steel', '72', '', '', '1.9800', '0.1400', 'tCO2e/t', 'illustrative',
             'ILLUSTRATIVE placeholder, not sourced from the Annex -- generic sector fallback only.'),
            (rs, 'aluminium', '76', '', '', '1.5400', '5.2000', 'tCO2e/t', 'illustrative',
             'ILLUSTRATIVE placeholder, not sourced from the Annex -- generic sector fallback only.'),
            (rs, 'cement', '25', '', '', '0.8600', '0.0900', 'tCO2e/t', 'illustrative',
             'ILLUSTRATIVE placeholder, not sourced from the Annex -- generic sector fallback only.'),
            (rs, 'fertilisers', '31', '', '', '1.7200', '0.3500', 'tCO2e/t', 'illustrative',
             'ILLUSTRATIVE placeholder, not sourced from the Annex -- generic sector fallback only.'),
        ]
        for rule_set_id, sector, cn_prefix, route, country, direct, indirect, unit, confidence, note in rows:
            total = str(Decimal(direct) + Decimal(indirect))
            c.execute('INSERT INTO default_values(rule_set_id,sector,cn_prefix,production_route,country,'
                       'direct_default,indirect_default,total_default,unit,confidence,markup_note,source_id) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (rule_set_id, sector, cn_prefix, route, country, direct, indirect, total, unit, confidence,
                        note, defaults_src))

    if not c.execute('SELECT 1 FROM methodologies LIMIT 1').fetchone():
        for code, name, kind, desc in [
            ('ACTUAL_VERIFIED', 'Actual emissions, verified', 'direct_actual',
             'Installation-reported actual emissions, verified by an accredited verifier.'),
            ('ACTUAL_UNVERIFIED', 'Actual emissions, not yet verified', 'direct_actual',
             'Installation-reported actual emissions pending verification. Usable for internal '
             'planning; not sufficient alone for a final declaration once verification is mandatory.'),
            ('DEFAULT_VALUE', 'Commission default value', 'direct_default',
             'Fallback used when actual/verified installation data is unavailable. Carries the '
             'regulatory default-value mark-up and increases certificate exposure.'),
            ('INDIRECT_ACTUAL', 'Indirect emissions, actual', 'indirect_actual',
             'Actual electricity-related indirect emissions where the sector requires them.'),
            ('INDIRECT_DEFAULT', 'Indirect emissions, default', 'indirect_default',
             'Default indirect emissions value where actual data is unavailable.'),
        ]:
            c.execute('INSERT INTO methodologies(code,name,kind,description,source_id) VALUES(?,?,?,?,?)',
                       (code, name, kind, desc, rules_src))

def seed_cn_reference(c):
    if c.execute('SELECT 1 FROM cn_reference LIMIT 1').fetchone():
        return
    rows = [
        ('72081000', 'Flat-rolled iron/steel, coils, hot-rolled', 'iron_steel', 'Iron and steel'),
        ('72091600', 'Flat-rolled iron/steel, cold-rolled', 'iron_steel', 'Iron and steel'),
        ('72131000', 'Bars and rods, hot-rolled, iron or non-alloy steel', 'iron_steel', 'Iron and steel'),
        ('72163100', 'U sections, iron or non-alloy steel', 'iron_steel', 'Iron and steel'),
        ('73041900', 'Seamless tubes, iron or steel', 'iron_steel', 'Iron and steel'),
        ('76011000', 'Unwrought aluminium, not alloyed', 'aluminium', 'Aluminium'),
        ('76041000', 'Aluminium bars, rods and profiles, not alloyed', 'aluminium', 'Aluminium'),
        ('76061190', 'Aluminium plates/sheets/strip, not alloyed', 'aluminium', 'Aluminium'),
        ('25231000', 'Cement clinkers', 'cement', 'Cement'),
        ('25232900', 'Portland cement, other', 'cement', 'Cement'),
        ('31021000', 'Urea', 'fertilisers', 'Fertilisers'),
        ('31051000', 'Fertiliser mixtures', 'fertilisers', 'Fertilisers'),
        ('28080000', 'Nitric acid; sulphonitric acids', 'fertilisers', 'Fertilisers'),
        ('28141000', 'Anhydrous ammonia', 'fertilisers', 'Fertilisers'),
    ]
    for code, desc, sector, cat in rows:
        c.execute('INSERT OR IGNORE INTO cn_reference(code,description,sector,aggregated_category) '
                   'VALUES(?,?,?,?)', (code, desc, sector, cat))
