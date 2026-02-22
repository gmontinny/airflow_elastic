from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import os

dag = DAG(
    'pyspark_demo',
    start_date=datetime(2025, 10, 11, 10, 45),
    schedule_interval='@once',
    catchup=False,
    is_paused_upon_creation=False,
    tags=['pyspark', 'demo'],
)

def test_pyspark():
    """Testa se PySpark está funcionando"""
    try:
        from pyspark.sql import SparkSession
        
        spark = SparkSession.builder \
            .appName("PySparkTest") \
            .remote(os.getenv('SPARK_CONNECT_URL', 'sc://spark-connect:15002')) \
            .getOrCreate()
        
        # Criar DataFrame simples
        df = spark.range(10).toDF("number")
        df = df.withColumn("squared", df.number * df.number)
        
        print("✅ PySpark funcionando!")
        print(f"DataFrame criado com {df.count()} linhas")
        df.show()
        
        spark.stop()
        return "success"
    except Exception as e:
        print(f"❌ PySpark falhou: {e}")
        raise

test_task = PythonOperator(
    task_id='test_pyspark',
    python_callable=test_pyspark,
    dag=dag,
)