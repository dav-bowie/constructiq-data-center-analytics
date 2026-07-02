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
from pyspark.sql.window import Window

# ══════════════════════════════════════════════════════════════════
# 1. INITIALIZE
# ══════════════════════════════════════════════════════════════════
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'REDSHIFT_URL', 'REDSHIFT_USER', 'REDSHIFT_PASSWORD'])
sc          = SparkContext()
glueContext = GlueContext(sc)
spark       = glueContext.spark_session
job         = Job(glueContext)
job.init(args['JOB_NAME'], args)

S3_BUCKET = "s3://constructiq-raw"

REDSHIFT_URL = args['REDSHIFT_URL']
REDSHIFT_PROPS = {
    "user":     args['REDSHIFT_USER'],
    "password": args['REDSHIFT_PASSWORD'],
    "driver":   "com.amazon.redshift.jdbc42.Driver",
}

print("✓ Glue job initialized")

# ══════════════════════════════════════════════════════════════════
# 2. EXTRACT — read raw CSVs from S3
# ══════════════════════════════════════════════════════════════════
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

print(f"  Cost ledger:    {df_cost.count()} rows")
print(f"  Change orders:  {df_co.count()} rows")
print(f"  Schedule:       {df_sched.count()} rows")
print(f"  Pay apps:       {df_pay.count()} rows")
print("✓ Extract complete")

# ══════════════════════════════════════════════════════════════════
# 3. TRANSFORM — date normalization
# ══════════════════════════════════════════════════════════════════
print("Transforming: normalizing dates...")

def normalize_date(col_name):
    return F.coalesce(
        F.to_date(F.col(col_name), "yyyy-MM-dd"),
        F.to_date(F.col(col_name), "MM/dd/yyyy"),
        F.to_date(F.col(col_name), "dd-MMM-yyyy"),
        F.to_date(F.col(col_name), "MM-dd-yyyy"),
        F.to_date(F.col(col_name), "MMM-yyyy"),
        F.to_date(F.col(col_name), "yyyy-MM"),
    )

df_co = df_co \
    .withColumn("submitted_date_clean", normalize_date("submitted_date")) \
    .withColumn("approved_date_clean",  normalize_date("approved_date"))

df_sched = df_sched \
    .withColumn("planned_start_clean",  normalize_date("planned_start")) \
    .withColumn("planned_finish_clean", normalize_date("planned_finish")) \
    .withColumn("actual_start_clean",   normalize_date("actual_start")) \
    .withColumn("actual_finish_clean",  normalize_date("actual_finish"))

print("✓ Dates normalized")

# ══════════════════════════════════════════════════════════════════
# 4. TRANSFORM — NULL handling
# ══════════════════════════════════════════════════════════════════
print("Transforming: handling NULLs...")

SENTINEL_DATE = F.lit("9999-12-31").cast(DateType())

df_co = df_co.withColumn(
    "approved_date_clean",
    F.when(F.col("approved_date_clean").isNull(), SENTINEL_DATE)
     .otherwise(F.col("approved_date_clean"))
)

df_co = df_co.withColumn(
    "co_approval_lag_days",
    F.when(
        F.col("approved_date_clean") == SENTINEL_DATE,
        F.lit(None).cast(IntegerType())
    ).otherwise(
        F.datediff(F.col("approved_date_clean"), F.col("submitted_date_clean"))
    )
)

df_cost = df_cost.withColumn(
    "variance",
    F.when(
        F.col("variance").isNull(),
        F.col("approved_budget") - F.col("forecasted_final_cost")
    ).otherwise(F.col("variance"))
)

print("✓ NULLs handled")

# ══════════════════════════════════════════════════════════════════
# 5. TRANSFORM — vendor name standardization (PySpark only)
# ══════════════════════════════════════════════════════════════════
print("Transforming: standardizing vendor names...")

