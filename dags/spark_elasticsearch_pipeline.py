from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import os

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 15),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def process_with_spark_and_index():
    """Processa CSV com Spark e indexa no Elasticsearch"""
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, count, sum as spark_sum, avg, upper
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk
    
    spark_url = os.getenv('SPARK_CONNECT_URL', 'sc://spark-connect:15002')
    es_host = os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')
    
    print(f"🔗 Conectando ao Spark: {spark_url}")
    spark = SparkSession.builder \
        .appName("SparkElasticsearchIndexer") \
        .remote(spark_url) \
        .getOrCreate()
    
    csv_path = '/opt/spark/work-dir/data/mm_dataset.csv'
    print(f"📂 Lendo CSV: {csv_path}")
    
    df = spark.read.csv(csv_path, header=True, inferSchema=True)
    
    print(f"📊 Total de registros: {df.count()}")
    df.printSchema()
    
    # Agregações por estado
    state_agg = df.groupBy('State') \
        .agg(
            count('*').alias('total_records'),
            spark_sum('Count').alias('total_count'),
            avg('Count').alias('avg_count')
        ) \
        .orderBy(col('total_count').desc())
    
    print("\n🗺️ Top 10 Estados:")
    state_agg.show(10)
    
    # Agregações por cor
    color_agg = df.groupBy('Color') \
        .agg(
            count('*').alias('total_records'),
            spark_sum('Count').alias('total_count')
        ) \
        .orderBy(col('total_count').desc())
    
    print("\n🎨 Agregação por Cor:")
    color_agg.show()
    
    # Converter para Pandas para indexar
    print("\n📤 Convertendo para Pandas...")
    state_pandas = state_agg.toPandas()
    color_pandas = color_agg.toPandas()
    
    spark.stop()
    
    # Indexar no Elasticsearch
    print(f"\n🔍 Conectando ao Elasticsearch: {es_host}")
    es = Elasticsearch([es_host])
    
    # Criar índices
    state_index = 'mm_state_aggregations'
    color_index = 'mm_color_aggregations'
    
    for index in [state_index, color_index]:
        if es.indices.exists(index=index):
            es.indices.delete(index=index)
            print(f"🗑️ Índice '{index}' removido")
        es.indices.create(index=index)
        print(f"✅ Índice '{index}' criado")
    
    # Indexar agregações de estado
    def generate_state_docs():
        for _, row in state_pandas.iterrows():
            yield {
                "_index": state_index,
                "_source": {
                    "state": row['State'],
                    "total_records": int(row['total_records']),
                    "total_count": int(row['total_count']),
                    "avg_count": float(row['avg_count']),
                    "processed_at": datetime.now().isoformat()
                }
            }
    
    success_state, _ = bulk(es, generate_state_docs(), chunk_size=100)
    print(f"✅ Indexados {success_state} documentos em '{state_index}'")
    
    # Indexar agregações de cor
    def generate_color_docs():
        for _, row in color_pandas.iterrows():
            yield {
                "_index": color_index,
                "_source": {
                    "color": row['Color'],
                    "total_records": int(row['total_records']),
                    "total_count": int(row['total_count']),
                    "processed_at": datetime.now().isoformat()
                }
            }
    
    success_color, _ = bulk(es, generate_color_docs(), chunk_size=100)
    print(f"✅ Indexados {success_color} documentos em '{color_index}'")
    
    return {
        'state_docs': success_state,
        'color_docs': success_color
    }

def verify_elasticsearch_indices():
    """Verifica índices criados no Elasticsearch"""
    from elasticsearch import Elasticsearch
    
    es_host = os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')
    es = Elasticsearch([es_host])
    
    indices = ['mm_state_aggregations', 'mm_color_aggregations']
    
    for index in indices:
        count = es.count(index=index)['count']
        print(f"\n📊 Índice: {index}")
        print(f"   Total documentos: {count}")
        
        # Buscar top 3
        result = es.search(index=index, body={
            "size": 3,
            "sort": [{"total_count": {"order": "desc"}}]
        })
        
        print(f"   Top 3:")
        for hit in result['hits']['hits']:
            source = hit['_source']
            if 'state' in source:
                print(f"     - {source['state']}: {source['total_count']} (avg: {source['avg_count']:.2f})")
            else:
                print(f"     - {source['color']}: {source['total_count']}")

def create_elasticsearch_visualization():
    """Cria queries de exemplo para visualização"""
    from elasticsearch import Elasticsearch
    
    es_host = os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')
    es = Elasticsearch([es_host])
    
    print("\n📈 Queries de Visualização:\n")
    
    # Top 5 estados
    print("🗺️ Top 5 Estados por Total Count:")
    result = es.search(index='mm_state_aggregations', body={
        "size": 5,
        "sort": [{"total_count": {"order": "desc"}}],
        "query": {"match_all": {}}
    })
    
    for i, hit in enumerate(result['hits']['hits'], 1):
        s = hit['_source']
        print(f"   {i}. {s['state']}: {s['total_count']:,} (média: {s['avg_count']:.2f})")
    
    # Distribuição de cores
    print("\n🎨 Distribuição de Cores:")
    result = es.search(index='mm_color_aggregations', body={
        "size": 10,
        "sort": [{"total_count": {"order": "desc"}}]
    })
    
    for hit in result['hits']['hits']:
        s = hit['_source']
        print(f"   {s['color']}: {s['total_count']:,} registros")
    
    # Estatísticas gerais
    print("\n📊 Estatísticas Gerais:")
    state_count = es.count(index='mm_state_aggregations')['count']
    color_count = es.count(index='mm_color_aggregations')['count']
    print(f"   Estados únicos: {state_count}")
    print(f"   Cores únicas: {color_count}")

with DAG(
    'spark_elasticsearch_pipeline',
    default_args=default_args,
    description='Pipeline Spark + Elasticsearch para processar e indexar agregações',
    schedule_interval=None,
    catchup=False,
    tags=['spark', 'elasticsearch', 'aggregation', 'analytics'],
) as dag:

    process_task = PythonOperator(
        task_id='process_with_spark_and_index',
        python_callable=process_with_spark_and_index,
    )

    verify_task = PythonOperator(
        task_id='verify_elasticsearch_indices',
        python_callable=verify_elasticsearch_indices,
    )

    visualize_task = PythonOperator(
        task_id='create_elasticsearch_visualization',
        python_callable=create_elasticsearch_visualization,
    )

    process_task >> verify_task >> visualize_task
