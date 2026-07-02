# EVM Methodology — ConstructIQ

Earned Value Management (EVM) is the industry standard framework for measuring
construction program performance. Every metric in the ConstructIQ dashboard
derives from three core numbers measured at a point in time.

---

## The Three Base Metrics

### Planned Value (PV)
**What it is:** The budgeted cost of work that was *scheduled* to be complete by the reporting date.
**Also called:** BCWS — Budgeted Cost of Work Scheduled.
**Example:** If BLD-A's concrete package had a $10M budget spread evenly over 10 months, PV at month 5 = $5M.

### Earned Value (EV)
**What it is:** The budgeted cost of work that has *actually been completed* by the reporting date.
**Also called:** BCWP — Budgeted Cost of Work Performed.
**Example:** If 45% of the concrete package is physically complete, EV = 45% × $10M = $4.5M.

### Actual Cost (AC)
**What it is:** The real money spent to achieve the work completed.
**Also called:** ACWP — Actual Cost of Work Performed.
**Example:** If the contractor has invoiced $5.2M to reach 45% complete, AC = $5.2M.

---

## Derived Metrics

### Cost Performance Index (CPI)

```
CPI = EV / AC
```

Measures cost efficiency. For every dollar spent, how much budgeted work was delivered?

| CPI | Meaning |
|-----|---------|
| > 1.0 | Under budget — delivering more work per dollar than planned |
| = 1.0 | On budget |
| < 1.0 | Over budget — costing more per unit of work than planned |

**ConstructIQ example:** BLD-C CPI = 0.868. For every $1.00 spent, only $0.87 of budgeted work is being delivered. The client is paying $1.15 for every $1.00 of planned output.

---

### Schedule Performance Index (SPI)

```
SPI = EV / PV
```

Measures schedule efficiency. How much of the planned work has actually been completed?

| SPI | Meaning |
|-----|---------|
| > 1.0 | Ahead of schedule |
| = 1.0 | On schedule |
| < 1.0 | Behind schedule |

**ConstructIQ example:** BLD-B SPI = 0.988. Slightly behind schedule — 98.8% of planned work complete at snapshot date.

---

### Estimate at Completion (EAC)

```
EAC = BAC / CPI
```

Where BAC = Budget at Completion (total approved budget).

Projects the final cost of the building if current cost efficiency continues for the remainder of the program. This is the number the client's CFO watches.

**ConstructIQ example:**
- BLD-A: BAC = $763M, CPI = 0.909 → EAC = $763M / 0.909 = **$840M** (+$77M over budget)
- BLD-C: BAC = $723M, CPI = 0.868 → EAC = $723M / 0.868 = **$833M** (+$110M over budget)

---

### Variance at Completion (VAC)

```
VAC = BAC - EAC
```

The projected budget surplus (positive) or overrun (negative) at program completion.

**ConstructIQ example:** BLD-C VAC = $723M - $833M = **-$110M**. Without corrective action, BLD-C finishes $110M over budget.

---

### Cost Variance Percentage

```
CV% = (BAC - EAC) / BAC × 100
```

Expresses VAC as a percentage of the approved budget. Useful for comparing buildings of different sizes on the same scale.

---

## EVM Answer Key — Northern Virginia Campus (Snapshot: 2025-09-30)

| Building | Code | Approved Budget | CPI | SPI | EAC | VAC | Status |
|---|---|---|---|---|---|---|---|
| Alpha | BLD-A | $763M | 0.909 | ~1.00 | $840M | -$77M | Over budget |
| Beta | BLD-B | $729M | 1.025 | 0.988 | $711M | +$18M | Healthy |
| Gamma | BLD-C | $723M | 0.868 | ~0.99 | $833M | -$110M | Critical — most at-risk |
| Delta | BLD-D | $603M | 1.010 | 1.003 | $597M | +$6M | On track |

BLD-C is the program's problem building. A CPI of 0.868 at this stage of the program
is a strong leading indicator of significant budget overrun at completion. The T&T team
would be escalating corrective action plans to the client's program director.

---

## Why EVM Matters for Hyperscale Data Centers

A hyperscale data center campus at this scale ($2.1B, 200MW) has critical path
constraints that make EVM especially important:

1. **Equipment lead times are fixed.** Switchgear, UPS systems, and cooling units
   have 40-80 week lead times. A schedule slip of 2 months can push commissioning
   back by an entire quarter, delaying revenue for the cloud operator.

2. **Tenant commitments are made years in advance.** AWS pre-sells capacity to
   enterprise customers. A cost overrun that forces scope reduction risks violating
   those commitments.

3. **Four buildings run simultaneously.** Resources (labor, materials, subcontractors)
   compete across BLD-A through BLD-D. EVM at the building level reveals where to
   reallocate resources for maximum program impact.
