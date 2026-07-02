-- cost_variance_by_wbs.sql
-- ConstructIQ | AWS Northern Virginia Data Center Campus
-- Used in Power BI Page 5: Cost Variance Drill-Through
--
-- Identifies top cost overrun drivers by Work Breakdown Structure category.
-- A building-level CPI of 0.868 is a headline number — this query tells the
-- T&T project controls team exactly WHICH work packages are driving it, so
-- corrective action can be directed at the right trade contractors.
--
-- Variance = approved_budget - forecasted_final_cost
-- Negative variance = forecast over budget. Results ordered worst first (ASC).
-- LIMIT 10 surfaces the top 10 overrun drivers across the full program.

SELECT
    wbs_level_1,
    building_id,
    SUM(approved_budget)            AS approved_budget,
    SUM(actual_cost_to_date)        AS actual_cost,
    SUM(forecasted_final_cost)      AS forecasted_final_cost,
    SUM(variance)                   AS variance,
    ROUND(
        SUM(variance)::numeric / NULLIF(SUM(approved_budget), 0) * 100
    , 2)                            AS variance_pct,
    SUM(earned_value)               AS earned_value,
    ROUND(
        SUM(earned_value)::numeric / NULLIF(SUM(actual_cost_to_date), 0)
    , 3)                            AS cpi
FROM fact_project_cost
GROUP BY wbs_level_1, building_id
ORDER BY SUM(variance) ASC
LIMIT 10;
