# Apache Spark — Complete Reference

## What is Apache Spark?
Apache Spark is a unified analytics engine for large-scale data processing. It extends the MapReduce model with in-memory computation, making it 10-100x faster than Hadoop for iterative algorithms and interactive queries.

## Core Architecture

### Cluster Components
- **Driver**: The main program that creates SparkContext, submits jobs, coordinates execution
- **Executors**: JVM processes on worker nodes that run tasks and cache data
- **Cluster Manager**: YARN, Kubernetes, Mesos, or Spark Standalone
- **SparkContext / SparkSession**: Entry point for Spark functionality

### Execution Model
```
Job → Stages → Tasks
```
- **Job**: triggered by an action (collect, write, show)
- **Stage**: set of tasks that can run in parallel (split at shuffle boundaries)
- **Task**: unit of work on a single partition

## RDD vs DataFrame vs Dataset

| API | Language | Schema | Optimization | Use When |
|---|---|---|---|---|
| RDD | Python/Scala/Java | None | None | Low-level control, custom transformations |
| DataFrame | Python/Scala/Java | Schema | Catalyst + Tungsten | 99% of use cases |
| Dataset | Scala/Java only | Typed | Catalyst + Tungsten | Type-safe in Scala |

**Always prefer DataFrame over RDD** unless you need row-level control.

## PySpark — Common Patterns

### Reading Data
```python
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("example").getOrCreate()

# CSV
df = spark.read.csv("s3://bucket/data.csv", header=True, inferSchema=True)

# Parquet (preferred format — columnar, compressed)
df = spark.read.parquet("s3://bucket/data/")

# Delta Lake
df = spark.read.format("delta").load("s3://bucket/delta-table/")
```

### Transformations
```python
from pyspark.sql import functions as F

df2 = (df
    .filter(F.col("status") == "active")
    .withColumn("revenue", F.col("quantity") * F.col("unit_price"))
    .groupBy("region")
    .agg(F.sum("revenue").alias("total_revenue"), F.count("*").alias("order_count"))
    .orderBy(F.desc("total_revenue"))
)
```

### Window Functions
```python
from pyspark.sql.window import Window

window = Window.partitionBy("customer_id").orderBy("order_date")
df = df.withColumn("running_total", F.sum("amount").over(window))
df = df.withColumn("rank", F.rank().over(window))
```

## Spark Optimization

### Partitioning
```python
# Read with explicit partitions
df = spark.read.parquet("s3://...").repartition(200)

# Write partitioned by date
df.write.partitionBy("year", "month").parquet("s3://output/")

# Optimal partition size: 128MB–256MB each
# Rule of thumb: num_partitions = total_data_size_MB / 200
```

### Broadcast Joins
For small tables (< 10MB), broadcast to avoid shuffle:
```python
from pyspark.sql.functions import broadcast
result = large_df.join(broadcast(small_df), "key")
```

### Caching
```python
df.cache()        # Memory (MEMORY_ONLY)
df.persist()      # Default: MEMORY_AND_DISK
df.unpersist()    # Release when done
```

### Common Performance Issues
1. **Data skew**: one partition much larger than others → salting technique
2. **Too many small files**: read performance suffers → coalesce before write
3. **Missing partition pruning**: filter column not a partition column → repartition
4. **Shuffles**: joins and groupBy are expensive → broadcast small tables, pre-partition

### Adaptive Query Execution (AQE) — Spark 3.x
```python
spark.conf.set("spark.sql.adaptive.enabled", "true")  # default in Spark 3.2+
# Automatically: coalesces small partitions, optimizes join strategies, skew handling
```

## Spark SQL
```python
df.createOrReplaceTempView("orders")
result = spark.sql("""
    SELECT region, 
           SUM(revenue) as total,
           RANK() OVER (ORDER BY SUM(revenue) DESC) as rank
    FROM orders
    GROUP BY region
""")
```

## Delta Lake
Open-source storage layer that adds ACID transactions to Spark:
```python
# Write
df.write.format("delta").mode("overwrite").save("/delta/events")

# ACID merge (upsert)
from delta.tables import DeltaTable
dt = DeltaTable.forPath(spark, "/delta/events")
dt.alias("t").merge(
    updates.alias("u"),
    "t.id = u.id"
).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()

# Time travel
df_yesterday = spark.read.format("delta").option("versionAsOf", 5).load("/delta/events")

# Schema evolution
df.write.format("delta").option("mergeSchema", "true").mode("append").save("/delta/events")
```

## Databricks-Specific Features
- **Photon**: vectorized query engine, 2-5x faster than vanilla Spark
- **Unity Catalog**: fine-grained access control, data lineage
- **Databricks Runtime**: optimized Spark + Delta + libraries
- **Auto Loader**: incremental file ingestion from cloud storage
- **MLflow**: integrated experiment tracking
