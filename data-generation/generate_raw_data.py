import csv
import random
import math
from datetime import datetime, timedelta, date

random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────────────
BUILDINGS = {
    "BLD-A": {"name": "Building Alpha", "mw": 60,  "sqft": 420000, "budget": 580_000_000, "phase": "MEP Fit-Out"},
    "BLD-B": {"name": "Building Beta",  "mw": 50,  "sqft": 380000, "budget": 510_000_000, "phase": "Shell Complete"},
    "BLD-C": {"name": "Building Gamma", "mw": 50,  "sqft": 380000, "budget": 490_000_000, "phase": "MEP Fit-Out"},
    "BLD-D": {"name": "Building Delta", "mw": 40,  "sqft": 320000, "budget": 420_000_000, "phase": "Foundation"},
}
TOTAL_BUDGET = sum(b["budget"] for b in BUILDINGS.values())  # $2.0B

# WBS hierarchy — Level 1 / Level 2 / cost_code
WBS = [
    ("01-SITEWORK",    "01.10-Earthwork",          "01.10.001"),
    ("01-SITEWORK",    "01.20-Utilities",           "01.20.001"),
    ("01-SITEWORK",    "01.30-Paving",              "01.30.001"),
    ("02-STRUCTURE",   "02.10-Concrete",            "02.10.001"),
    ("02-STRUCTURE",   "02.20-Structural Steel",    "02.20.001"),
    ("02-STRUCTURE",   "02.30-Precast",             "02.30.001"),
    ("03-ENVELOPE",    "03.10-Roofing",             "03.10.001"),
    ("03-ENVELOPE",    "03.20-Cladding",            "03.20.001"),
    ("03-ENVELOPE",    "03.30-Glazing",             "03.30.001"),
    ("04-MEP",         "04.10-Mechanical",          "04.10.001"),
    ("04-MEP",         "04.20-Electrical",          "04.20.001"),
    ("04-MEP",         "04.30-Plumbing",            "04.30.001"),
    ("04-MEP",         "04.40-Fire Protection",     "04.40.001"),
    ("05-IT-INFRA",    "05.10-Power Distribution",  "05.10.001"),
    ("05-IT-INFRA",    "05.20-Cooling Systems",     "05.20.001"),
    ("05-IT-INFRA",    "05.30-Network Backbone",    "05.30.001"),
    ("06-FINISHES",    "06.10-Interior Finishes",   "06.10.001"),
    ("06-FINISHES",    "06.20-Flooring",            "06.20.001"),
    ("07-COMMISSIONING","07.10-Testing & Balance",  "07.10.001"),
    ("07-COMMISSIONING","07.20-Startup",            "07.20.001"),
    ("08-SOFT-COSTS",  "08.10-A&E Fees",            "08.10.001"),
    ("08-SOFT-COSTS",  "08.20-Permits & Insurance", "08.20.001"),
    ("08-SOFT-COSTS",  "08.30-Owner Contingency",   "08.30.001"),
]

# Vendor names with intentional messiness
VENDORS_CLEAN = [
    "Turner Electric Co.",
    "Balfour Beatty Construction",
    "Skanska USA Building",
    "Gaylor Electric",
    "ACCO Brands HVAC",
    "Southland Industries",
    "Rosendin Electric",
    "Swinerton Builders",
    "DPR Construction",
    "Limbach Holdings",
    "EMCOR Group",
    "Cupertino Electric",
    "Power Engineers Inc.",
    "Telamon Corporation",
    "WSP Global",
]

