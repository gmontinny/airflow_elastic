from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import csv
import os
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 15),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def check_elasticsearch_connection():
    """Verifica conexão com Elasticsearch"""
    es_host = os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')
    es = Elasticsearch([es_host])
    
    if es.ping():
        print(f"✅ Elasticsearch conectado: {es_host}")
        info = es.info()
        print(f"Cluster: {info['cluster_name']}, Versão: {info['version']['number']}")
        return True
    else:
        raise Exception("❌ Falha ao conectar no Elasticsearch")

def create_index():
    """Cria índice no Elasticsearch"""
    es_host = os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')
    es = Elasticsearch([es_host])
    
    index_name = 'mm_dataset'
    
    if es.indices.exists(index=index_name):
        print(f"Índice '{index_name}' já existe")
        return
    
    mapping = {
        "mappings": {
            "properties": {
                "state": {"type": "keyword"},
                "color": {"type": "keyword"},
                "count": {"type": "integer"}
            }
        }
    }
    
    es.indices.create(index=index_name, body=mapping)
    print(f"✅ Índice '{index_name}' criado com sucesso")

def index_csv_data():
    """Lê CSV e indexa dados no Elasticsearch"""
    es_host = os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')
    es = Elasticsearch([es_host])
    
    csv_path = '/opt/airflow/work-dir/data/mm_dataset.csv'
    index_name = 'mm_dataset'
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")
    
    def generate_docs():
        with open(csv_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                yield {
                    "_index": index_name,
                    "_source": {
                        "state": row['State'],
                        "color": row['Color'],
                        "count": int(row['Count'])
                    }
                }
    
    success, failed = bulk(es, generate_docs(), chunk_size=1000, raise_on_error=False)
    print(f"✅ Indexados {success} documentos")
    if failed:
        print(f"⚠️ Falhas: {len(failed)}")

def get_index_stats():
    """Obtém estatísticas do índice"""
    es_host = os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')
    es = Elasticsearch([es_host])
    
    index_name = 'mm_dataset'
    
    count = es.count(index=index_name)['count']
    print(f"📊 Total de documentos no índice '{index_name}': {count}")
    
    agg_query = {
        "size": 0,
        "aggs": {
            "by_state": {
                "terms": {"field": "state", "size": 5}
            },
            "by_color": {
                "terms": {"field": "color", "size": 5}
            }
        }
    }
    
    result = es.search(index=index_name, body=agg_query)
    
    print("\n🔝 Top 5 Estados:")
    for bucket in result['aggregations']['by_state']['buckets']:
        print(f"  {bucket['key']}: {bucket['doc_count']} docs")
    
    print("\n🎨 Top 5 Cores:")
    for bucket in result['aggregations']['by_color']['buckets']:
        print(f"  {bucket['key']}: {bucket['doc_count']} docs")

with DAG(
    'elasticsearch_indexer',
    default_args=default_args,
    description='Indexa dados do CSV no Elasticsearch',
    schedule_interval=None,
    catchup=False,
    tags=['elasticsearch', 'indexer', 'csv'],
) as dag:

    check_es = PythonOperator(
        task_id='check_elasticsearch',
        python_callable=check_elasticsearch_connection,
    )

    create_idx = PythonOperator(
        task_id='create_index',
        python_callable=create_index,
    )

    index_data = PythonOperator(
        task_id='index_csv_data',
        python_callable=index_csv_data,
    )

    stats = PythonOperator(
        task_id='get_stats',
        python_callable=get_index_stats,
    )

    check_es >> create_idx >> index_data >> stats
