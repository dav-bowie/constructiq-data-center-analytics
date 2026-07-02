-- cash_flow_forecast.sql
-- ConstructIQ | AWS Northern Virginia Data Center Campus
-- Used in Power BI Page 4: Cash Flow (S-Curve)
--
-- Shows cumulative spend trajectory per building over time.
-- Cash flow is reported to the client's finance team each period to confirm
-- draw-down against the program budget is tracking to the S-curve baseline.
-- An S-curve running ahead of forecast = cash consumed faster than planned.
-- An S-curve running behind = possible schedule slippage or billing delays.
--
-- Source: fact_pay_applications. work_completed_to_date is already cumulative
-- per contractor per period — summing by building and period gives total program
-- cash out position at each point in time.

SELECT
    building_id,
    period,
    period_sequence,
    SUM(work_completed_this_period)   AS monthly_spend,
    SUM(work_completed_to_date)       AS cumulative_spend,
    SUM(scheduled_value)              AS scheduled_value,
    SUM(retainage_held)               AS retainage_held,
    SUM(net_payment_due)              AS net_payment_due
FROM fact_pay_applications
GROUP BY building_id, period, period_sequence
ORDER BY building_id, period_sequence;
