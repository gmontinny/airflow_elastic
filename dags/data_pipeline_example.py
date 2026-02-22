from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import os

# Configurações padrão do DAG
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 11, 10, 30),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Definição do DAG
dag = DAG(
    'data_pipeline_example',
    default_args=default_args,
    description='Pipeline de dados com Kafka, Spark, MinIO e StarRocks',
    schedule_interval=timedelta(hours=1),
    catchup=False,
    tags=['data-pipeline', 'kafka', 'spark', 'minio', 'starrocks'],
)

def check_kafka_connection():
    """Verifica conexão com Kafka"""
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9093'),
            value_serializer=lambda v: str(v).encode('utf-8'),
            request_timeout_ms=5000,
            api_version_auto_timeout_ms=5000
        )
        producer.send('test-topic', 'test-message').get(timeout=5)
        producer.close()
        print("✅ Kafka connection successful")
        return True
    except Exception as e:
        print(f"❌ Kafka connection failed: {e}")
        return False

def check_minio_connection():
    """Verifica conexão com MinIO"""
    try:
        from minio import Minio
        from urllib3 import Timeout
        client = Minio(
            'minio:9000',
            access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            secure=False,
            timeout=Timeout(connect=5, read=5)
        )
        list(client.list_buckets())
        print("✅ MinIO connection successful")
        return True
    except Exception as e:
        print(f"❌ MinIO connection failed: {e}")
        return False

def process_with_spark():
    """Processa dados usando Spark Connect"""
    try:
        from pyspark.sql import SparkSession
        
        spark = SparkSession.builder \
            .appName("AirflowSparkJob") \
            .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .remote(os.getenv('SPARK_CONNECT_URL', 'sc://spark-connect:15002')) \
            .getOrCreate()
        
        df = spark.range(100).toDF("number")
        count = df.count()
        
        print(f"✅ Spark processing completed. Processed {count} records")
        spark.stop()
        return True
    except Exception as e:
        print(f"❌ Spark processing failed: {e}")
        return False

# Definição das tasks
check_kafka_task = PythonOperator(
    task_id='check_kafka_connection',
    python_callable=check_kafka_connection,
    execution_timeout=timedelta(seconds=30),
    dag=dag,
)

check_minio_task = PythonOperator(
    task_id='check_minio_connection',
    python_callable=check_minio_connection,
    execution_timeout=timedelta(seconds=30),
    dag=dag,
)

spark_processing_task = PythonOperator(
    task_id='process_with_spark',
    python_callable=process_with_spark,
    execution_timeout=timedelta(minutes=2),
    dag=dag,
)

check_starrocks_task = BashOperator(
    task_id='check_starrocks_health',
    bash_command='timeout 10 curl -f http://starrocks-fe-0:9030/api/health || echo "StarRocks not ready"',
    execution_timeout=timedelta(seconds=15),
    dag=dag,
)

# Definição das dependências
[check_kafka_task, check_minio_task, check_starrocks_task] >> spark_processing_task