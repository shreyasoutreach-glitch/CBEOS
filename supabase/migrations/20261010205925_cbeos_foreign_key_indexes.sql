-- Index single-column foreign keys that did not already have a covering index.
-- The schema is currently empty, so the Supabase advisor may report new indexes as unused until real workloads exist.
DO $cbeos$
DECLARE
  r record;
  idx_name text;
BEGIN
  FOR r IN
    SELECT c.conname, c.conrelid::regclass AS table_name, a.attname AS column_name
    FROM pg_constraint c
    JOIN pg_class t ON t.oid=c.conrelid
    JOIN pg_namespace n ON n.oid=t.relnamespace
    JOIN unnest(c.conkey) WITH ORDINALITY k(attnum,ord) ON true
    JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=k.attnum
    WHERE c.contype='f' AND n.nspname='public'
      AND array_length(c.conkey,1)=1
      AND NOT EXISTS (
        SELECT 1 FROM pg_index i
        WHERE i.indrelid=c.conrelid AND i.indisvalid
          AND i.indnkeyatts >= 1 AND i.indkey[0]=c.conkey[1]
      )
  LOOP
    idx_name := left('idx_cbeos_fk_' || r.table_name::text || '_' || r.column_name, 48)
                || '_' || substr(md5(r.conname),1,10);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (%I)', idx_name, r.table_name, r.column_name);
  END LOOP;
END
$cbeos$;
