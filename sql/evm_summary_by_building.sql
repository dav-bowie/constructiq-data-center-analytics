-- evm_summary_by_building.sql
-- ConstructIQ | AWS Northern Virginia Data Center Campus
-- Used in Power BI Page 2: EVM Performance
--
-- Calculates CPI, SPI, EAC, VAC per building to identify cost and schedule health.
-- CPI and SPI are derived from summed base components (EV, AC, PV) — never averaged
-- from row-level ratios, which produces incorrect results across cost codes of
-- different budget weights.
--
-- CPI < 1.0 = over budget. SPI < 1.0 = behind schedule.
-- EAC = what the building will actually cost if current efficiency continues.
-- VAC = projected surplus (positive) or overrun (negative) at completion.

SELECT
    building_id,
    ROUND(SUM(earned_value)::numeric / NULLIF(SUM(actual_cost_to_date), 0), 3)   AS cpi,
    ROUND(SUM(earned_value)::numeric / NULLIF(SUM(planned_value), 0), 3)          AS spi,
    ROUND(
        SUM(approved_budget)::numeric /
        NULLIF(SUM(earned_value)::numeric / NULLIF(SUM(actual_cost_to_date), 0), 0)
    , 0)                                                                           AS eac,
    ROUND(
        SUM(approved_budget) - (
            SUM(approved_budget)::numeric /
            NULLIF(SUM(earned_value)::numeric / NULLIF(SUM(actual_cost_to_date), 0), 0)
        )
    , 0)                                                                           AS vac,
    SUM(approved_budget)       AS total_budget,
    SUM(actual_cost_to_date)   AS total_actual_cost,
    SUM(earned_value)          AS total_earned_value
FROM fact_project_cost
GROUP BY building_id
ORDER BY building_id;
