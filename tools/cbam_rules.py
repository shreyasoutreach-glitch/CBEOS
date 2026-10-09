"""Fail-closed selectors for CBAM rules while source reconciliation is incomplete."""
from decimal import Decimal,InvalidOperation
class ValidationBlocked(ValueError):pass
def markup_percent(sector,year):
 if type(year) is not int or year<2026 or year>2040:raise ValidationBlocked('Unsupported reporting year')
 s=str(sector or '').strip().casefold()
 if s in {'fertiliser','fertilisers','fertilizer','fertilizers'}:return Decimal('1')
 if s in {'cement','iron_steel','iron and steel','iron & steel','steel','aluminium','aluminum','hydrogen'}:return Decimal('10' if year==2026 else '20' if year==2027 else '30')
 raise ValidationBlocked(f'No configured mark-up for sector {sector!r}')
def calculate_default_total(row,year):
 if row.get('approval_status')!='approved':raise ValidationBlocked('Staged or unapproved values cannot be used for calculation')
 state=row.get('value_state');selected_country=row.get('country');raw=row.get('total_tco2e_per_t')
 if state=='fallback_required':
  raw=row.get('fallback_candidate_total');selected_country=row.get('fallback_source_country')
  if raw is None or not selected_country or not row.get('fallback_candidate_unique',False):raise ValidationBlocked('Fallback candidate is not uniquely reconciled and approved')
 elif state!='numeric' or raw is None:raise ValidationBlocked(f'Unsupported default value state: {state!r}')
 try:base=Decimal(str(raw))
 except InvalidOperation as exc:raise ValidationBlocked('Default total is not numeric') from exc
 if not base.is_finite() or base<0:raise ValidationBlocked('Invalid total-emissions value')
 pct=markup_percent(row.get('sector'),year);marked=(base*(Decimal('1')+pct/Decimal('100'))).quantize(Decimal('0.000001'))
 if not row.get('source_sha256'):raise ValidationBlocked('Source hash is required')
 return {'base_total_tco2e_per_t':format(base,'f'),'markup_percent':format(pct,'f'),'marked_total_tco2e_per_t':format(marked,'f'),'reporting_year':year,'selected_country':selected_country,'source_sha256':row['source_sha256'],'rule_status':'validation_only_not_legal_signoff'}
def choose_benchmark(row,column,required_route=None):
 if column not in {'a','b'}:raise ValidationBlocked('Benchmark column must be explicit')
 if row.get('approval_status')!='approved':raise ValidationBlocked('Unapproved benchmark cannot be used')
 state=row.get(f'column_{column}_state');raw=row.get(f'column_{column}_bmg_tco2e_per_t')
 if state!='numeric' or raw is None:raise ValidationBlocked('Selected benchmark column is not numeric')
 route=row.get(f'column_{column}_route')
 if required_route and route and route.casefold()!=required_route.casefold():raise ValidationBlocked('Production route mismatch')
 if required_route and not route and not row.get('route_independent_approved',False):raise ValidationBlocked('Route-independent benchmark requires explicit approval')
 if not row.get('source_sha256'):raise ValidationBlocked('Source hash is required')
 try:value=Decimal(str(raw))
 except InvalidOperation as exc:raise ValidationBlocked('Benchmark not numeric') from exc
 if not value.is_finite() or value<0:raise ValidationBlocked('Invalid benchmark')
 return value
