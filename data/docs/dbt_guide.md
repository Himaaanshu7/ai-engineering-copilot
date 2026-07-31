# dbt (data build tool) — Complete Reference

## What is dbt?
dbt is a transformation framework that lets data analysts and engineers write SQL SELECT statements and dbt handles the rest: materialization, dependency management, testing, documentation, and lineage.

dbt only handles the T in ELT. You still need a loader (Airbyte, Fivetran, Stitch) and a data warehouse.

## Core Concepts

### Models
A model is a SQL SELECT statement in a `.sql` file. dbt compiles it and creates a table or view.

```sql
-- models/marts/revenue_by_region.sql
WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
),
regions AS (
    SELECT * FROM {{ ref('dim_regions') }}
)
SELECT
    r.region_name,
    SUM(o.revenue) AS total_revenue,
    COUNT(DISTINCT o.customer_id) AS unique_customers
FROM orders o
JOIN regions r ON o.region_id = r.id
GROUP BY 1
```

### ref() and source()
- `{{ ref('model_name') }}` — reference another dbt model; dbt builds the DAG automatically
- `{{ source('schema', 'table') }}` — reference a raw source table

### Materializations
```yaml
# dbt_project.yml
models:
  my_project:
    staging:
      +materialized: view       # fast, no storage, always fresh
    marts:
      +materialized: table      # persisted, slow to build
    +materialized: incremental  # only process new rows
```

| Materialization | When to Use |
|---|---|
| view | Staging, lightweight transforms, always-fresh data |
| table | Final marts, complex/expensive queries |
| incremental | Large tables where re-computing everything is too slow |
| ephemeral | CTEs you only use in one model; no object created in warehouse |

### Incremental Models
```sql
-- models/marts/events.sql
{{ config(materialized='incremental', unique_key='event_id') }}

SELECT event_id, user_id, event_type, created_at
FROM {{ source('raw', 'events') }}

{% if is_incremental() %}
  WHERE created_at > (SELECT MAX(created_at) FROM {{ this }})
{% endif %}
```

## Tests

### Generic Tests (built-in)
```yaml
# models/schema.yml
models:
  - name: orders
    columns:
      - name: order_id
        tests:
          - not_null
          - unique
      - name: status
        tests:
          - accepted_values:
              values: ['pending', 'shipped', 'delivered', 'cancelled']
      - name: customer_id
        tests:
          - relationships:
              to: ref('customers')
              field: id
```

### Singular Tests (custom SQL)
```sql
-- tests/assert_revenue_positive.sql
SELECT order_id
FROM {{ ref('orders') }}
WHERE revenue < 0
-- Test passes if 0 rows returned
```

## dbt Project Structure
```
my_project/
├── models/
│   ├── staging/           # 1:1 with source tables, light cleaning
│   │   ├── _sources.yml   # source definitions
│   │   └── stg_orders.sql
│   ├── intermediate/      # business logic building blocks
│   └── marts/             # final consumption layer
│       ├── finance/
│       └── marketing/
├── tests/                 # singular tests
├── macros/                # reusable Jinja functions
├── seeds/                 # CSV files loaded as tables
├── snapshots/             # SCD Type 2 history tables
└── dbt_project.yml
```

## Jinja Macros
```sql
-- macros/cents_to_dollars.sql
{% macro cents_to_dollars(column_name) %}
    ({{ column_name }} / 100.0)::NUMERIC(10, 2)
{% endmacro %}

-- Usage in a model:
SELECT {{ cents_to_dollars('amount_cents') }} AS amount_dollars
```

## Snapshots (SCD Type 2)
```sql
-- snapshots/customer_snapshot.sql
{% snapshot customer_snapshot %}
    {{
        config(
            target_schema='snapshots',
            unique_key='id',
            strategy='timestamp',
            updated_at='updated_at',
        )
    }}
    SELECT * FROM {{ source('app', 'customers') }}
{% endsnapshot %}
```

## dbt Commands
```bash
dbt run                    # Run all models
dbt run --select marts     # Run only mart models
dbt test                   # Run all tests
dbt build                  # run + test together
dbt docs generate          # Generate docs site
dbt docs serve             # Serve docs locally
dbt compile                # Compile Jinja without running
dbt debug                  # Check connection
```

## dbt Best Practices
1. **Staging models** should be 1:1 with sources; no joins, just renaming/casting
2. **Mart models** should be optimized for consumption — no raw column names
3. **Use schema.yml** for all models — not just for tests, but for documentation
4. **Prefix staging models** with `stg_`, intermediate with `int_`, marts without prefix
5. **Never use SELECT *** in dbt models — explicit columns make lineage clear
6. **Incremental strategy**: use `unique_key` to handle late-arriving data

## dbt vs Stored Procedures
| | dbt | Stored Procedures |
|---|---|---|
| Version control | Git-native | Hard |
| Testing | Built-in | Manual |
| Documentation | Auto-generated | Manual |
| Lineage | Visual DAG | None |
| Language | SQL + Jinja | SQL/PL/pgSQL |
| When to use | Analytics engineering | OLTP, complex procedural logic |
