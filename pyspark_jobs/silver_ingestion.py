from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

from pyspark.sql.functions import (
    col,
    to_timestamp,
    hour,
    dayofweek,
    when,
    lower,
    trim,
    regexp_replace,
    length
)

builder = (
    SparkSession.builder
    .appName("Silver Layer")
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

customers = spark.read.format("delta").load(
    "lakehouse/bronze/customers"
)

merchants = spark.read.format("delta").load(
    "lakehouse/bronze/merchants"
)

transactions = spark.read.format("delta").load(
    "lakehouse/bronze/transactions"
)

reviews = spark.read.format("delta").load(
    "lakehouse/bronze/reviews"
)

tickets = spark.read.format("delta").load(
    "lakehouse/bronze/support_tickets"
)

customers_silver = (
    customers
    .dropDuplicates(["customer_id"])
    .dropna(subset=["customer_id", "email"])
    .withColumn(
        "customer_name",
        trim(col("customer_name"))
    )
    .withColumn(
        "email",
        lower(trim(col("email")))
    )
)

merchants_silver = (
    merchants
    .dropDuplicates(["merchant_id"])
    .dropna(subset=["merchant_id"])
    .withColumn(
        "merchant_name",
        trim(col("merchant_name"))
    )
    .withColumn(
        "category",
        trim(col("category"))
    )
    .withColumn(
        "risk_score",
        col("risk_score").cast("integer")
    )
)

transactions_silver = (
    transactions
    .dropDuplicates(["transaction_id"])
    .dropna(subset=["transaction_id", "customer_id", "merchant_id"])
)

transactions_silver = (
    transactions_silver
    .withColumn(
        "amount",
        col("amount").cast("double")
    )
    .withColumn(
        "fraud_score",
        col("fraud_score").cast("double")
    )
    .withColumn(
        "timestamp",
        to_timestamp(col("timestamp"))
    )
)

transactions_silver = (
    transactions_silver

    .withColumn(
        "txn_hour",
        hour(col("timestamp"))
    )

    .withColumn(
        "is_weekend",
        when(
            dayofweek(col("timestamp")).isin([1, 7]),
            1
        ).otherwise(0)
    )

    .withColumn(
        "is_high_value",
        when(col("amount") > 5000, 1).otherwise(0)
    )

    .withColumn(
        "is_late_night",
        when(
            (col("txn_hour") >= 0) &
            (col("txn_hour") <= 4),
            1
        ).otherwise(0)
    )

    .withColumn(
        "payment_method",
        trim(lower(col("payment_method")))
    )

    .withColumn(
        "device_type",
        trim(lower(col("device_type")))
    )
)

reviews_silver = (
    reviews
    .dropDuplicates(["review_id"])
    .dropna(subset=["review_text"])
    .withColumn(
        "review_text",
        regexp_replace(col("review_text"), r"\\n", " ")
    )
    .withColumn(
        "review_length",
        length(col("review_text"))
    )
)

tickets_silver = (
    tickets
    .dropDuplicates(["ticket_id"])
    .dropna(subset=["description"])
    .withColumn(
        "description",
        regexp_replace(col("description"), r"\\n", " ")
    )
    .withColumn(
        "description_length",
        length(col("description"))
    )
)

customers_silver.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/silver/customers")

merchants_silver.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/silver/merchants")

transactions_silver.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/silver/transactions")

reviews_silver.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/silver/reviews")

tickets_silver.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/silver/support_tickets")

print("Silver Layer Created Successfully!")