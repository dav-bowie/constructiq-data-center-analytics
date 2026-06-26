# constructiq_etl.py
# ConstructIQ — AWS Glue ETL Job
# Raw CSV (S3) → Clean star schema (Redshift)
# Client: Amazon Web Services — Northern Virginia Data Center Campus
# Program value: $2.1B | 4 buildings | Snapshot date: 2025-09-30

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import *
from rapidfuzz import process, fuzz

# ══════════════════════════════════════════════════════════════════
# 1. INITIALIZE
# ══════════════════════════════════════════════════════════════════
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'REDSHIFT_CONNECTION'])
sc          = SparkContext()
glueContext = GlueContext(sc)
spark       = glueContext.spark_session
job         = Job(glueContext)
job.init(args['JOB_NAME'], args)

S3_BUCKET = "s3://constructiq-raw"

# Credentials come from the Glue Data Catalog connection — no hardcoded secrets
redshift_conf = glueContext.extract_jdbc_conf(args['REDSHIFT_CONNECTION'])
REDSHIFT_URL   = redshift_conf['url']
REDSHIFT_PROPS = {
    "user":     redshift_conf['user'],
    "password": redshift_conf['password'],
    "driver":   "com.amazon.redshift.jdbc42.Driver",
}

print("✓ Glue job initialized")

# ══════════════════════════════════════════════════════════════════
# 2. EXTRACT — read raw CSVs from S3
# ══════════════════════════════════════════════════════════════════
# Why: Each CSV simulates a different source system export.
# Spark reads them in parallel as distributed DataFrames.
# header=True  → first row is column names
# inferSchema=True → Spark guesses data types (we'll fix bad ones in Transform)

print("Extracting raw data from S3...")

df_cost = spark.read.csv(
    f"{S3_BUCKET}/procore-cost-ledger/cost_ledger_raw.csv",
    header=True,
    inferSchema=True,
)

df_co = spark.read.csv(
    f"{S3_BUCKET}/change-order-log/change_order_log_raw.csv",
    header=True,
    inferSchema=True,
)

df_sched = spark.read.csv(
    f"{S3_BUCKET}/schedule-progress/schedule_progress_raw.csv",
    header=True,
    inferSchema=True,
)

df_pay = spark.read.csv(
    f"{S3_BUCKET}/pay-applications/pay_applications_raw.csv",
    header=True,
    inferSchema=True,
)

# Quick row counts — first sanity check
print(f"  Cost ledger:    {df_cost.count()} rows")
print(f"  Change orders:  {df_co.count()} rows")
print(f"  Schedule:       {df_sched.count()} rows")
print(f"  Pay apps:       {df_pay.count()} rows")

print("✓ Extract complete")

# ══════════════════════════════════════════════════════════════════
# 3. TRANSFORM — date normalization
# ══════════════════════════════════════════════════════════════════
# Why: Your raw data has four different date formats across files.
# Power BI and Redshift both require consistent YYYY-MM-DD.
# If one row says "15-Jan-2025" and another says "01/15/2025",
# any date filter or time-series chart will silently break.

print("Transforming: normalizing dates...")

# This function tries all known formats and returns YYYY-MM-DD or null
def normalize_date(col_name):
    return F.coalesce(
        F.to_date(F.col(col_name), "yyyy-MM-dd"),
        F.to_date(F.col(col_name), "MM/dd/yyyy"),
        F.to_date(F.col(col_name), "dd-MMM-yyyy"),
        F.to_date(F.col(col_name), "MM-dd-yyyy"),
        F.to_date(F.col(col_name), "MMM-yyyy"),
        F.to_date(F.col(col_name), "yyyy-MM"),
    )

# Apply to change order dates
df_co = df_co \
    .withColumn("submitted_date_clean", normalize_date("submitted_date")) \
    .withColumn("approved_date_clean",  normalize_date("approved_date"))

# Apply to schedule dates
df_sched = df_sched \
    .withColumn("planned_start_clean",  normalize_date("planned_start")) \
    .withColumn("planned_finish_clean", normalize_date("planned_finish")) \
    .withColumn("actual_start_clean",   normalize_date("actual_start")) \
    .withColumn("actual_finish_clean",  normalize_date("actual_finish"))

print("✓ Dates normalized")

# ══════════════════════════════════════════════════════════════════
# 4. TRANSFORM — NULL handling
# ══════════════════════════════════════════════════════════════════
# Why: Pending change orders have no approved_date — that's valid,
# not an error. We fill with a sentinel date (9999-12-31) so the
# row still appears in aging reports instead of being filtered out.
# Without this, your CO aging table would silently drop pending COs.

