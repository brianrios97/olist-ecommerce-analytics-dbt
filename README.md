# Olist E-Commerce Analytics Engineering & BI Platform

Plataforma end-to-end de **Analytics Engineering & BI** sobre el dataset real de **Olist (Brasil, ~100k órdenes en 9 tablas)** enriquecido con series macroeconómicas oficiales del **Banco Central de Brasil (BCB — SGS API)** para analizar crecimiento real (deflactado por **IPCA**) vs. nominal, conversión **BRL/USD (PTAX)**, retención por cohortes/RFM e impacto del SLA logístico en la satisfacción del cliente.

## Arquitectura Objetivo

- **Infraestructura:** Docker Compose con PostgreSQL 16 (`localhost:5434`).
- **Capa `raw` (ELT inmutable en Python):**
  - 9 tablas CSV oficiales de Olist (`raw.olist_*`).
  - Series oficiales BCB SGS: inflación mensual IPCA serie `433` (`raw.bcb_ipca`) y tipo de cambio diario BRL/USD PTAX serie `1` (`raw.bcb_fx_usd_brl`), con reintentos, caché local y carga idempotente.
- **Capa de Transformación (`dbt Core` + `dbt-postgres`):** `staging` → `intermediate` → `marts` (esquema estrella).
- **Calidad y CI/CD:** `dbt test` (genéricos + singulares de negocio), `dbt docs` y GitHub Actions.
- **Capa BI:** Power BI Desktop (3 páginas analíticas).

## Roadmap por Sprints

- [x] **Sprint 1:** Estructura del repo, GitHub remote, Docker + PostgreSQL 16 e ingesta idempotente verificada en `raw` (Olist + API BCB).
- [ ] **Sprint 2:** Configuración de `dbt Core`, modelos `staging` + `intermediate` y primeros `dbt test`.
- [ ] **Sprint 3:** Modelos `marts` en esquema estrella, tests singulares de negocio, `dbt docs` y CI/CD en GitHub Actions.
- [ ] **Sprint 4:** Conexión en Power BI Desktop, medidas DAX, capturas y documentación final de portafolio.
