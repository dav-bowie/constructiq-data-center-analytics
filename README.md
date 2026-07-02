# ConstructIQ — Hyperscale Data Center Cost Control Pipeline

End-to-end data engineering and analytics pipeline for a fictional $2.1B, 200MW AWS data center campus in Northern Virginia. Built to mirror the project controls workflow Turner & Townsend delivers on hyperscale programs — automated data ingestion, EVM metric calculation, and executive dashboard delivery.

---

## The Business Problem

A $2.1 billion construction program running four buildings simultaneously generates cost data from Procore, schedule data from Primavera P6, and payment data from contractor submittals — all in different formats, on different export schedules, with different naming conventions for the same vendors. Without automation, project controls analysts spend most of their week manually cleaning spreadsheets. By the time the data is ready, it is already stale and the program review meeting is tomorrow.

ConstructIQ solves this by automating the full data flow. Raw exports land in S3. The Glue ETL normalizes and transforms them. By Monday morning, the Power BI dashboard is refreshed with current CPI, SPI, cash flow, and change order exposure across all four buildings — no manual intervention.

**The insight that matters most:** BLD-C (Gamma) is tracking $110 million over its $490M budget, detectable months before construction completes. A CPI of 0.868 means for every dollar spent on that building, only $0.87 of budgeted work is being delivered. The dashboard surfaces this in the first 10 seconds of the program review meeting so the Turner & Townsend team can focus the conversation on corrective action, not data cleanup.

---

## Who the Client Is

**Amazon Web Services** is building a 200MW hyperscale data center campus in Northern Virginia — the world's largest data center market. The campus has four active buildings at different stages of construction. Turner & Townsend is engaged as Owner's Representative with a mandate for digital project controls.

| Building | Capacity | Budget | Phase | CPI |
|---|---|---|---|---|
| BLD-A (Alpha) | 60 MW | $580M | MEP Fit-Out | 0.909 — Over budget |
| BLD-B (Beta) | 50 MW | $510M | Shell Complete | 1.025 — Healthy |
| BLD-C (Gamma) | 50 MW | $490M | MEP Fit-Out | **0.868 — Critical** |
| BLD-D (Delta) | 40 MW | $420M | Foundation | 1.010 — On track |

AWS pre-sells data center capacity to enterprise customers years in advance. A building that finishes late or over budget has direct revenue consequences for the client — which is why the T&T team needs real-time visibility, not a monthly spreadsheet.

---

## Decisions the Dashboard Enables

| Report Page | Business Question It Answers |
|---|---|
| **Executive Summary** | Which buildings need immediate attention this week? |
| **EVM Performance** | Is cost and schedule performance trending better or worse month-over-month? |
| **Change Order Log** | Which open change orders represent the largest unresolved cost exposure? |
| **Cash Flow** | Is program draw-down tracking to the finance team's S-curve baseline? |
| **Cost Variance Drill-Through** | Which specific work packages are driving the overrun on BLD-C? |

---

## Architecture

```
┌──────────────────┐     ┌─────────────────┐     ┌───────────────────────┐     ┌─────────────────────┐     ┌─────────────┐
│  Source Systems  │     │   Amazon S3     │     │    AWS Glue ETL       │     │  Redshift Serverless│     │  Power BI   │
│                  │     │                 │     │                       │     │                     │     │             │
│ Procore          │────▶│ Raw CSV zone    │────▶│ PySpark job           │────▶│ 4 fact tables       │────▶│ 5 report    │
│ Primavera P6     │     │ 4 CSV files     │     │ Date normalization    │     │ 4 dimension tables  │     │ pages       │
│ Pay app register │     │                 │     │ Vendor fuzzy match    │     │                     │     │             │
└──────────────────┘     └─────────────────┘     │ EVM calculations      │     └─────────────────────┘     └─────────────┘
                                                 │ Star schema build     │
                                                 └───────────────────────┘
```

**S3** holds raw CSV exports as the landing zone and hosts the Glue job script.

**AWS Glue** runs `constructiq_etl.py` — a PySpark job that normalizes messy source data, applies fuzzy vendor name matching, calculates EVM metrics, and builds the star schema. Runs on managed Spark infrastructure (no cluster to maintain).

