-- change_order_aging.sql
-- ConstructIQ | AWS Northern Virginia Data Center Campus
-- Used in Power BI Page 3: Change Order Log
--
-- Buckets pending COs by days outstanding to identify approval bottlenecks.
-- On a $2.1B program, unresolved COs represent uncommitted cost risk to the owner.
-- Industry standard aging buckets: 0-15 days (on track), 16-30 days (at risk),
-- 30+ days (escalation required — T&T flags these to the program director).
--
-- Pending/Under Review COs have null co_approval_lag_days (sentinel date 9999-12-31
-- was used for approved_date in the ETL). They appear in co_count and total_cost_impact
-- but are excluded from aging buckets.

SELECT
    building_id,
    status,
    COUNT(*)                                                                        AS co_count,
    SUM(cost_impact)                                                                AS total_cost_impact,
    AVG(co_approval_lag_days)                                                       AS avg_approval_lag,
    SUM(CASE WHEN co_approval_lag_days BETWEEN 0 AND 15  THEN 1 ELSE 0 END)        AS bucket_0_15_days,
    SUM(CASE WHEN co_approval_lag_days BETWEEN 16 AND 30 THEN 1 ELSE 0 END)        AS bucket_16_30_days,
    SUM(CASE WHEN co_approval_lag_days > 30              THEN 1 ELSE 0 END)        AS bucket_30_plus_days
FROM fact_change_orders
GROUP BY building_id, status
ORDER BY building_id, status;
