-- change_order_aging.sql
-- ConstructIQ | AWS Northern Virginia Data Center Campus
-- Purpose: Change order volume, cost exposure, and approval aging by building.
--
-- On a $2.1B program, unapproved change orders represent uncommitted cost risk.
-- T&T tracks aging to pressure contractors and the owner to resolve COs quickly.
-- Buckets follow industry standard: 0-15 days (on track), 16-30 days (at risk),
-- 30+ days (escalation required).
--
-- Pending COs use sentinel date 9999-12-31 for approved_date — those rows
-- are excluded from aging buckets and counted separately as open exposure.

SELECT
    co.building_id,
    co.wbs_level_1,
    co.co_type,
    co.status,

    -- Volume
    COUNT(*)                        AS co_count,
    SUM(co.cost_impact)             AS total_cost_impact,
    SUM(co.schedule_impact_days)    AS total_schedule_impact_days,
    AVG(co.cost_impact)             AS avg_cost_per_co,

    -- Aging buckets — only for approved COs where lag is known
    SUM(CASE
        WHEN co.co_approval_lag_days BETWEEN 0 AND 15 THEN 1 ELSE 0
    END) AS approved_0_to_15_days,

    SUM(CASE
        WHEN co.co_approval_lag_days BETWEEN 16 AND 30 THEN 1 ELSE 0
    END) AS approved_16_to_30_days,

    SUM(CASE
        WHEN co.co_approval_lag_days > 30 THEN 1 ELSE 0
    END) AS approved_over_30_days,

    -- Average approval cycle time for closed COs
    ROUND(AVG(
        CASE WHEN co.co_approval_lag_days IS NOT NULL
             THEN co.co_approval_lag_days END
    ), 1) AS avg_approval_days,

    -- Cost exposure from pending/under review COs (unresolved risk)
    SUM(CASE
        WHEN co.status IN ('Pending', 'Under Review') THEN co.cost_impact ELSE 0
    END) AS open_cost_exposure,

    SUM(CASE
        WHEN co.status IN ('Pending', 'Under Review') THEN 1 ELSE 0
    END) AS open_co_count,

    -- Rejected CO value (scope that was pushed back — useful for owner reporting)
    SUM(CASE
        WHEN co.status = 'Rejected' THEN co.cost_impact ELSE 0
    END) AS rejected_cost_value

FROM fact_change_orders co

GROUP BY
    co.building_id,
    co.wbs_level_1,
    co.co_type,
    co.status

ORDER BY
    co.building_id,
    total_cost_impact DESC;