**Redshift Serverless** stores the clean star schema — 4 fact tables and 4 dimension tables — and serves as the query engine for Power BI.

**Power BI** connects to Redshift via ODBC. DAX measures recalculate CPI and SPI from base components (not from pre-aggregated columns) so all report slicing produces mathematically correct results.

---

## Dashboard Pages

### Page 1 — Executive Summary
KPI cards showing CPI, SPI, EAC, and VAC for each building. Traffic light status (Green / Amber / Red) based on CPI thresholds. Designed for the first 5 minutes of the monthly program review meeting with the client's capital projects leadership.

### Page 2 — EVM Performance
CPI and SPI trend lines over time for all four buildings. Scatter plot positioning each building by cost vs schedule performance. Makes deteriorating trends visible before they become critical overruns.

### Page 3 — Change Order Log
Aging analysis with 0–15 / 16–30 / 30+ day buckets. Total open cost exposure from pending and under-review COs. Waterfall chart of approved vs rejected vs pending cost impact by building.

### Page 4 — Cash Flow
S-curve showing cumulative actual spend vs planned baseline per building. Monthly burn rate chart. Identifies buildings where cash draw-down is running ahead of or behind the finance team's forecast.

### Page 5 — Cost Variance Drill-Through
Matrix of cost variance by WBS level 1 category and building. Conditional formatting on variance percentage. Click-through to cost code detail to identify the specific work packages driving overruns on BLD-C.

---

## EVM Answer Key

Validated output from Redshift — snapshot date September 30, 2025:

| Building | CPI | SPI | EAC | VAC | Status |
|---|---|---|---|---|---|
| BLD-A (Alpha) | 0.909 | 1.000 | $840,430,728 | −$77M | Over budget |
| BLD-B (Beta) | 1.025 | 0.988 | $710,678,388 | +$18M | Healthy |
| BLD-C (Gamma) | **0.868** | 0.992 | **$832,568,639** | **−$110M** | **Critical** |
| BLD-D (Delta) | 1.010 | 1.003 | $597,160,619 | +$6M | On track |

Run `sql/evm_summary_by_building.sql` against Redshift to reproduce these results.

---

## Data Sources and Intentional Messiness

The four raw CSVs simulate real-world export problems from enterprise construction systems. These are the issues that break naive pipelines and require a purpose-built ETL:

| Data Quality Issue | Where | ETL Solution |
|---|---|---|
| 4 different date formats (`2025-01-15`, `01/15/2025`, `15-Jan-2025`, `01-15-2025`) | All files | `F.coalesce()` cascade across 6 `to_date()` format patterns |
| Vendor name variations (`Turner Electric`, `Turner Elec.`, `TURNER ELECTRIC CO.`) | Cost ledger, pay apps | rapidfuzz `token_sort_ratio` ≥ 85 threshold → canonical name |
| Null `approved_date` on pending change orders | Change order log | Sentinel date `9999-12-31`; these rows excluded from aging bucket calculations |
| Null `actual_start` / `actual_finish` on future activities | Schedule | Left as null — valid for activities not yet started, not a data error |
| Missing `variance` on ~6% of cost ledger rows | Cost ledger | Back-filled as `approved_budget − forecasted_final_cost` |
| Cumulative billing figures in pay applications | Pay applications | `MAX(period_sequence)` per contractor per building to get current position |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Raw data storage | Amazon S3 |
| ETL compute | AWS Glue 4.0 (Spark 3.3, Python 3.10) |
| Fuzzy name matching | rapidfuzz 3.9.3 |
| Analytical warehouse | Amazon Redshift Serverless |
| Dashboard | Power BI Desktop |
| ETL language | PySpark |
| Analytical queries | SQL (Redshift / PostgreSQL dialect) |
| IAM and secrets | AWS IAM roles, Glue Data Catalog connections |
| Version control | Git / GitHub |

---

## How to Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/dav-bowie/constructiq-data-center-analytics.git
cd constructiq-data-center-analytics

# 2. Install Python dependencies
pip install -r glue-etl/requirements.txt

# 3. Regenerate raw data (already committed, but can be rebuilt)
python data-generation/generate_raw_data.py