print("Transforming: handling NULLs...")

SENTINEL_DATE = F.lit("9999-12-31").cast(DateType())

df_co = df_co.withColumn(
    "approved_date_clean",
    F.when(
        F.col("approved_date_clean").isNull(),
        SENTINEL_DATE
    ).otherwise(F.col("approved_date_clean"))
)

# CO approval lag in days (null-safe — pending COs get null lag, not an error)
df_co = df_co.withColumn(
    "co_approval_lag_days",
    F.when(
        F.col("approved_date_clean") == SENTINEL_DATE,
        F.lit(None).cast(IntegerType())
    ).otherwise(
        F.datediff(
            F.col("approved_date_clean"),
            F.col("submitted_date_clean")
        )
    )
)

# Cost ledger: fill blank variance with calculated value
df_cost = df_cost.withColumn(
    "variance",
    F.when(
        F.col("variance").isNull(),
        F.col("approved_budget") - F.col("forecasted_final_cost")
    ).otherwise(F.col("variance"))
)

print("✓ NULLs handled")

# ══════════════════════════════════════════════════════════════════
# 5. TRANSFORM — vendor name standardization (fuzzy matching)
# ══════════════════════════════════════════════════════════════════
# Why: "Turner Elec." and "TURNER ELECTRIC CO." are the same vendor.
# If you don't standardize, your pay app totals split across 4 rows
# instead of summing to one vendor — every downstream report breaks.
# rapidfuzz scores similarity 0-100; we accept matches above 85.

print("Transforming: standardizing vendor names...")

