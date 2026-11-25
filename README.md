# Olist E-Commerce Analytics Engineering & BI Platform

End-to-end Analytics Engineering & BI platform combining the real **Olist Brazilian E-Commerce** dataset (~100k orders across 9 relational tables) with official macroeconomic series from the **Central Bank of Brazil (BCB — SGS API)** to evaluate real (IPCA inflation-adjusted) vs. nominal revenue growth, customer cohort retention & RFM segmentation, and logistics SLA impact on customer satisfaction.

## Target Architecture

- **Storage & Warehouse:** PostgreSQL 16 (Docker Compose on host port `5434`)
- **ELT Ingestion (`raw` schema):** Idempotent Python ingestion (`src/`) loading the 9 Olist CSV datasets and BCB SGS API series (IPCA monthly variation `433`, USD/BRL PTAX daily rate `1`) with local raw caching in `data/raw/`.
- **Transformations (`dbt Core` + `dbt-postgres`):**
  - `staging` (`stg_*` views): 1:1 cleaning, column standardization, and type casting.
  - `intermediate` (`int_*`): cumulative IPCA deflator index, USD conversion, payment reconciliation, logistics SLA metrics, `customer_unique_id` resolution, cohorts, and RFM.
  - `marts` (`fct_*`, `dim_*` tables): star schema ready for BI (`fct_orders`, `fct_order_items`, `dim_customers`, `dim_products`, `dim_sellers`, `dim_date`).
- **Data Quality & CI/CD:** `dbt test` (generic + singular business tests), `dbt docs`, and GitHub Actions.
- **BI Layer:** Power BI Desktop (3-page executive & operational dashboard).

## Project Roadmap

- [x] **Sprint 1:** Repository setup, Docker PostgreSQL 16, Python `.venv`, idempotent ELT ingestion into `raw` (Olist + BCB SGS API).
- [ ] **Sprint 2:** dbt Core setup, `staging` + `intermediate` models, initial `dbt test` suite.
- [ ] **Sprint 3:** Star schema `marts`, singular business tests, `dbt docs`, GitHub Actions CI.
- [ ] **Sprint 4:** Power BI Desktop semantic model, DAX measures, dashboard pages, and portfolio documentation.

## Sprint 1 — Quickstart

1. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
2. Start PostgreSQL 16 (port `5434`):
   ```bash
   docker compose up -d
   ```
3. Create virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   # Windows PowerShell: .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
4. Run idempotent ingestion into `raw`:
   ```bash
   python src/ingest_bcb.py
   python src/ingest_olist.py
   python src/verify_raw.py
   ```
