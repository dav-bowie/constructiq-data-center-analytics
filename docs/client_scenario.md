# Client Scenario — AWS Northern Virginia Data Center Campus

## Program Brief

| Field | Detail |
|---|---|
| **Client** | Amazon Web Services (AWS) |
| **Program** | Northern Virginia Hyperscale Data Center Campus |
| **Location** | Northern Virginia, USA (Loudoun County / Ashburn corridor) |
| **Total Program Value** | $2.1 billion |
| **Total IT Capacity** | 200 megawatts (MW) |
| **Active Buildings** | 4 (BLD-A through BLD-D) |
| **Snapshot Date** | September 30, 2025 |
| **T&T Role** | Owner's Representative / Digital Project Controls |

---

## Why Northern Virginia

Northern Virginia is the world's largest data center market, responsible for more than 70% of global internet traffic routing. The Ashburn/Loudoun County corridor has become the de facto hub for hyperscale cloud infrastructure due to its concentration of dark fiber, available power, and proximity to major internet exchange points.

AWS has operated in us-east-1 (N. Virginia) since 2006 — this campus represents the next generation of that infrastructure, purpose-built for the AI/ML workloads requiring high power density and sub-millisecond latency to existing AWS services.

---

## The Four Buildings

### BLD-A — Alpha
| | |
|---|---|
| **IT Capacity** | 60 MW |
| **Gross Area** | 420,000 sqft |
| **Budget** | $580M |
| **Current Phase** | MEP Fit-Out |
| **CPI** | 0.909 — Over budget |
| **EAC** | $840,430,728 |

Alpha is the lead building on campus and furthest along in construction. Cost pressure is concentrated in the MEP fit-out phase — electrical switchgear installation, UPS systems, and cooling infrastructure. Long lead equipment delivery delays compressed the installation schedule, driving overtime costs. T&T is monitoring closely but the trajectory is manageable.

---

### BLD-B — Beta
| | |
|---|---|
| **IT Capacity** | 50 MW |
| **Gross Area** | 380,000 sqft |
| **Budget** | $510M |
| **Current Phase** | Shell Complete |
| **CPI** | 1.025 — Healthy |
| **EAC** | $710,678,388 |

Beta is the program's strongest performer. Lessons learned from Alpha's procurement cycle — earlier subcontractor buyouts, standardized equipment specifications, tighter change order approval gates — were applied here. The shell is complete and MEP fit-out contracts have been awarded at favorable rates. Tracking under budget.

---

### BLD-C — Gamma ⚠️
| | |
|---|---|
| **IT Capacity** | 50 MW |
| **Gross Area** | 380,000 sqft |
| **Budget** | $490M |
| **Current Phase** | MEP Fit-Out |
| **CPI** | 0.868 — Critical |
| **EAC** | $832,568,639 |

Gamma is the program's problem building and the primary focus of T&T's risk reporting to the client. Three compounding factors are driving the cost overrun:

1. **Owner-directed scope changes (OCOs)** on the MEP systems — the client upgraded cooling specifications mid-construction to support higher-density GPU compute racks, adding unplanned cost and schedule pressure.
2. **Contractor productivity shortfall** on the structural package — the GC underperformed against baseline productivity assumptions during the steel erection phase.
3. **Critical path compression** from late generator and switchgear deliveries — forced parallel work sequencing that increased labor costs.

A CPI of 0.868 at the MEP Fit-Out phase leaves very little room for recovery. T&T has issued a formal program risk escalation and required the contractor to submit a cost recovery plan within 30 days.

---

### BLD-D — Delta
| | |
|---|---|
| **IT Capacity** | 40 MW |
| **Gross Area** | 320,000 sqft |
| **Budget** | $420M |
| **Current Phase** | Foundation |
| **CPI** | 1.010 — On track |
| **EAC** | $597,160,619 |

Delta is the newest building on campus, currently in foundation and early structural work. It benefits from standardized designs developed across Alpha and Beta, pre-negotiated subcontractor rates from the earlier procurement cycles, and a more favorable labor market. Tracking closely to baseline.

---

## T&T's Role on This Program

Turner & Townsend is engaged as the Owner's Representative with a specific mandate for Digital Project Controls. The engagement covers:

- **Cost management:** Monthly cost reports, change order management, budget forecasting
- **Schedule management:** Primavera P6 schedule review, critical path analysis, delay analysis
- **Digital controls:** This ConstructIQ pipeline — automating the data integration and reporting layer across all four buildings
- **Risk management:** Monthly risk register updates, escalation reporting to the client's SVP of Infrastructure

The ConstructIQ dashboard is the primary reporting tool used in the monthly program review meeting with the client's capital projects leadership team.

---

## Source Systems

Data flows from three enterprise platforms used across the program:

| System | Used For | Data Quality Issues |
|---|---|---|
| **Procore** | Cost ledger, change orders, pay applications | Mixed date formats, vendor name variations |
| **Primavera P6** | Schedule progress, activity tracking | Mixed date formats, null actuals on future activities |
| **Pay App Register** | Contractor billing, retainage tracking | Cumulative figures, mixed period formats |

Each system exports independently on different schedules. The ETL pipeline normalizes and joins these feeds into a single Redshift star schema updated with each Glue job run.
