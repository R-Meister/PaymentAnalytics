from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

from pyspark.sql.functions import (
    col,
    sum,
    count,
    avg,
    round,
    date_trunc,
    when
)

builder = (
    SparkSession.builder
    .appName("Gold Layer")
    .config("spark.driver.memory", "4g")
    .config("spark.executor.memory", "4g")
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

transactions = spark.read.format("delta").load(
    "lakehouse/silver/transactions"
)

customers = spark.read.format("delta").load(
    "lakehouse/silver/customers"
)

merchants = spark.read.format("delta").load(
    "lakehouse/silver/merchants"
)

tickets = spark.read.format("delta").load(
    "lakehouse/silver/support_tickets"
)

daily_revenue = (
    transactions
    .groupBy(
        date_trunc("day", col("timestamp")).alias("date")
    )
    .agg(
        round(sum("amount"), 2).alias("total_revenue"),
        count("*").alias("total_transactions"),
        sum(
            when(col("is_fraud") == 1, 1).otherwise(0)
        ).alias("fraud_transactions"),
        round(
            avg("amount"), 2
        ).alias("avg_transaction_value")
    )
)

merchant_kpis = (
    transactions
    .groupBy("merchant_id")
    .agg(
        round(sum("amount"), 2).alias("merchant_revenue"),
        count("*").alias("txn_count"),
        round(avg("amount"), 2).alias("avg_txn_value"),
        round(
            avg(
                when(col("is_fraud") == 1, 1).otherwise(0)
            ) * 100,
            2
        ).alias("fraud_rate_pct"),
        round(
            avg(
                when(col("status") == "Success", 1).otherwise(0)
            ) * 100,
            2
        ).alias("success_rate_pct")
    )
)

payment_trends = (
    transactions
    .groupBy("payment_method")
    .agg(
        count("*").alias("total_transactions"),
        round(sum("amount"), 2).alias("total_volume")
    )
)

fraud_summary = (
    transactions
    .groupBy(
        "risk_level",
        "payment_method"
    )
    .agg(
        count("*").alias("total_transactions"),
        sum(
            when(col("is_fraud") == 1, 1).otherwise(0)
        ).alias("fraud_count"),
        round(
            avg("fraud_score"),
            2
        ).alias("avg_fraud_score")
    )
)

customer_segments = (
    transactions
    .groupBy("customer_id")
    .agg(
        round(sum("amount"), 2).alias("total_spent"),
        count("*").alias("txn_count"),
        round(avg("amount"), 2).alias("avg_spend")
    )
)

support_metrics = (
    tickets
    .groupBy(
        "issue_type",
        "priority",
        "status"
    )
    .agg(
        count("*").alias("ticket_count")
    )
)

daily_revenue.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/gold/daily_revenue")

merchant_kpis.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/gold/merchant_kpis")

payment_trends.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/gold/payment_trends")

fraud_summary.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/gold/fraud_summary")

customer_segments.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/gold/customer_segments")

support_metrics.write.format("delta") \
    .mode("overwrite") \
    .save("lakehouse/gold/support_metrics")