VENDOR_MAP = {
    "TURNER ELECTRIC": "Turner Electric Co.",
    "TURNER ELEC": "Turner Electric Co.",
    "BALFOUR BEATTY": "Balfour Beatty Construction",
    "SKANSKA": "Skanska USA Building",
    "GAYLOR": "Gaylor Electric",
    "ACCO": "ACCO Brands HVAC",
    "SOUTHLAND": "Southland Industries",
    "ROSENDIN": "Rosendin Electric",
    "SWINERTON": "Swinerton Builders",
    "DPR": "DPR Construction",
    "LIMBACH": "Limbach Holdings",
    "EMCOR": "EMCOR Group",
    "CUPERTINO": "Cupertino Electric",
    "POWER ENGINEERS": "Power Engineers Inc.",
    "TELAMON": "Telamon Corporation",
    "WSP": "WSP Global",
}

vendor_map_expr = F.col("vendor_name")
for k, v in VENDOR_MAP.items():
    vendor_map_expr = F.when(
        F.upper(F.col("vendor_name")).contains(k), v
    ).otherwise(vendor_map_expr)

df_cost = df_cost.withColumn("vendor_name_clean", vendor_map_expr)

contractor_map_expr = F.col("contractor_name")
for k, v in VENDOR_MAP.items():
    contractor_map_expr = F.when(
        F.upper(F.col("contractor_name")).contains(k), v
    ).otherwise(contractor_map_expr)

df_pay = df_pay.withColumn("contractor_name_clean", contractor_map_expr)

print("✓ Vendor names standardized")

# ══════════════════════════════════════════════════════════════════
# 6. TRANSFORM — EVM calculations
# ══════════════════════════════════════════════════════════════════
print("Transforming: calculating EVM metrics...")

df_cost = df_cost \
    .withColumn("cpi",
        F.when(F.col("actual_cost_to_date") > 0,
            F.round(F.col("earned_value") / F.col("actual_cost_to_date"), 3)
        ).otherwise(F.lit(None).cast(DoubleType()))
    ) \
    .withColumn("spi",
        F.when(F.col("planned_value") > 0,
            F.round(F.col("earned_value") / F.col("planned_value"), 3)
        ).otherwise(F.lit(None).cast(DoubleType()))
    ) \
    .withColumn("eac",
        F.when(F.col("actual_cost_to_date") > 0,
            F.round(F.col("approved_budget") / (F.col("earned_value") / F.col("actual_cost_to_date")), 0)
        ).otherwise(F.lit(None).cast(DoubleType()))
    ) \
    .withColumn("vac",
        F.when(F.col("actual_cost_to_date") > 0,
            F.round(F.col("approved_budget") - (F.col("approved_budget") / (F.col("earned_value") / F.col("actual_cost_to_date"))), 0)
        ).otherwise(F.lit(None).cast(DoubleType()))
    ) \
    .withColumn("cost_variance_pct",
        F.when(F.col("approved_budget") > 0,
            F.round((F.col("approved_budget") - F.col("forecasted_final_cost")) / F.col("approved_budget") * 100, 2)
        ).otherwise(F.lit(None).cast(DoubleType()))
    )

print("✓ EVM metrics calculated")

# ══════════════════════════════════════════════════════════════════
# 7. BUILD FACT DATAFRAMES
# ══════════════════════════════════════════════════════════════════
print("Building fact DataFrames...")

fact_cost = df_cost.select(
    F.col("cost_key"), F.col("building_id"), F.col("cost_code"),
    F.col("wbs_level_1"), F.col("wbs_level_2"),
    F.col("vendor_name_clean").alias("vendor_name"),
    F.col("contract_value"), F.col("approved_budget"),
    F.col("committed_cost"), F.col("actual_cost_to_date"),
    F.col("forecasted_final_cost"), F.col("variance"),
    F.col("earned_value"), F.col("planned_value"),
    F.col("percent_complete_actual"), F.col("percent_complete_baseline"),
    F.col("cpi"), F.col("spi"), F.col("eac"), F.col("vac"),
    F.col("cost_variance_pct"),
)

fact_co = df_co.select(
    F.col("change_order_id"), F.col("building_id"), F.col("co_type"),
    F.col("description"),
    F.col("submitted_date_clean").alias("submitted_date"),
    F.col("approved_date_clean").alias("approved_date"),
    F.col("status"), F.col("cost_impact"), F.col("schedule_impact_days"),
    F.col("co_approval_lag_days"), F.col("responsible_party"),
    F.col("wbs_code"), F.col("wbs_level_1"),
)

