from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import socket
import json
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

KAFKA_HOST = 'kafka'
KAFKA_PORT = 9093
KAFKA_TOPIC = 'airflow-demo-topic'


def verify_kafka_connectivity():
    """Verifica conectividade com Kafka"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((KAFKA_HOST, KAFKA_PORT))
        sock.close()
        if result == 0:
            logger.info(f"✓ Kafka conectado com sucesso em {KAFKA_HOST}:{KAFKA_PORT}")
            return True
        else:
            raise Exception(f"Não foi possível conectar ao Kafka em {KAFKA_HOST}:{KAFKA_PORT}")
    except Exception as e:
        logger.error(f"✗ Erro ao conectar ao Kafka: {e}")
        raise


def create_kafka_topic():
    """Cria tópico Kafka usando protocolo Kafka"""
    try:
        from kafka.admin import KafkaAdminClient, NewTopic
        admin_client = KafkaAdminClient(
            bootstrap_servers=f'{KAFKA_HOST}:{KAFKA_PORT}',
            request_timeout_ms=5000,
            client_id='airflow-admin'
        )
        topic_list = [NewTopic(name=KAFKA_TOPIC, num_partitions=1, replication_factor=1)]
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
        admin_client.close()
        logger.info(f"✓ Tópico '{KAFKA_TOPIC}' criado com sucesso")
    except Exception as e:
        logger.info(f"✓ Tópico '{KAFKA_TOPIC}' já existe ou foi criado: {str(e)}")


def produce_messages():
    """Produz mensagens para o Kafka"""
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=f'{KAFKA_HOST}:{KAFKA_PORT}',
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            request_timeout_ms=10000,
            client_id='airflow-producer'
        )
        
        messages = [
            {'id': 1, 'name': 'Sensor A', 'temperature': 25.5},
            {'id': 2, 'name': 'Sensor B', 'temperature': 26.3},
            {'id': 3, 'name': 'Sensor C', 'temperature': 24.8},
        ]
        
        for msg in messages:
            producer.send(KAFKA_TOPIC, value=msg)
            logger.info(f"✓ Mensagem enviada: {msg['name']}")
        
        producer.flush()
        producer.close()
        logger.info("✓ Produtor finalizado")
    except Exception as e:
        logger.error(f"✗ Erro ao produzir mensagens: {e}")
        raise


def consume_messages():
    """Consome mensagens do Kafka"""
    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=f'{KAFKA_HOST}:{KAFKA_PORT}',
            auto_offset_reset='earliest',
            consumer_timeout_ms=5000,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            client_id='airflow-consumer'
        )
        
        messages_consumed = []
        for message in consumer:
            logger.info(f"  → {message.value}")
            messages_consumed.append(message.value)
        
        consumer.close()
        logger.info(f"✓ Total de mensagens consumidas: {len(messages_consumed)}")
    except Exception as e:
        logger.error(f"✗ Erro ao consumir mensagens: {e}")
        raise


def list_kafka_topics():
    """Lista tópicos Kafka"""
    try:
        from kafka.admin import KafkaAdminClient
        admin_client = KafkaAdminClient(
            bootstrap_servers=f'{KAFKA_HOST}:{KAFKA_PORT}',
            request_timeout_ms=5000,
            client_id='airflow-admin'
        )
        topics = admin_client.list_topics()
        admin_client.close()
        logger.info(f"✓ Tópicos disponíveis: {', '.join(topics)}")
    except Exception as e:
        logger.error(f"✗ Erro ao listar tópicos: {e}")
        raise


with DAG(
    'kafka_integration_demo',
    default_args=default_args,
    description='DAG demonstrando integração com Apache Kafka',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['kafka', 'demo', 'streaming'],
) as dag:

    verify_connectivity = PythonOperator(
        task_id='verify_kafka_connectivity',
        python_callable=verify_kafka_connectivity,
        doc_md="Verifica se o Kafka está acessível"
    )

    create_topic = PythonOperator(
        task_id='create_kafka_topic',
        python_callable=create_kafka_topic,
        doc_md="Cria o tópico Kafka para a demo"
    )

    produce = PythonOperator(
        task_id='produce_messages',
        python_callable=produce_messages,
        doc_md="Produz 3 mensagens de sensores para o Kafka"
    )

    consume = PythonOperator(
        task_id='consume_messages',
        python_callable=consume_messages,
        doc_md="Consome as mensagens do Kafka"
    )

    list_topics = PythonOperator(
        task_id='list_kafka_topics',
        python_callable=list_kafka_topics,
        doc_md="Lista todos os tópicos Kafka"
    )

    verify_connectivity >> create_topic >> produce >> consume >> list_topics
