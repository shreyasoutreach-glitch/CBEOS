"""Validation-only CBAM rule selectors; never imply source approval."""
from decimal import Decimal,InvalidOperation
class ValidationBlocked(ValueError):pass
def markup_percent(sector:str,year:int)->Decimal:
 if type(year) is not int or not 2026<=year<=2040:raise ValidationBlocked('Unsupported reporting year')
 s=(sector or '').strip().casefold()
 if s in {'fertilizer','fertilisers','fertilizers'}:return Decimal('1')
 if s in {'cement','iron_steel','iron and steel','steel','aluminium','aluminum','hydrogen'}:return Decimal('10' if year==2026 else '20' if year==2027 else '30')
 raise ValidationBlocked(f'No legally configured markup for sector {sector!r}')
def apply_default_markup(row:dict,year:int)->dict:
 state=row.get('value_state');value=row.get('total_tco2e_per_t');selected=row.get('country')
 if state=='fallback_required':
  value=row.get('fallback_candidate_total');selected=row.get('fallback_source_country')
  if value is None or not selected:raise ValidationBlocked('Country default is absent/dashed and no unique fallback was reconciled')
 elif state!='numeric' or value is None:raise ValidationBlocked(f'Unsupported default-value state: {state!r}')
 try:base=Decimal(str(value))
 except InvalidOperation as e:raise ValidationBlocked('Default value is not numeric') from e
 if not base.is_finite() or base<0:raise ValidationBlocked('Invalid base default value')
 pct=markup_percent(row.get('sector'),year);marked=(base*(Decimal('1')+pct/Decimal('100'))).quantize(Decimal('0.000001'))
 return {'base_total_tco2e_per_t':format(base,'f'),'markup_percent':format(pct,'f'),'marked_total_tco2e_per_t':format(marked,'f'),'reporting_year':year,'selected_country':selected,'source_sheet':row.get('source_sheet'),'source_row':row.get('source_row'),'source_sha256':row.get('source_sha256'),'rule_status':'validation_only_not_approved_for_declaration'}
def choose_benchmark(row:dict,column:str,required_route:str|None=None)->Decimal:
 if column not in {'a','b'}:raise ValidationBlocked('Benchmark column must be explicit: a or b')
 state=row.get(f'column_{column}_state');raw=row.get(f'column_{column}_bmg_tco2e_per_t')
 if state!='numeric' or raw is None:raise ValidationBlocked(f'Benchmark column {column.upper()} is not numeric')
 route=row.get(f'column_{column}_route')
 if required_route and route and route.casefold()!=required_route.casefold():raise ValidationBlocked(f'Benchmark production route mismatch: required {required_route}, found {route}')
 if required_route and not route and not row.get('route_independent_approved',False):raise ValidationBlocked('Blank benchmark route requires explicit legal approval as route-independent')
 try:value=Decimal(str(raw))
 except InvalidOperation as e:raise ValidationBlocked('Benchmark value is not numeric') from e
 if not value.is_finite() or value<0:raise ValidationBlocked('Invalid benchmark value')
 return value
