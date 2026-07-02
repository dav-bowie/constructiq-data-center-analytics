-- cost_variance_by_wbs.sql
-- ConstructIQ | AWS Northern Virginia Data Center Campus
-- Purpose: Top 10 WBS codes by absolute cost variance across the program.
--
-- Cost variance by WBS code tells the project controls team exactly WHERE
-- budget pressure is coming from. A high-level CPI of 0.87 on BLD-C is
-- a headline number — this query identifies which work packages are driving it.
-- The T&T director uses this to direct the client's attention to specific
-- trade packages where corrective action is needed.
--
-- Variance = approved_budget - forecasted_final_cost
-- Negative variance = forecast over budget (the common and concerning case).

WITH variance_by_wbs AS (
    SELECT
        f.building_id,
        f.wbs_level_1,
        f.wbs_level_2,
        w.wbs_code,

        COUNT(f.cost_code)              AS cost_code_count,
        SUM(f.approved_budget)          AS total_budget,
        SUM(f.actual_cost_to_date)      AS total_actual_cost,
        SUM(f.forecasted_final_cost)    AS total_forecast,
        SUM(f.earned_value)             AS total_earned_value,
        SUM(f.committed_cost)           AS total_committed,

        -- Variance: positive = under budget, negative = over budget
        SUM(f.approved_budget - f.forecasted_final_cost) AS total_variance,

        -- Absolute variance for ranking — surfaces both over and under runs
        ABS(SUM(f.approved_budget - f.forecasted_final_cost)) AS abs_variance,

        -- WBS-level CPI
        ROUND(
            SUM(f.earned_value) / NULLIF(SUM(f.actual_cost_to_date), 0)
        , 3) AS wbs_cpi,

        -- Variance as % of budget — normalises across large and small packages
        ROUND(
            SUM(f.approved_budget - f.forecasted_final_cost)
            / NULLIF(SUM(f.approved_budget), 0) * 100
        , 2) AS variance_pct

    FROM fact_project_cost f
    LEFT JOIN dim_wbs w
        ON f.cost_code = w.wbs_code
        AND f.wbs_level_1 = w.wbs_level_1

    GROUP BY
        f.building_id,
        f.wbs_level_1,
        f.wbs_level_2,
        w.wbs_code
),

ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            ORDER BY abs_variance DESC
        ) AS variance_rank
    FROM variance_by_wbs
)

SELECT
    variance_rank,
    building_id,
    wbs_code,
    wbs_level_1,
    wbs_level_2,
    cost_code_count,
    total_budget,
    total_actual_cost,
    total_forecast,
    total_variance,
    variance_pct,
    wbs_cpi,

    -- Flag for report highlighting
    CASE
        WHEN total_variance < 0 AND ABS(variance_pct) >= 10 THEN 'Critical Over-run'
        WHEN total_variance < 0 AND ABS(variance_pct) >= 5  THEN 'Over-run'
        WHEN total_variance > 0                              THEN 'Under Budget'
        ELSE 'On Budget'
    END AS variance_flag

FROM ranked
WHERE variance_rank <= 10

ORDER BY variance_rank;
