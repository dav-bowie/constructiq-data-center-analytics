-- pay_app_reconciliation.sql
-- ConstructIQ | AWS Northern Virginia Data Center Campus
-- Purpose: Reconcile total billed vs approved vs retainage held by contractor.
--
-- Pay app reconciliation is a monthly deliverable on T&T-managed programs.
-- The project controls team verifies that what contractors have billed matches
-- what has been approved, and confirms retainage is being withheld correctly.
-- Retainage (typically 10%) is held back until substantial completion as a
-- performance guarantee — incorrect retainage creates legal and cash flow risk.
--
-- This query uses the latest pay app per contractor per building (MAX period_sequence)
-- to get current cumulative totals. Earlier periods are included for trend analysis.

WITH latest_period_per_contractor AS (
    -- Get the most recent submission for each contractor per building.
    -- Cumulative fields (work_completed_to_date, total_earned) reflect
    -- the full program-to-date position as of the latest billing period.
    SELECT
        building_id,
        contractor_name,
        trade,
        period,
        period_sequence,
        scheduled_value,
        work_completed_to_date,
        total_earned,
        retainage_held,
        net_payment_due,
        pay_app_status
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY building_id, contractor_name
                ORDER BY period_sequence DESC
            ) AS rn
        FROM fact_pay_applications
    ) ranked
    WHERE rn = 1
)

SELECT
    lp.building_id,
    b.campus,
    lp.contractor_name,
    lp.trade,
    lp.period                               AS latest_billing_period,
    lp.pay_app_status                       AS latest_status,

    -- Contract position
    lp.scheduled_value                      AS contract_value,
    lp.work_completed_to_date               AS total_billed_to_date,
    lp.total_earned                         AS total_earned_incl_materials,
    lp.retainage_held                       AS total_retainage_withheld,
    lp.net_payment_due                      AS net_amount_payable,

    -- Percent billed against contract
    ROUND(
        lp.work_completed_to_date
        / NULLIF(lp.scheduled_value, 0) * 100
    , 1) AS pct_contract_billed,

    -- Effective retainage rate — should be ~10% per contract terms
    ROUND(
        lp.retainage_held
        / NULLIF(lp.total_earned, 0) * 100
    , 2) AS effective_retainage_pct,

    -- Retainage variance from expected 10% — flags incorrect withholding
    ROUND(
        lp.retainage_held - (lp.total_earned * 0.10)
    , 0) AS retainage_variance_vs_10pct,

    -- Remaining contract value yet to be billed
    lp.scheduled_value - lp.work_completed_to_date AS remaining_contract_value

FROM latest_period_per_contractor lp
JOIN dim_building b ON lp.building_id = b.building_id

ORDER BY
    lp.building_id,
    lp.trade,
    lp.contractor_name;
