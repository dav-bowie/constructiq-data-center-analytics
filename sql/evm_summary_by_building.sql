-- evm_summary_by_building.sql
-- ConstructIQ | AWS Northern Virginia Data Center Campus
-- Purpose: Earned Value Management summary rolled up to building level.
--
-- EVM is the primary health metric T&T reports to the client each month.
-- CPI (Cost Performance Index) and SPI (Schedule Performance Index) tell
-- the program director whether each building is tracking to budget and schedule.
-- CPI < 1.0 = over budget. SPI < 1.0 = behind schedule.
--
-- IMPORTANT: CPI and SPI must be recalculated from the sum of base components
-- (EV, AC, PV) — never averaged from row-level ratios. Averaging ratios produces
-- incorrect results when cost codes have different budget weights.

SELECT
    b.building_id,
    b.campus,
    b.client,

    -- Budget totals
    SUM(f.approved_budget)          AS total_approved_budget,
    SUM(f.actual_cost_to_date)      AS total_actual_cost,
    SUM(f.earned_value)             AS total_earned_value,
    SUM(f.planned_value)            AS total_planned_value,
    SUM(f.forecasted_final_cost)    AS total_eac_from_source,

    -- CPI: for every $1 spent, how much work was delivered?
    -- CPI < 1.0 = over budget. CPI of 0.87 means $1.15 spent per $1 of work.
    ROUND(
        SUM(f.earned_value) / NULLIF(SUM(f.actual_cost_to_date), 0)
    , 3) AS cpi,

    -- SPI: are we ahead or behind the baseline schedule?
    -- SPI < 1.0 = behind schedule. SPI of 0.95 = 95% of planned work done.
    ROUND(
        SUM(f.earned_value) / NULLIF(SUM(f.planned_value), 0)
    , 3) AS spi,

    -- EAC: if current cost efficiency continues, what will the building cost?
    -- EAC = Budget / CPI
    ROUND(
        SUM(f.approved_budget) / NULLIF(
            SUM(f.earned_value) / NULLIF(SUM(f.actual_cost_to_date), 0)
        , 0)
    , 0) AS eac,

    -- VAC: projected over/under budget at completion
    -- Negative VAC = forecast over budget
    ROUND(
        SUM(f.approved_budget) - (
            SUM(f.approved_budget) / NULLIF(
                SUM(f.earned_value) / NULLIF(SUM(f.actual_cost_to_date), 0)
            , 0)
        )
    , 0) AS vac,

    -- Cost variance as a percentage of approved budget
    ROUND(
        (SUM(f.approved_budget) - SUM(f.forecasted_final_cost))
        / NULLIF(SUM(f.approved_budget), 0) * 100
    , 2) AS cost_variance_pct,

    -- Traffic light status for executive dashboard
    -- Thresholds: CPI >= 0.95 = Green, 0.90-0.95 = Amber, < 0.90 = Red
    CASE
        WHEN SUM(f.earned_value) / NULLIF(SUM(f.actual_cost_to_date), 0) >= 0.95 THEN 'Green'
        WHEN SUM(f.earned_value) / NULLIF(SUM(f.actual_cost_to_date), 0) >= 0.90 THEN 'Amber'
        ELSE 'Red'
    END AS cost_status,

    CASE
        WHEN SUM(f.earned_value) / NULLIF(SUM(f.planned_value), 0) >= 0.95 THEN 'Green'
        WHEN SUM(f.earned_value) / NULLIF(SUM(f.planned_value), 0) >= 0.90 THEN 'Amber'
        ELSE 'Red'
    END AS schedule_status

FROM fact_project_cost f
JOIN dim_building b ON f.building_id = b.building_id

GROUP BY
    b.building_id,
    b.campus,
    b.client

ORDER BY cpi ASC;  -- worst-performing building first
