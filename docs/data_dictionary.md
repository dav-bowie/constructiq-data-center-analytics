# Data Dictionary — ConstructIQ Star Schema

All tables reside in Amazon Redshift Serverless, schema: `public`.
Populated by the AWS Glue ETL job (`glue-etl/constructiq_etl.py`) on each run.
Snapshot date: September 30, 2025.

---

## Fact Tables

### `fact_project_cost`
One row per cost code per building. The primary table for all EVM calculations.
Source: Procore cost ledger export.

| Column | Type | Construction Meaning |
|---|---|---|
| `cost_key` | INTEGER | Source system row identifier from the Procore export |
| `building_id` | VARCHAR | Which of the four buildings this cost code belongs to (BLD-A through BLD-D) |
| `cost_code` | VARCHAR | Procore cost code — the most granular level of cost tracking (e.g. `01.10.001`) |
| `wbs_level_1` | VARCHAR | Top-level Work Breakdown Structure category the cost code belongs to (e.g. `01-SITEWORK`, `04-MEP`) |
| `wbs_level_2` | VARCHAR | Second-level WBS sub-category (e.g. `01.10-Earthwork`, `04.20-HVAC`) |
| `vendor_name` | VARCHAR | Standardized subcontractor or supplier name, fuzzy-matched to a canonical list to eliminate spelling variations |
| `contract_value` | BIGINT | Original awarded contract value in USD before any change orders |
| `approved_budget` | BIGINT | Current approved budget including all approved change orders — this is the BAC (Budget at Completion) for EVM purposes |
| `committed_cost` | BIGINT | Total committed cost: awarded contracts plus approved change orders in the pipeline |
| `actual_cost_to_date` | BIGINT | Real money spent and invoiced against this cost code through the snapshot date (the AC in EVM) |
| `forecasted_final_cost` | BIGINT | Project team's current forecast of what this cost code will cost at completion |
| `variance` | BIGINT | `approved_budget − forecasted_final_cost`. Negative = forecast over budget. Back-filled from budget math where missing in source data |
| `earned_value` | BIGINT | Budgeted value of work physically completed through the snapshot date (the EV in EVM) |
| `planned_value` | BIGINT | Budgeted value of work that was scheduled to be complete by the snapshot date (the PV in EVM) |
| `percent_complete_actual` | DOUBLE | Physical percent complete as reported by the contractor (0.0 to 1.0) |
| `percent_complete_baseline` | DOUBLE | Planned percent complete per the baseline schedule at the snapshot date (0.0 to 1.0) |
| `cpi` | DOUBLE | Cost Performance Index = EV / AC. Values below 1.0 mean over budget. Null if AC = 0 (work not yet started) |
| `spi` | DOUBLE | Schedule Performance Index = EV / PV. Values below 1.0 mean behind schedule. Null if PV = 0 |
| `eac` | DOUBLE | Estimate at Completion = Budget / CPI. Projected final cost if current efficiency continues. Null if CPI = 0 |
| `vac` | DOUBLE | Variance at Completion = Budget − EAC. Negative values indicate a projected overrun |
| `cost_variance_pct` | DOUBLE | `(Budget − Forecast) / Budget × 100`. Expresses the cost position as a percentage of budget |

---

### `fact_change_orders`
One row per change order. Tracks all scope changes submitted against the program.
Source: Change order log export.

