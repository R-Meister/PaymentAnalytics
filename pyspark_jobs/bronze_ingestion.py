from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

builder = (
    SparkSession.builder
    .appName("Bronze Ingestion")
    .config(
        "spark.driver.extraJavaOptions",
        "-Djava.security.manager=allow"
    )
    .config(
        "spark.executor.extraJavaOptions",
        "-Djava.security.manager=allow"
    )
    .config("spark.hadoop.fs.defaultFS", "file:///")
    .config(
        "spark.sql.extensions",
        "io.delta.sql.DeltaSparkSessionExtension"
    )
    .config(
        "spark.sql.catalog.spark_catalog",
        "org.apache.spark.sql.delta.catalog.DeltaCatalog"
    )
)

spark = configure_spark_with_delta_pip(builder).getOrCreate()

customers = spark.read.csv(
    "data/customers.csv",
    header=True,
    inferSchema=True
)

merchants = spark.read.csv(
    "data/merchants.csv",
    header=True,
    inferSchema=True
)

transactions = spark.read.csv(
    "data/transactions.csv",
    header=True,
    inferSchema=True
)

reviews = spark.read.csv(
    "data/reviews.csv",
    header=True,
    inferSchema=True
)

tickets = spark.read.csv(
    "data/support_tickets.csv",
    header=True,
    inferSchema=True
)

customers.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/bronze/customers")

merchants.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/bronze/merchants")

transactions.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/bronze/transactions")

reviews.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/bronze/reviews")

tickets.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/bronze/support_tickets")