# 4. Upload raw CSVs to S3
aws s3 cp data-generation/raw/cost_ledger_raw.csv       s3://constructiq-raw/procore-cost-ledger/
aws s3 cp data-generation/raw/change_order_log_raw.csv  s3://constructiq-raw/change-order-log/
aws s3 cp data-generation/raw/schedule_progress_raw.csv s3://constructiq-raw/schedule-progress/
aws s3 cp data-generation/raw/pay_applications_raw.csv  s3://constructiq-raw/pay-applications/

# 5. Upload the ETL script to S3
aws s3 cp glue-etl/constructiq_etl.py s3://constructiq-raw/scripts/

# 6. In the AWS Glue console, create a Spark job with:
#    - Script:     s3://constructiq-raw/scripts/constructiq_etl.py
#    - IAM role:   AWSGlueServiceRole-ConstructIQ
#    - Glue ver:   4.0 (Spark 3.3, Python 3.10)
#    - Worker:     G.1X, 2 workers
#    - Parameters: --additional-python-modules rapidfuzz==3.9.3
#                  --REDSHIFT_CONNECTION constructiq-redshift

# 7. Run the Glue job — all 8 tables load in a single execution

# 8. Validate output against the EVM answer key
#    Run sql/evm_summary_by_building.sql in Redshift Query Editor

# 9. Connect Power BI Desktop to Redshift via ODBC (Amazon Redshift ODBC driver)
```

**Note:** `constructiq_etl.py` requires the AWS Glue runtime and cannot run locally as-is. The `glue-etl/stubs/awsglue/` directory and `pyrightconfig.json` enable local type checking without the runtime — no import errors in the editor.

---

## Project Structure

```
constructiq-data-center-analytics/
│
├── README.md                           # This file
│
├── architecture/
│   └── pipeline_diagram.png            # End-to-end pipeline architecture diagram
│
├── data-generation/
│   ├── generate_raw_data.py            # Python script that generates the 4 raw CSVs
│   └── raw/
│       ├── cost_ledger_raw.csv         # Simulated Procore cost export — intentionally messy
│       ├── change_order_log_raw.csv    # Simulated change order register
│       ├── schedule_progress_raw.csv   # Simulated Primavera P6 export
│       └── pay_applications_raw.csv    # Simulated contractor billing register
│
├── glue-etl/
│   ├── constructiq_etl.py              # Main ETL — 9 sections, 8 output tables
│   ├── pyrightconfig.json              # Pyright config pointing at awsglue stubs
│   ├── requirements.txt                # pyspark==3.5.1, rapidfuzz==3.9.3
│   └── stubs/awsglue/                  # Local .pyi stubs for awsglue (runtime-only package)
│
├── sql/
│   ├── evm_summary_by_building.sql     # CPI, SPI, EAC, VAC per building
│   ├── change_order_aging.sql          # CO count, cost exposure, aging buckets
│   ├── cash_flow_forecast.sql          # Monthly and cumulative spend by building
│   ├── pay_app_reconciliation.sql      # Billed vs certified vs retainage by contractor
│   └── cost_variance_by_wbs.sql        # Top 10 WBS codes by cost overrun
│
├── powerbi/
│   └── screenshots/                    # Dashboard page screenshots
│       ├── Executive_Summary.png
│       ├── EVM_Performance.png
│       ├── Change_Order_Log.png
│       ├── Cash_Flow.png
│       └── Cost_Variance.png
│
└── docs/
    ├── evm_methodology.md              # EVM concepts, formulas, answer key, calculation rules
    ├── client_scenario.md              # Fictional AWS program brief, building details, T&T role
    └── data_dictionary.md              # All 8 tables documented field by field
```

---

## About This Project

Built by David Nguyen as a pre-employment portfolio project ahead of joining **Turner & Townsend** as a **Project Analyst, Digital** on August 10, 2026 through their Graduate Development Program.

The architecture, domain logic, data quality challenges, and EVM methodology reflect real hyperscale data center program delivery work — not a generic data engineering tutorial. Every design decision in the pipeline is grounded in how T&T actually manages cost and schedule reporting on major capital programs.

*Turner & Townsend is a global professional services firm specializing in program management, cost management, and project management across infrastructure, real estate, and natural resources sectors.*