VENDOR_MESS = {
    "Turner Electric Co.":        ["Turner Elec.", "Turner Electric", "Turner Electric Co", "TURNER ELECTRIC CO."],
    "Balfour Beatty Construction": ["Balfour Beatty", "Balfour Beatty Const.", "BALFOUR BEATTY"],
    "Skanska USA Building":        ["Skanska USA", "Skanska", "Skanska US Building"],
    "Gaylor Electric":             ["Gaylor Elec", "Gaylor Electric Inc.", "GAYLOR ELECTRIC"],
    "ACCO Brands HVAC":            ["ACCO HVAC", "ACCO Brands", "Acco Brands HVAC"],
    "Southland Industries":        ["Southland Ind.", "Southland", "SOUTHLAND INDUSTRIES"],
    "Rosendin Electric":           ["Rosendin Elec.", "Rosendin", "Rosendin Electric Inc."],
    "Swinerton Builders":          ["Swinerton", "Swinerton Builder", "SWINERTON BUILDERS"],
    "DPR Construction":            ["DPR Const.", "DPR", "D.P.R. Construction"],
    "Limbach Holdings":            ["Limbach", "Limbach Holding", "LIMBACH HOLDINGS"],
    "EMCOR Group":                 ["EMCOR", "Emcor Group", "EMCOR GROUP INC."],
    "Cupertino Electric":          ["Cupertino Elec.", "Cupertino Electric Inc", "CUPERTINO ELECTRIC"],
    "Power Engineers Inc.":        ["Power Engineers", "Power Engr.", "POWER ENGINEERS"],
    "Telamon Corporation":         ["Telamon Corp", "Telamon", "TELAMON CORP."],
    "WSP Global":                  ["WSP", "W.S.P. Global", "WSP Global Inc."],
}

def messy_vendor(vendor):
    if random.random() < 0.35:
        return random.choice(VENDOR_MESS[vendor])
    return vendor

# Date helpers — inconsistent formats simulate real export messiness
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%m-%d-%Y"]

def fmt_date(d, idx=0):
    if d is None:
        return ""
    fmt = DATE_FORMATS[idx % len(DATE_FORMATS)]
    return d.strftime(fmt)

PROJECT_START = date(2023, 6, 1)
PROJECT_END   = date(2026, 3, 31)
REPORT_DATE   = date(2025, 9, 30)   # "today" for data snapshot

MONTHS = []
d = PROJECT_START
while d <= REPORT_DATE:
    MONTHS.append(d)
    # advance to next month
    if d.month == 12:
        d = date(d.year + 1, 1, 1)
    else:
        d = date(d.year, d.month + 1, 1)

