-- cash_flow_forecast.sql
-- ConstructIQ | AWS Northern Virginia Data Center Campus
-- Purpose: Monthly cash flow — actual billings vs cumulative program spend.
--
-- Cash flow is reported to the client's finance team each period to confirm
-- that draw-down against the program budget is tracking to the S-curve baseline.
-- An S-curve that runs ahead of forecast = cash being consumed faster than planned.
-- An S-curve that runs behind = possible schedule slippage or billing delays.
--
-- Source: fact_pay_applications, which records contractor payment applications
-- each month. work_completed_to_date is cumulative; to get monthly spend we
-- use MAX(work_completed_to_date) per contractor per period (latest submission).

WITH latest_pay_app_per_contractor AS (
    -- Each contractor may submit multiple revisions in a period.
    -- Take the highest period_sequence (most recent) to avoid double-counting.
    SELECT
        building_id,
        contractor_name,
        period,
        period_sequence,
        work_completed_this_period,
        work_completed_to_date,
        total_earned,
        net_payment_due,
        retainage_held,
        pay_app_status
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY building_id, contractor_name, period
                ORDER BY period_sequence DESC
            ) AS rn
        FROM fact_pay_applications
    ) ranked
    WHERE rn = 1
),

monthly_by_building AS (
    SELECT
        building_id,
        period,

        -- Monthly cash out (this period's billings across all contractors)
        SUM(work_completed_this_period)     AS monthly_work_billed,
        SUM(net_payment_due)                AS monthly_net_payment,
        SUM(retainage_held)                 AS monthly_retainage_withheld,

        -- Count of active contractors billing this period
        COUNT(DISTINCT contractor_name)     AS active_contractors,

        -- Certified vs pending split — certified = cash actually released
        SUM(CASE WHEN pay_app_status = 'Certified'
                 THEN net_payment_due ELSE 0 END)   AS certified_payment,
        SUM(CASE WHEN pay_app_status != 'Certified'
                 THEN net_payment_due ELSE 0 END)   AS pending_payment

    FROM latest_pay_app_per_contractor
    GROUP BY building_id, period
)

SELECT
    m.building_id,
    b.campus,
    m.period,

    m.monthly_work_billed,
    m.monthly_net_payment,
    m.monthly_retainage_withheld,
    m.active_contractors,
    m.certified_payment,
    m.pending_payment,

    -- Cumulative spend to date (S-curve value) — running sum over time per building
    SUM(m.monthly_work_billed) OVER (
        PARTITION BY m.building_id
        ORDER BY m.period
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_work_billed,

    SUM(m.monthly_net_payment) OVER (
        PARTITION BY m.building_id
        ORDER BY m.period
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_net_paid

FROM monthly_by_building m
JOIN dim_building b ON m.building_id = b.building_id

ORDER BY
    m.building_id,
    m.period;
