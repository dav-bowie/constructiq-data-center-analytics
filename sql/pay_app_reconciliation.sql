-- pay_app_reconciliation.sql
-- ConstructIQ | AWS Northern Virginia Data Center Campus
-- Used in Power BI Page 3: Change Order Log (contractor billing panel)
--
-- Validates billed vs approved vs retainage held per contractor.
-- Pay app reconciliation is a monthly T&T deliverable — the project controls team
-- verifies contractor billings match approved amounts and retainage is withheld
-- correctly. Retainage (typically 10%) is held until substantial completion as a
-- performance guarantee. Incorrect retainage withheld creates legal and cash flow risk.

SELECT
    building_id,
    contractor_name,
    COUNT(*)                                                                            AS pay_app_count,
    SUM(scheduled_value)                                                                AS contract_value,
    SUM(work_completed_to_date)                                                         AS total_billed,
    SUM(total_earned)                                                                   AS total_certified,
    SUM(retainage_held)                                                                 AS total_retainage,
    SUM(net_payment_due)                                                                AS total_net_payment,
    ROUND(SUM(retainage_held)::numeric / NULLIF(SUM(total_earned), 0) * 100, 2)        AS retainage_pct
FROM fact_pay_applications
GROUP BY building_id, contractor_name
ORDER BY building_id, total_billed DESC;
