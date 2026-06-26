from typing import Any
from pyspark.context import SparkContext
from pyspark.sql import SparkSession

class GlueContext:
    spark_session: SparkSession
    def __init__(self, sc: SparkContext) -> None: ...
    def __getattr__(self, name: str) -> Any: ...