CANONICAL_VENDORS = [
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

def standardize_vendor(name):
    if name is None:
        return "Unknown"
    result = process.extractOne(
        name,
        CANONICAL_VENDORS,
        scorer=fuzz.token_sort_ratio,
    )
    # result = (match, score, index)
    if result and result[1] >= 85:
        return result[0]
    return name  # below threshold — keep original, flag for review

standardize_vendor_udf = F.udf(standardize_vendor, StringType())

df_cost = df_cost.withColumn(
    "vendor_name_clean",
    standardize_vendor_udf(F.col("vendor_name"))
)

df_pay = df_pay.withColumn(
    "contractor_name_clean",
    standardize_vendor_udf(F.col("contractor_name"))
)

print("✓ Vendor names standardized")

# ══════════════════════════════════════════════════════════════════
# 6. TRANSFORM — EVM calculations
# ══════════════════════════════════════════════════════════════════
# Why: These are the metrics your Power BI dashboard is built on.
# CPI < 1.0 means over budget. SPI < 1.0 means behind schedule.
# EAC = what the project will actually cost if trends continue.
# VAC = how much over or under budget you'll finish.
# These don't exist in the raw data — you derive them here.
# Division guards: early-period rows can have zero actual cost or
# planned value, which would produce Infinity and corrupt the table.

print("Transforming: calculating EVM metrics...")

df_cost = df_cost \
    .withColumn(
        "cpi",
        F.when(
            F.col("actual_cost_to_date") > 0,
            F.round(F.col("earned_value") / F.col("actual_cost_to_date"), 3)
        ).otherwise(F.lit(None).cast(DoubleType()))
    ) \
    .withColumn(
        "spi",
        F.when(
            F.col("planned_value") > 0,
            F.round(F.col("earned_value") / F.col("planned_value"), 3)
        ).otherwise(F.lit(None).cast(DoubleType()))
    ) \
    .withColumn(
        "eac",
        F.when(
            F.col("actual_cost_to_date") > 0,
            F.round(
                F.col("approved_budget") / (
                    F.col("earned_value") / F.col("actual_cost_to_date")
                ), 0
            )
        ).otherwise(F.lit(None).cast(DoubleType()))
    ) \
    .withColumn(
        "vac",
        F.when(
            F.col("actual_cost_to_date") > 0,
            F.round(
                F.col("approved_budget") - (
                    F.col("approved_budget") / (
                        F.col("earned_value") / F.col("actual_cost_to_date")
                    )
                ), 0
            )
        ).otherwise(F.lit(None).cast(DoubleType()))
    ) \
    .withColumn(
        "cost_variance_pct",
        F.when(
            F.col("approved_budget") > 0,
            F.round(
                (F.col("approved_budget") - F.col("forecasted_final_cost"))
                / F.col("approved_budget") * 100, 2
            )
        ).otherwise(F.lit(None).cast(DoubleType()))
    )

print("✓ EVM metrics calculated")

# ══════════════════════════════════════════════════════════════════
# 7. TRANSFORM — build clean output DataFrames (star schema)
# ══════════════════════════════════════════════════════════════════
# Why: Redshift wants clean, typed columns with no raw/messy originals.
# We select only what the star schema needs and rename for clarity.

print("Building star schema DataFrames...")

fact_cost = df_cost.select(
    F.col("cost_key"),
    F.col("building_id"),
    F.col("cost_code"),
    F.col("wbs_level_1"),
    F.col("wbs_level_2"),
    F.col("vendor_name_clean").alias("vendor_name"),
    F.col("contract_value"),
    F.col("approved_budget"),
    F.col("committed_cost"),
    F.col("actual_cost_to_date"),
    F.col("forecasted_final_cost"),
    F.col("variance"),
    F.col("earned_value"),
    F.col("planned_value"),
    F.col("percent_complete_actual"),
    F.col("percent_complete_baseline"),
    F.col("cpi"),
    F.col("spi"),
    F.col("eac"),
    F.col("vac"),
    F.col("cost_variance_pct"),
)

fact_co = df_co.select(
    F.col("change_order_id"),
    F.col("building_id"),
    F.col("co_type"),
    F.col("description"),
    F.col("submitted_date_clean").alias("submitted_date"),
    F.col("approved_date_clean").alias("approved_date"),
    F.col("status"),
    F.col("cost_impact"),
    F.col("schedule_impact_days"),
    F.col("co_approval_lag_days"),
    F.col("responsible_party"),
    F.col("wbs_code"),
    F.col("wbs_level_1"),
)

fact_sched = df_sched.select(
    F.col("activity_id"),
    F.col("building_id"),
    F.col("activity_name"),
    F.col("wbs_level_1"),
    F.col("wbs_code"),
    F.col("planned_start_clean").alias("planned_start"),
    F.col("planned_finish_clean").alias("planned_finish"),
    F.col("actual_start_clean").alias("actual_start"),
    F.col("actual_finish_clean").alias("actual_finish"),
    F.col("baseline_duration").cast(IntegerType()),
    F.col("actual_duration").cast(IntegerType()),
    F.col("percent_complete").cast(DoubleType()),
    F.col("total_float_days").cast(IntegerType()),
    F.col("critical_path_flag"),
)

fact_pay = df_pay.select(
    F.col("pay_app_id"),
    F.col("building_id"),
    F.col("period"),
    F.col("period_sequence").cast(IntegerType()),
    F.col("contractor_name_clean").alias("contractor_name"),
    F.col("trade"),
    F.col("scheduled_value").cast(LongType()),
    F.col("work_completed_this_period").cast(LongType()),
    F.col("work_completed_to_date").cast(LongType()),
    F.col("stored_materials").cast(LongType()),
    F.col("total_earned").cast(LongType()),
    F.col("retainage_pct").cast(DoubleType()),
    F.col("retainage_held").cast(LongType()),
    F.col("net_payment_due").cast(LongType()),
    F.col("pay_app_status"),
)

print("✓ Star schema DataFrames ready")
print(f"  fact_cost:  {fact_cost.count()} rows")
print(f"  fact_co:    {fact_co.count()} rows")
print(f"  fact_sched: {fact_sched.count()} rows")
print(f"  fact_pay:   {fact_pay.count()} rows")

# ══════════════════════════════════════════════════════════════════
# 8. LOAD — write to Redshift Serverless
# ══════════════════════════════════════════════════════════════════
# Why: Redshift is where Power BI connects to run queries.
# mode="overwrite" replaces the table each run — correct for
# monthly refresh cycles where the full dataset is reloaded.
# In production you'd use "append" with deduplication logic.

print("Loading to Redshift...")

tables = {
    "fact_project_cost":     fact_cost,
    "fact_change_orders":    fact_co,
    "fact_schedule":         fact_sched,
    "fact_pay_applications": fact_pay,
}

for table_name, df in tables.items():
    df.write.jdbc(
        url=REDSHIFT_URL,
        table=table_name,
        mode="overwrite",
        properties=REDSHIFT_PROPS,
    )
    print(f"  ✓ Loaded {table_name}")

print("✓ All tables loaded to Redshift")

job.commit()
print("✓ Glue job complete")
