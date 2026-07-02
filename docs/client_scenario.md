# Client Scenario — AWS Northern Virginia Data Center Campus

## Program Overview

| Field | Detail |
|---|---|
| **Client** | Amazon Web Services (AWS) |
| **Program** | Northern Virginia Hyperscale Data Center Campus |
| **Location** | Northern Virginia, USA (Ashburn/Loudoun County corridor) |
| **Total Program Value** | $2.1 billion |
| **Total Capacity** | 200 megawatts (MW) IT load |
| **Buildings** | 4 active data center buildings |
| **Snapshot Date** | September 30, 2025 |
| **Program Manager** | Turner & Townsend |

---

## Why Northern Virginia

Northern Virginia is the world's largest data center market, home to over 70% of
global internet traffic. AWS has operated in the region since 2006 (us-east-1).
This campus represents the next generation of hyperscale infrastructure — purpose-built
for AI/ML workloads requiring high power density and ultra-low latency connectivity
to the existing AWS backbone.

---

## The Four Buildings

### BLD-A — Alpha
- **Status:** Over budget. CPI = 0.909.
- **Approved Budget:** ~$763M
- **EAC:** ~$840M (projected $77M overrun)
- **Description:** The first building on campus, furthest along in construction.
  Sitework, structural, and MEP systems are substantially complete. Cost pressure
  is concentrated in electrical fit-out and commissioning scope.

### BLD-B — Beta
- **Status:** Healthy. CPI = 1.025.
- **Approved Budget:** ~$729M
- **EAC:** ~$711M (projected $18M under budget)
- **Description:** Performing to plan. Lessons learned from BLD-A procurement
  were applied here — earlier subcontractor buyouts and tighter change order
  discipline have kept costs in check.

### BLD-C — Gamma
- **Status:** Critical — most at-risk. CPI = 0.868.
- **Approved Budget:** ~$723M
- **EAC:** ~$833M (projected $110M overrun)
- **Description:** The problem building. A CPI of 0.868 is a strong leading
  indicator of significant budget overrun at completion. Root causes include
  owner-directed scope changes on the MEP systems (OCOs), contractor productivity
  issues on the structural package, and late equipment deliveries that compressed
  the critical path. T&T is reporting this as a program-level risk requiring
  immediate corrective action.

### BLD-D — Delta
- **Status:** On track. CPI = 1.010.
- **Approved Budget:** ~$603M
- **EAC:** ~$597M (projected $6M under budget)
- **Description:** The newest building, benefiting from standardized designs and
  pre-negotiated rates from the BLD-A and BLD-B procurement cycles. Tracking
  closely to baseline.

---

## Source Systems (Simulated)

The raw data in this project simulates exports from three enterprise platforms
commonly used on hyperscale data center programs:

| System | Purpose | Data Exported |
|---|---|---|
| **Procore** | Construction project management | Cost ledger, change order log, pay applications |
| **Primavera P6** | Schedule management | Schedule progress, activity status, float analysis |
| **SAP** | ERP / financial management | (future integration) |

Each system exports data independently, on different schedules, in different
formats. The ETL pipeline's job is to normalize and join these feeds into a
single source of truth.

---

## Intentional Data Quality Issues

The raw CSVs were generated with real-world data quality problems to simulate
actual source system exports:

| Issue | Where | ETL Resolution |
|---|---|---|
| Mixed date formats (`2025-01-15`, `01/15/2025`, `15-Jan-2025`, `01-15-2025`) | All files | `F.coalesce()` across 6 `to_date()` patterns |
| Vendor name variations (`Turner Electric`, `Turner Elec.`, `TURNER ELECTRIC CO.`) | Cost ledger, pay apps | rapidfuzz fuzzy matching, 85-score threshold |
| Null `approved_date` on pending change orders | Change order log | Sentinel date 9999-12-31; excluded from aging calcs |
| Null `actual_start`/`actual_finish` on future activities | Schedule | Left as null — valid for activities not yet started |
| Missing `variance` on ~6% of cost ledger rows | Cost ledger | Back-filled as `approved_budget - forecasted_final_cost` |
| Mixed period formats (`2023-06`, `June 2023`) | Pay applications | Normalized via date coalesce pipeline |

---

## What T&T Delivers to the Client

Each month, Turner & Townsend produces:

1. **Executive Dashboard** — EVM summary per building with traffic light status
2. **Change Order Log** — Aging analysis, open cost exposure, approval cycle times
3. **Cash Flow Report** — Cumulative actual vs planned S-curve by building
4. **Pay Application Reconciliation** — Contractor billing verification
5. **Cost Variance Analysis** — WBS-level drill-down on where budget pressure originates

The ConstructIQ pipeline automates the data transformation underlying all five deliverables.