# ── Building progress params ───────────────────────────────────────────────────
# pct_complete_actual, cpi_target (drives cost health), spi_target
BLDG_PARAMS = {
    "BLD-A": {"pct_actual": 0.82, "cpi": 0.91, "spi": 0.95},  # over budget, slight delay
    "BLD-B": {"pct_actual": 0.61, "cpi": 1.03, "spi": 0.98},  # healthy
    "BLD-C": {"pct_actual": 0.74, "cpi": 0.87, "spi": 0.88},  # over budget + delayed (problem building)
    "BLD-D": {"pct_actual": 0.23, "cpi": 1.01, "spi": 1.05},  # early, on track
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. COST LEDGER
# ══════════════════════════════════════════════════════════════════════════════
print("Generating cost_ledger.csv ...")

cost_rows = []
cost_key = 1

for bld_id, bld in BUILDINGS.items():
    params   = BLDG_PARAMS[bld_id]
    bld_budget = bld["budget"]
    cpi      = params["cpi"]
    pct_act  = params["pct_actual"]

    for wbs1, wbs2, cost_code in WBS:
        # allocate budget slice
        base_wt = random.uniform(0.02, 0.10)
        approved_budget = round(bld_budget * base_wt * random.uniform(0.8, 1.2))

        contract_value  = round(approved_budget * random.uniform(0.90, 1.05))
        committed_cost  = round(approved_budget * random.uniform(0.95, 1.08))

        # EVM ground truth
        pct_baseline    = min(pct_act * random.uniform(0.92, 1.08), 1.0)
        earned_value    = round(approved_budget * pct_act)
        planned_value   = round(approved_budget * pct_baseline)
        actual_cost     = round(earned_value / cpi * random.uniform(0.97, 1.03))

        forecasted_final = round(approved_budget / cpi)
        variance         = approved_budget - forecasted_final

        # introduce occasional NULL / blank variance (messy)
        if random.random() < 0.06:
            variance = ""

        period = MONTHS[int(len(MONTHS) * pct_act * random.uniform(0.85, 1.0))]
        period_str = period.strftime("%Y-%m") if random.random() > 0.2 else period.strftime("%b-%Y")

        cost_rows.append({
            "cost_key":              cost_key,
            "cost_code":             cost_code,
            "wbs_level_1":           wbs1,
            "wbs_level_2":           wbs2,
            "vendor_name":           messy_vendor(random.choice(VENDORS_CLEAN)),
            "contract_value":        contract_value,
            "approved_budget":       approved_budget,
            "committed_cost":        committed_cost,
            "actual_cost_to_date":   actual_cost,
            "forecasted_final_cost": forecasted_final,
            "variance":              variance,
            "earned_value":          earned_value,
            "planned_value":         planned_value,
            "percent_complete_actual":   round(pct_act, 4),
            "percent_complete_baseline": round(pct_baseline, 4),
            "period_month":          period_str,
            "building_id":           bld_id,
        })
        cost_key += 1

with open("/home/claude/cost_ledger_raw.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=cost_rows[0].keys())
    writer.writeheader()
    writer.writerows(cost_rows)

print(f"  → {len(cost_rows)} rows written")


# ══════════════════════════════════════════════════════════════════════════════
# 2. CHANGE ORDER LOG
# ══════════════════════════════════════════════════════════════════════════════
print("Generating change_order_log.csv ...")

CO_TYPES = ["PCO", "COR", "OCO"]
CO_STATUS = ["Approved", "Pending", "Rejected", "Under Review"]
CO_PARTIES = ["General Contractor", "Owner", "Architect", "Subcontractor", "Owner - Scope Add"]

CO_DESCRIPTIONS = [
    "Underground utility conflict — reroute conduit run",
    "Owner-directed scope addition: generator pad expansion",
    "Unforeseen soil conditions — additional piles required",
    "Design change: raised floor height increased 6 inches",
    "Schedule acceleration request — overtime premium",
    "Material escalation: copper wire price increase",
    "HVAC equipment substitution — long lead item",
    "Additional fire stopping at penetrations",
    "MEP coordination conflict — ductwork reroute",
    "Owner-directed: add EV charging stations to parking",
    "Structural steel connection detail change",
    "Masonry wall type change at server room boundary",
    "Electrical panel relocation — clearance requirement",
    "Additional seismic bracing per revised calculations",
    "Waterproofing scope expansion at below-grade walls",
    "Change in cooling tower quantity (4 → 6 units)",
    "Lightning protection system addition",
    "Owner-directed: upgrade generator fuel capacity",
    "Rework: improperly installed conduit — floor 2",
    "Door hardware upgrade per owner security standard",
    "Additional monitoring sensors — owner request",
    "Temporary power extension — schedule change",
]

co_rows = []
co_id = 1001

for bld_id in BUILDINGS:
    n_cos = random.randint(28, 45)
    for _ in range(n_cos):
        submitted = PROJECT_START + timedelta(days=random.randint(30, 820))
        status    = random.choices(CO_STATUS, weights=[50, 25, 10, 15])[0]

        if status == "Approved":
            approved = submitted + timedelta(days=random.randint(7, 45))
            approved_str = fmt_date(approved, co_id % 4)
        elif status == "Rejected":
            approved = submitted + timedelta(days=random.randint(14, 60))
            approved_str = fmt_date(approved, co_id % 4)
        else:
            approved = None
            approved_str = ""   # NULL — pending COs have no approval date

        cost_impact     = round(random.uniform(-50_000, 2_800_000), 2)
        schedule_impact = random.choices([0, random.randint(1, 45)], weights=[40, 60])[0]
        wbs_entry       = random.choice(WBS)

        # messy: some submitted_date fields use different formats
        sub_fmt = random.choice([0, 1, 2, 3])

        co_rows.append({
            "change_order_id":      f"CO-{co_id}",
            "co_type":              random.choice(CO_TYPES),
            "description":          random.choice(CO_DESCRIPTIONS),
            "submitted_date":       fmt_date(submitted, sub_fmt),
            "approved_date":        approved_str,
            "status":               status,
            "cost_impact":          cost_impact,
            "schedule_impact_days": schedule_impact,
            "responsible_party":    random.choice(CO_PARTIES),
            "building_id":          bld_id,
            "wbs_code":             wbs_entry[2],
            "wbs_level_1":          wbs_entry[0],
        })
        co_id += 1

with open("/home/claude/change_order_log_raw.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=co_rows[0].keys())
    writer.writeheader()
    writer.writerows(co_rows)

print(f"  → {len(co_rows)} rows written")


# ══════════════════════════════════════════════════════════════════════════════
# 3. SCHEDULE / PROGRESS LOG (P6 export)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating schedule_progress_raw.csv ...")

ACTIVITY_TEMPLATES = [
    ("Mobilization & Site Setup",          "01-SITEWORK"),
    ("Mass Excavation",                    "01-SITEWORK"),
    ("Underground Utility Installation",   "01-SITEWORK"),
    ("Site Paving & Hardscape",            "01-SITEWORK"),
    ("Concrete Foundation — Mat Slab",     "02-STRUCTURE"),
    ("Concrete Foundation — Footings",     "02-STRUCTURE"),
    ("Structural Steel Erection",          "02-STRUCTURE"),
    ("Precast Wall Panel Installation",    "02-STRUCTURE"),
    ("Roof Deck & Insulation",             "03-ENVELOPE"),
    ("Exterior Cladding",                  "03-ENVELOPE"),
    ("Curtain Wall & Glazing",             "03-ENVELOPE"),
    ("Mechanical Rough-In",                "04-MEP"),
    ("Electrical Conduit Rough-In",        "04-MEP"),
    ("Plumbing Rough-In",                  "04-MEP"),
    ("Fire Suppression Installation",      "04-MEP"),
    ("Power Distribution Equipment Set",   "05-IT-INFRA"),
    ("UPS & Battery System Install",       "05-IT-INFRA"),
    ("Cooling Tower Erection",             "05-IT-INFRA"),
    ("CRAC Unit Installation",             "05-IT-INFRA"),
    ("Fiber & Network Backbone",           "05-IT-INFRA"),
    ("Interior Framing & Drywall",         "06-FINISHES"),
    ("Raised Floor System",                "06-FINISHES"),
    ("Painting & Ceiling",                 "06-FINISHES"),
    ("TAB — Test Adjust Balance",          "07-COMMISSIONING"),
    ("Integrated Systems Testing",         "07-COMMISSIONING"),
    ("Owner Commissioning & Startup",      "07-COMMISSIONING"),
]

sched_rows = []
act_counter = 1

for bld_id, bld in BUILDINGS.items():
    params  = BLDG_PARAMS[bld_id]
    spi     = params["spi"]
    pct_act = params["pct_actual"]

    # stagger building start dates
    bld_offset = {"BLD-A": 0, "BLD-B": 60, "BLD-C": 90, "BLD-D": 210}[bld_id]
    bld_start  = PROJECT_START + timedelta(days=bld_offset)

    cumulative_days = 0
    for act_name, wbs1 in ACTIVITY_TEMPLATES:
        baseline_dur = random.randint(20, 90)
        planned_start = bld_start + timedelta(days=cumulative_days)
        planned_finish = planned_start + timedelta(days=baseline_dur)

        # actual duration affected by SPI
        actual_dur = round(baseline_dur / spi * random.uniform(0.92, 1.08))

        actual_start = planned_start + timedelta(days=random.randint(-3, 12))

        # percent complete based on building progress and activity position
        activity_pct = cumulative_days / 600   # relative position in schedule
        if activity_pct < pct_act - 0.1:
            pct_complete = round(random.uniform(0.90, 1.00), 2)
            actual_finish_dt = actual_start + timedelta(days=actual_dur)
            actual_finish_str = fmt_date(actual_finish_dt, act_counter % 4)
        elif activity_pct < pct_act + 0.05:
            pct_complete = round(random.uniform(0.30, 0.85), 2)
            actual_finish_str = ""   # in progress — no finish date
        else:
            pct_complete = 0.0
            actual_finish_str = ""   # not started

        # P6 exports actual_start as blank if activity not started
        if pct_complete == 0.0:
            actual_start_str = ""
        else:
            actual_start_str = fmt_date(actual_start, (act_counter + 1) % 4)

        wbs_match = [w for w in WBS if w[0] == wbs1]
        wbs_entry = random.choice(wbs_match) if wbs_match else WBS[0]

        sched_rows.append({
            "activity_id":           f"ACT-{act_counter:04d}",
            "activity_name":         act_name,
            "building_id":           bld_id,
            "wbs_level_1":           wbs1,
            "wbs_code":              wbs_entry[2],
            "planned_start":         fmt_date(planned_start, act_counter % 4),
            "planned_finish":        fmt_date(planned_finish, act_counter % 4),
            "actual_start":          actual_start_str,
            "actual_finish":         actual_finish_str,
            "baseline_duration":     baseline_dur,
            "actual_duration":       actual_dur if pct_complete > 0 else "",
            "percent_complete":      pct_complete,
            "total_float_days":      random.randint(-10, 25) if pct_complete < 1.0 else 0,
            "critical_path_flag":    random.choice(["Y", "N", "Y", "N", "Y"]),
        })
        act_counter += 1
        cumulative_days += baseline_dur // 2   # overlap activities

with open("/home/claude/schedule_progress_raw.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=sched_rows[0].keys())
    writer.writeheader()
    writer.writerows(sched_rows)

print(f"  → {len(sched_rows)} rows written")


# ══════════════════════════════════════════════════════════════════════════════
# 4. PAYMENT APPLICATIONS
# ══════════════════════════════════════════════════════════════════════════════
print("Generating pay_applications_raw.csv ...")

CONTRACTORS = [
    ("Balfour Beatty Construction", "GC"),
    ("Skanska USA Building",        "GC"),
    ("Rosendin Electric",           "Sub-Electrical"),
    ("Southland Industries",        "Sub-Mechanical"),
    ("Gaylor Electric",             "Sub-Electrical"),
    ("Limbach Holdings",            "Sub-Plumbing"),
    ("EMCOR Group",                 "Sub-MEP"),
    ("Cupertino Electric",          "Sub-Electrical"),
    ("DPR Construction",            "GC"),
]

pay_rows = []
pay_id = 5001

for bld_id, bld in BUILDINGS.items():
    params  = BLDG_PARAMS[bld_id]
    pct_act = params["pct_actual"]
    bld_offset = {"BLD-A": 0, "BLD-B": 60, "BLD-C": 90, "BLD-D": 210}[bld_id]
    bld_start  = PROJECT_START + timedelta(days=bld_offset)

    # assign 3-5 contractors per building
    assigned = random.sample(CONTRACTORS, k=random.randint(3, 5))

    for contractor, trade in assigned:
        # scheduled value = portion of building budget
        sched_value = round(bld["budget"] * random.uniform(0.05, 0.22))
        retainage_pct = random.choice([5.0, 10.0, 10.0, 10.0])

        n_periods = int(len(MONTHS) * pct_act)
        cumulative_earned = 0

        for i, period in enumerate(MONTHS[:n_periods]):
            # S-curve: slow start, fast middle, taper at end
            relative_pos = i / max(n_periods - 1, 1)
            s_curve_pct  = (math.sin((relative_pos - 0.5) * math.pi) + 1) / 2
            period_pct   = s_curve_pct / n_periods * random.uniform(0.7, 1.3)

            work_this_period = round(sched_value * period_pct * random.uniform(0.85, 1.15))
            cumulative_earned = min(cumulative_earned + work_this_period, round(sched_value * pct_act))

            stored_materials = round(work_this_period * random.uniform(0.0, 0.12))
            total_earned     = cumulative_earned + stored_materials
            retainage_held   = round(total_earned * retainage_pct / 100)
            net_payment      = total_earned - retainage_held

            # messy: some rows have period as "YYYY-MM", some as "Month YYYY"
            if random.random() > 0.3:
                period_str = period.strftime("%Y-%m")
            else:
                period_str = period.strftime("%B %Y")

            # messy: contractor name variations
            contractor_str = messy_vendor(contractor) if contractor in VENDOR_MESS else contractor

            pay_rows.append({
                "pay_app_id":                  f"PA-{pay_id}",
                "period":                      period_str,
                "period_sequence":             i + 1,
                "building_id":                 bld_id,
                "contractor_name":             contractor_str,
                "trade":                       trade,
                "scheduled_value":             sched_value,
                "work_completed_this_period":  work_this_period,
                "work_completed_to_date":      cumulative_earned,
                "stored_materials":            stored_materials,
                "total_earned":                total_earned,
                "retainage_pct":               retainage_pct,
                "retainage_held":              retainage_held,
                "net_payment_due":             net_payment,
                "pay_app_status":              random.choices(
                    ["Certified", "Submitted", "Under Review", "Disputed"],
                    weights=[65, 20, 10, 5]
                )[0],
            })
            pay_id += 1

with open("/home/claude/pay_applications_raw.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=pay_rows[0].keys())
    writer.writeheader()
    writer.writerows(pay_rows)

print(f"  → {len(pay_rows)} rows written")
print("\nAll four raw datasets generated.")
