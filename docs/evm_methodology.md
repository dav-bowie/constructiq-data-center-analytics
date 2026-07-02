# EVM Methodology — ConstructIQ

Earned Value Management (EVM) is the industry-standard framework for measuring construction program performance objectively. Rather than asking "are we on budget?" — which only compares spend to plan — EVM asks "are we getting what we paid for?" It is the primary reporting language between Turner & Townsend and the client on major capital programs.

---

## The Three Base Metrics

Everything in EVM starts with three numbers, all measured at the same point in time.

### Planned Value (PV)
The budgeted cost of work that was *scheduled* to be complete by the reporting date.
Also called BCWS — Budgeted Cost of Work Scheduled.

> **Example:** If the MEP package on BLD-A had a $100M budget planned to be 60% complete by September 30, then PV = $60M.

### Earned Value (EV)
The budgeted cost of work that has *actually been completed* by the reporting date — regardless of what was spent to achieve it.
Also called BCWP — Budgeted Cost of Work Performed.

> **Example:** If only 52% of that MEP package is physically complete, EV = $52M. The schedule is behind.

### Actual Cost (AC)
The real money spent to achieve the completed work.
Also called ACWP — Actual Cost of Work Performed.

> **Example:** If the contractor has invoiced $59M to reach 52% complete, AC = $59M. More was spent per unit of work than planned.

---

## Derived Metrics

### Cost Performance Index (CPI)

```
CPI = EV ÷ AC
```

For every dollar spent, how much budgeted work was delivered?

| CPI Value | Meaning |
|---|---|
| > 1.0 | Under budget — delivering more work per dollar than planned |
| = 1.0 | Exactly on budget |
| < 1.0 | Over budget — each unit of work costs more than planned |

A CPI of 0.87 means the program is spending $1.15 for every $1.00 of planned output. This is BLD-C's situation.

**Why it matters to a T&T director:** CPI is a leading indicator. At 70% complete, a CPI of 0.87 almost never recovers to 1.0 — the remaining work must be completed at a CPI of 1.0 or better to offset the overrun already baked in. Early identification is the only lever.

---

### Schedule Performance Index (SPI)

```
SPI = EV ÷ PV
```

What percentage of planned work has actually been completed?

| SPI Value | Meaning |
|---|---|
| > 1.0 | Ahead of schedule |
| = 1.0 | On schedule |
| < 1.0 | Behind schedule |

**Why it matters:** On a hyperscale data center campus, schedule drives revenue. AWS pre-sells capacity. A building that finishes 3 months late creates downstream consequences for the client's enterprise customers.

---

### Estimate at Completion (EAC)

```
EAC = Budget ÷ CPI
```

If current cost efficiency continues for the remainder of the program, what will the building actually cost?

> **Example:** BLD-C has a $722M approved budget and a CPI of 0.868.
> EAC = $722M ÷ 0.868 = **$832M**

This is the number the client's CFO watches. A growing EAC month-over-month signals a worsening cost position.

---

### Variance at Completion (VAC)

```
VAC = Budget − EAC
```

The projected surplus (positive) or overrun (negative) at program completion.

> **Example:** BLD-C: VAC = $722M − $832M = **−$110M**

Without corrective action, BLD-C finishes $110M over budget.

---

## ConstructIQ Program Results — Snapshot: September 30, 2025

Validated output from `sql/evm_summary_by_building.sql` run against Amazon Redshift:

| Building | CPI | SPI | EAC | VAC | Status |
|---|---|---|---|---|---|
| BLD-A (Alpha) | 0.909 | 1.000 | $840,430,728 | −$77M | Over budget |
| BLD-B (Beta) | 1.025 | 0.988 | $710,678,388 | +$18M | Healthy |
| BLD-C (Gamma) | **0.868** | 0.992 | **$832,568,639** | **−$110M** | **Critical — most at-risk** |
| BLD-D (Delta) | 1.010 | 1.003 | $597,160,619 | +$6M | On track |

### What this tells the program director

- **BLD-C requires immediate escalation.** CPI of 0.868 at this stage of construction means the overrun trajectory is locked in unless the cost efficiency of remaining work improves significantly. T&T would be issuing a formal program risk report and requiring the contractor to submit a recovery plan.
- **BLD-A is under manageable pressure.** CPI of 0.909 is concerning but not critical. Focused change order discipline and procurement optimization on remaining packages could tighten this.
- **BLD-B and BLD-D are performing well.** These buildings demonstrate that the design and procurement approach works — lessons learned should be captured and applied to BLD-A and BLD-C recovery planning.

---

## Important: How CPI Must Be Calculated

CPI must always be derived from the **sum of EV divided by the sum of AC** across all cost codes — never by averaging the pre-calculated CPI values from individual rows.

```sql
-- Correct
ROUND(SUM(earned_value) / NULLIF(SUM(actual_cost_to_date), 0), 3) AS cpi

-- Wrong — produces incorrect results when cost codes have different budget weights
AVG(cpi) AS cpi
```

This is enforced in both the SQL queries and the Power BI DAX measures in this project.
