# Clean install proof

Run against a **new empty database** (`fast_livery_clean`) on the production host,
so the migration chain is proven to build the whole schema from zero.

```
database: fast_livery_clean (created empty)
migrations: 0037 -> 0038_ideal_customer_profile -> 0039_products -> 0040_agency_meta_app
alembic head: 0040_agency_meta_app
tables created: 43
key tables present: agencies agents clients conversations messages products users whatsapp_cloud_channels
result: PASS
```

## What this proves

- The migration chain has no gaps and runs on an empty database.
- No table is created by hand outside Alembic.
- The schema the app expects is reproducible.

## What this does not prove

- Application behaviour against that schema (no seed data was loaded).
- The pivot migration `0041_marketing_foundation` (branch only, not merged).

The production database was not modified: the clean database is separate and can
be dropped with `DROP DATABASE fast_livery_clean`.