| Column | Type | Construction Meaning |
|---|---|---|
| `change_order_id` | VARCHAR | Unique CO identifier assigned by the cost management system (e.g. `CO-1001`) |
| `building_id` | VARCHAR | Which building the scope change applies to |
| `co_type` | VARCHAR | Category of change order: `OCO` = Owner-directed change (owner's cost), `COR` = Contractor's request for compensation, `PCO` = Proposed change order (not yet formally submitted) |
| `description` | VARCHAR | Plain-language description of the scope change |
| `submitted_date` | DATE | Date the change order was formally submitted — normalized to YYYY-MM-DD from mixed source formats |
| `approved_date` | DATE | Date the CO was approved. Set to `9999-12-31` if the CO is still Pending or Under Review — this sentinel value allows pending COs to appear in reports without breaking date filters |
| `status` | VARCHAR | Current approval status: `Approved`, `Rejected`, `Pending`, `Under Review` |
| `cost_impact` | DOUBLE | Cost impact in USD. Positive = cost increase to the program |
| `schedule_impact_days` | INTEGER | Number of calendar days of schedule impact claimed by the CO |
| `co_approval_lag_days` | INTEGER | Days elapsed from submission to approval. Null for COs that are still pending — this is the field used for aging analysis |
| `responsible_party` | VARCHAR | The party whose actions originated the change (Owner, Contractor, Design Team, etc.) |
| `wbs_code` | VARCHAR | The WBS code this CO is charged to, for cost allocation |
| `wbs_level_1` | VARCHAR | Top-level WBS category for grouping and reporting |

---

### `fact_schedule`
One row per schedule activity. Source: Primavera P6 export.

| Column | Type | Construction Meaning |
|---|---|---|
| `activity_id` | VARCHAR | Unique activity identifier from the P6 schedule (e.g. `ACT-0001`) |
| `building_id` | VARCHAR | Which building this activity belongs to |
| `activity_name` | VARCHAR | Description of the construction activity (e.g. `Mass Excavation`, `Steel Erection`) |
| `wbs_level_1` | VARCHAR | Top-level WBS category this activity falls under |
| `wbs_code` | VARCHAR | Specific WBS code for this activity |
| `planned_start` | DATE | Baseline planned start date from the original approved schedule |
| `planned_finish` | DATE | Baseline planned finish date from the original approved schedule |
| `actual_start` | DATE | Actual date work began. Null if the activity has not yet started |
| `actual_finish` | DATE | Actual date work was completed. Null if the activity is still in progress |
| `baseline_duration` | INTEGER | Planned duration in calendar days from the approved baseline |
| `actual_duration` | INTEGER | Actual duration in calendar days. Null for activities not yet complete |
| `percent_complete` | DOUBLE | Physical percent complete as of the snapshot date (0.0 to 1.0) |
| `total_float_days` | INTEGER | Schedule float available in calendar days. Negative float = the activity is already delaying the project end date |
| `critical_path_flag` | VARCHAR | `Y` if this activity is on the critical path (any delay extends the overall project). `N` otherwise |

---

### `fact_pay_applications`
One row per contractor pay application per billing period.
Source: Pay application register.

| Column | Type | Construction Meaning |
|---|---|---|
| `pay_app_id` | VARCHAR | Unique identifier for this payment application (e.g. `PA-5001`) |
| `building_id` | VARCHAR | Which building the contractor is billing for |
| `period` | VARCHAR | The billing month in YYYY-MM format (e.g. `2023-06`) |
| `period_sequence` | INTEGER | Sequential billing period number starting from 1. Used to identify the most recent submission when contractors revise applications |
| `contractor_name` | VARCHAR | Standardized contractor name after fuzzy matching in the ETL |
| `trade` | VARCHAR | Trade classification (e.g. `GC` for general contractor, `Electrical`, `Mechanical`, `Structural`) |
| `scheduled_value` | BIGINT | Total contract value — the denominator for calculating percent billed |
| `work_completed_this_period` | BIGINT | Work invoiced in this billing period only (not cumulative) |
| `work_completed_to_date` | BIGINT | Cumulative work invoiced through this billing period |
| `stored_materials` | BIGINT | Value of materials delivered to site and stored but not yet installed. Contractors can bill for these under most contract forms |
| `total_earned` | BIGINT | `work_completed_to_date + stored_materials` — the total amount the contractor has earned the right to bill |
| `retainage_pct` | DOUBLE | The percentage of earned value withheld as retainage (typically 10.0%) |
| `retainage_held` | BIGINT | Cumulative dollar amount withheld as retainage. Released at substantial completion |
| `net_payment_due` | BIGINT | Amount actually payable this period after deducting retainage |
| `pay_app_status` | VARCHAR | `Certified` = approved for payment, `Submitted` = received but not yet reviewed, `Under Review` = in the approval process, `Rejected` = returned to contractor |

---

## Dimension Tables

### `dim_building`
One row per building. Provides static program metadata for joins and reporting.

| Column | Type | Construction Meaning |
|---|---|---|
| `building_id` | VARCHAR | Primary key. The four buildings: BLD-A, BLD-B, BLD-C, BLD-D |
| `campus` | VARCHAR | Name of the overall campus (`Northern Virginia Data Center Campus`) |
| `client` | VARCHAR | The owner / client (`Amazon Web Services`) |
| `program_value_usd` | BIGINT | Total program value in USD across all four buildings ($2,100,000,000) |
| `snapshot_date` | DATE | The reporting snapshot date that all fact data is aligned to (2025-09-30) |

---

### `dim_wbs`
One row per Work Breakdown Structure code. Provides the cost hierarchy for grouping and drill-down.

| Column | Type | Construction Meaning |
|---|---|---|
| `wbs_code` | VARCHAR | The specific WBS or cost code (e.g. `01.10.001`, `04.30.001`) |
| `wbs_level_1` | VARCHAR | Top-level WBS division (e.g. `01-SITEWORK`, `02-STRUCTURE`, `04-MEP`, `07-COMMISSIONING`) |
| `wbs_level_2` | VARCHAR | Second-level sub-category providing more specific scope description. Null for some codes that exist only at the top level |

---

### `dim_vendor`
One row per standardized vendor or subcontractor. Deduplicated via fuzzy name matching in the ETL.

| Column | Type | Construction Meaning |
|---|---|---|
| `vendor_id` | INTEGER | Sequential surrogate key generated by the ETL |
| `vendor_name` | VARCHAR | Canonical vendor name after standardization (e.g. `Turner Electric Co.` regardless of how it appeared in source systems) |
| `trade` | VARCHAR | Trade classification from pay application data. Null for vendors who appear in the cost ledger but have not yet submitted a pay application |

---

### `dim_date`
One row per calendar day from 2023-01-01 to 2026-12-31. Standard date dimension for time-series analysis in Power BI.

| Column | Type | Construction Meaning |
|---|---|---|
| `full_date` | DATE | The calendar date — primary key for this dimension |
| `date_key` | INTEGER | Integer surrogate key in YYYYMMDD format (e.g. 20250930). Used for efficient joins |
| `year` | INTEGER | Calendar year (2023–2026) |
| `quarter` | INTEGER | Calendar quarter (1–4) |
| `month` | INTEGER | Month number (1–12) |
| `month_name` | VARCHAR | Full month name (e.g. `September`) — used in report labels |
| `week_of_year` | INTEGER | ISO week number (1–53) |
| `day_of_week` | INTEGER | Day of week as an integer: 1 = Sunday, 7 = Saturday |
| `day_name` | VARCHAR | Full day name (e.g. `Tuesday`) |
| `is_weekend` | BOOLEAN | True if Saturday or Sunday — useful for filtering to business days only |
| `is_month_end` | BOOLEAN | True if the last day of the month — useful for period-end reporting snapshots |
| `fiscal_year` | INTEGER | Fiscal year — aligns with calendar year for this program |
| `fiscal_quarter` | INTEGER | Fiscal quarter — aligns with calendar quarter for this program |