fact_sched = df_sched.select(
    F.col("activity_id"), F.col("building_id"), F.col("activity_name"),
    F.col("wbs_level_1"), F.col("wbs_code"),
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
    F.col("pay_app_id"), F.col("building_id"), F.col("period"),
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

print("✓ Fact DataFrames ready")

# ══════════════════════════════════════════════════════════════════
# 8. BUILD DIMENSION DATAFRAMES
# ══════════════════════════════════════════════════════════════════
print("Building dimension DataFrames...")

dim_building = (
    df_cost.select("building_id")
    .union(df_co.select("building_id"))
    .union(df_sched.select("building_id"))
    .union(df_pay.select("building_id"))
    .distinct()
    .withColumn("campus",            F.lit("Northern Virginia Data Center Campus"))
    .withColumn("client",            F.lit("Amazon Web Services"))
    .withColumn("program_value_usd", F.lit(2_100_000_000).cast(LongType()))
    .withColumn("snapshot_date",     F.to_date(F.lit("2025-09-30")))
)

wbs_cost  = df_cost.select(F.col("cost_code").alias("wbs_code"), F.col("wbs_level_1"), F.col("wbs_level_2"))
wbs_sched = df_sched.select(F.col("wbs_code"), F.col("wbs_level_1"), F.lit(None).cast(StringType()).alias("wbs_level_2"))
wbs_co    = df_co.select(F.col("wbs_code"), F.col("wbs_level_1"), F.lit(None).cast(StringType()).alias("wbs_level_2"))

dim_wbs = (
    wbs_cost.union(wbs_sched).union(wbs_co)
    .groupBy("wbs_code", "wbs_level_1")
    .agg(F.first("wbs_level_2", ignorenulls=True).alias("wbs_level_2"))
    .orderBy("wbs_code")
)

vendor_names = (
    df_cost.select(F.col("vendor_name_clean").alias("vendor_name"))
    .union(df_pay.select(F.col("contractor_name_clean").alias("vendor_name")))
    .distinct()
    .filter(F.col("vendor_name").isNotNull())
)

vendor_trades = df_pay.select(F.col("contractor_name_clean").alias("vendor_name"), F.col("trade")).distinct()

dim_vendor = (
    vendor_names
    .join(vendor_trades, on="vendor_name", how="left")
    .withColumn("vendor_id", F.row_number().over(Window.orderBy("vendor_name")))
    .select("vendor_id", "vendor_name", "trade")
)

dim_date = (
    spark.sql(
        "SELECT explode(sequence(to_date('2023-01-01'), to_date('2026-12-31'), interval 1 day)) AS full_date"
    )
    .withColumn("date_key",      F.date_format("full_date", "yyyyMMdd").cast(IntegerType()))
    .withColumn("year",          F.year("full_date"))
    .withColumn("quarter",       F.quarter("full_date"))
    .withColumn("month",         F.month("full_date"))
    .withColumn("month_name",    F.date_format("full_date", "MMMM"))
    .withColumn("week_of_year",  F.weekofyear("full_date"))
    .withColumn("day_of_week",   F.dayofweek("full_date"))
    .withColumn("day_name",      F.date_format("full_date", "EEEE"))
    .withColumn("is_weekend",    F.dayofweek("full_date").isin([1, 7]).cast(IntegerType()))
    .withColumn("is_month_end",  (F.col("full_date") == F.last_day("full_date")).cast(IntegerType()))
    .withColumn("fiscal_year",   F.year("full_date"))
    .withColumn("fiscal_quarter", F.quarter("full_date"))
)

print("✓ Dimension DataFrames ready")

# ══════════════════════════════════════════════════════════════════
# 9. LOAD — write to Redshift Serverless
# ══════════════════════════════════════════════════════════════════
print("Loading to Redshift...")

tables = {
    "fact_project_cost":     fact_cost,
    "fact_change_orders":    fact_co,
    "fact_schedule":         fact_sched,
    "fact_pay_applications": fact_pay,
    "dim_building":          dim_building,
    "dim_wbs":               dim_wbs,
    "dim_vendor":            dim_vendor,
    "dim_date":              dim_date,
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