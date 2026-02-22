# 🚀 Airflow Elastic - Pipeline de Dados Completo

Plataforma integrada de orquestração de dados com Apache Airflow, Elasticsearch, Kafka, Spark, MinIO e StarRocks.

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Arquitetura](#-arquitetura)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
  - [Docker Local](#docker-local)
  - [Kubernetes Cloud](#kubernetes-cloud)
- [Acesso aos Serviços](#-acesso-aos-serviços)
- [DAGs Disponíveis](#-dags-disponíveis)
- [Exemplos de Uso](#-exemplos-de-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Deploy em Produção](#-deploy-em-produção)
- [Documentação Técnica](#-documentação-técnica)
- [Troubleshooting](#-troubleshooting)

## 🎯 Visão Geral

Este projeto fornece um ambiente completo de engenharia de dados com:

- **Apache Airflow 2.10.4**: Orquestração de workflows
- **Elasticsearch 8.11.0**: Busca e análise de dados
- **Logstash 8.11.0**: Processamento de logs
- **Apache Kafka 7.4.0**: Streaming de dados
- **Apache Spark 4.0**: Processamento distribuído
- **MinIO**: Object storage (S3-compatible)
- **StarRocks**: Data warehouse analítico
- **Apache Superset**: Visualização de dados
- **PostgreSQL 13**: Metastore do Airflow
- **Redis 7.2**: Message broker

## 🏗️ Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Airflow   │────▶│    Kafka     │────▶│    Spark    │
│  (Orq.)     │     │ (Streaming)  │     │ (Process.)  │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │                     │
       ▼                    ▼                     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│Elasticsearch│     │    MinIO     │     │  StarRocks  │
│  (Search)   │     │  (Storage)   │     │    (DW)     │
└─────────────┘     └──────────────┘     └─────────────┘
       │                                          │
       ▼                                          ▼
┌─────────────┐                          ┌─────────────┐
│  Logstash   │                          │  Superset   │
│   (Logs)    │                          │   (BI)      │
└─────────────┘                          └─────────────┘
```

## 💻 Pré-requisitos

- **Docker Desktop** 4.0+ com Docker Compose
- **Recursos mínimos**:
  - 8GB RAM (recomendado 16GB)
  - 4 CPUs
  - 20GB espaço em disco
- **Sistema Operacional**: Windows 10/11, Linux ou macOS

## 🔧 Instalação

### Docker Local

#### 1. Clone o Repositório

```bash
git clone <repository-url>
cd airflow_elastic
```

#### 2. Configure as Variáveis de Ambiente

O arquivo `.env` já está configurado com:

```bash
# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Endpoints
KAFKA_BROKERS=kafka:9093
KAFKA_SCHEMA_REGISTRY=http://schema-registry:8081
ELASTICSEARCH_HOST=http://elasticsearch:9200
SPARK_CONNECT_URL=sc://spark-connect:15002

# Airflow
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
```

#### 3. Inicie os Serviços

```bash
docker-compose -f docker-compose-airflow.yml up -d
```

**Tempo estimado**: 5-10 minutos para primeira inicialização.

#### 4. Verifique o Status

```bash
docker-compose -f docker-compose-airflow.yml ps
```

Todos os serviços devem estar com status `healthy` ou `running`.

### Kubernetes Cloud

Para deploy em produção em AWS EKS, GCP GKE ou Azure AKS:

#### 1. Pré-requisitos

```bash
# Instalar kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# Instalar kustomize
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
```

#### 2. Criar Cluster

**AWS EKS**:
```bash
eksctl create cluster \
  --name airflow-elastic \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.xlarge \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10
```

**GCP GKE**:
```bash
gcloud container clusters create airflow-elastic \
  --zone us-central1-a \
  --machine-type n1-standard-4 \
  --num-nodes 3 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 10
```

**Azure AKS**:
```bash
az aks create \
  --resource-group airflow-rg \
  --name airflow-elastic \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 10
```

#### 3. Deploy

**Desenvolvimento**:
```bash
kubectl apply -k k8s/overlays/dev/
```

**Produção**:
```bash
# Atualizar secrets
kubectl create secret generic airflow-secrets \
  --from-literal=MINIO_ACCESS_KEY=<seu-access-key> \
  --from-literal=MINIO_SECRET_KEY=<seu-secret-key> \
  --from-literal=AIRFLOW_WWW_USER_PASSWORD=<senha-forte> \
  -n airflow-elastic

# Deploy
kubectl apply -k k8s/overlays/prod/
```

#### 4. Verificar Status

```bash
kubectl get pods -n airflow-elastic
kubectl get svc -n airflow-elastic
```

**Documentação completa**: [k8s/README.md](k8s/README.md)

## 🌐 Acesso aos Serviços

### Apache Airflow
- **URL**: http://localhost:8080
- **Usuário**: `airflow`
- **Senha**: `airflow`
- **Descrição**: Interface web para gerenciar e monitorar DAGs

### Elasticsearch
- **URL**: http://localhost:9200
- **Autenticação**: Desabilitada
- **API Health**: http://localhost:9200/_cluster/health
- **Descrição**: Motor de busca e análise

### Logstash
- **Porta TCP**: 5000
- **API Monitoring**: http://localhost:9600
- **Descrição**: Pipeline de processamento de dados

### Apache Kafka
- **Bootstrap Server**: localhost:9092
- **Internal**: kafka:9093
- **Schema Registry**: http://localhost:8081
- **Descrição**: Plataforma de streaming

### MinIO (S3)
- **Console**: http://localhost:9001
- **API**: http://localhost:9000
- **Usuário**: `minioadmin`
- **Senha**: `minioadmin`
- **Descrição**: Object storage

### StarRocks
- **FE Query**: http://localhost:9030
- **FE HTTP**: http://localhost:8030
- **BE**: http://localhost:8040
- **Descrição**: Data warehouse analítico

### Apache Superset
- **URL**: http://localhost:8088
- **Usuário**: `admin`
- **Senha**: `admin`
- **Descrição**: Plataforma de BI e visualização

### Spark Connect
- **URL**: sc://localhost:15002
- **Spark UI**: http://localhost:4040
- **Descrição**: Servidor Spark Connect

### Zookeeper
- **Porta**: 2181
- **Descrição**: Coordenação de serviços distribuídos

## 📊 DAGs Disponíveis

### 1. `data_pipeline_example`
**Descrição**: Pipeline completo demonstrando integração entre serviços.

**Tasks**:
- `check_kafka_connection`: Valida conectividade com Kafka
- `check_minio_connection`: Valida conectividade com MinIO
- `check_starrocks_health`: Verifica saúde do StarRocks
- `process_with_spark`: Processa dados com Spark

**Execução**:
1. Acesse Airflow: http://localhost:8080
2. Localize a DAG `data_pipeline_example`
3. Ative o toggle (ON)
4. Clique em "Trigger DAG" (▶️)

### 2. `kafka_integration_demo`
**Descrição**: Demonstração de produção e consumo de mensagens Kafka.

**Tasks**:
- `verify_kafka_connectivity`: Verifica conexão
- `create_kafka_topic`: Cria tópico `airflow-demo-topic`
- `produce_messages`: Produz 3 mensagens de sensores
- `consume_messages`: Consome mensagens
- `list_kafka_topics`: Lista todos os tópicos

**Execução**:
1. Acesse Airflow: http://localhost:8080
2. Localize a DAG `kafka_integration_demo`
3. Clique em "Trigger DAG" (▶️)
4. Monitore logs em tempo real

### 3. `elasticsearch_indexer`
**Descrição**: Indexa dados do CSV no Elasticsearch.

**Tasks**:
- `check_elasticsearch`: Verifica conexão com Elasticsearch
- `create_index`: Cria índice `mm_dataset`
- `index_csv_data`: Indexa dados de `data/mm_dataset.csv`
- `get_stats`: Exibe estatísticas e agregações

**Execução**:
1. Acesse Airflow: http://localhost:8080
2. Localize a DAG `elasticsearch_indexer`
3. Clique em "Trigger DAG" (▶️)
4. Aguarde conclusão (~30 segundos)

**Verificar Dados Indexados**:
```bash
# Total de documentos
curl http://localhost:9200/mm_dataset/_count

# Buscar documentos
curl http://localhost:9200/mm_dataset/_search?size=10

# Agregação por estado
curl -X GET "http://localhost:9200/mm_dataset/_search" -H 'Content-Type: application/json' -d'
{
  "size": 0,
  "aggs": {
    "by_state": {
      "terms": { "field": "state", "size": 10 }
    }
  }
}
'
```

### 4. `spark_elasticsearch_pipeline`
**Descrição**: Pipeline integrado Spark Connect + Elasticsearch para processar agregações.

**Tasks**:
- `process_with_spark_and_index`: Processa CSV com Spark, realiza agregações e indexa no Elasticsearch
- `verify_elasticsearch_indices`: Verifica índices criados e exibe top 3
- `create_elasticsearch_visualization`: Gera queries de visualização e estatísticas

**Fluxo de Processamento**:
1. Conecta ao Spark via Spark Connect (`sc://spark-connect:15002`)
2. Lê CSV com Spark DataFrame
3. Realiza agregações:
   - Por Estado: count, sum, avg
   - Por Cor: count, sum
4. Converte Spark → Pandas
5. Indexa em 2 índices Elasticsearch:
   - `mm_state_aggregations`
   - `mm_color_aggregations`

**Execução**:
1. Acesse Airflow: http://localhost:8080
2. Localize a DAG `spark_elasticsearch_pipeline`
3. Clique em "Trigger DAG" (▶️)
4. Aguarde conclusão (~1-2 minutos)

**Consultar Resultados**:
```bash
# Top 5 estados
curl -X GET "http://localhost:9200/mm_state_aggregations/_search" -H 'Content-Type: application/json' -d'
{
  "size": 5,
  "sort": [{"total_count": {"order": "desc"}}]
}
'

# Distribuição de cores
curl -X GET "http://localhost:9200/mm_color_aggregations/_search" -H 'Content-Type: application/json' -d'
{
  "size": 10,
  "sort": [{"total_count": {"order": "desc"}}]
}
'
```

## 🎓 Exemplos de Uso

### Exemplo 1: Consultar Elasticsearch via Python

```python
from elasticsearch import Elasticsearch

es = Elasticsearch(['http://localhost:9200'])

# Buscar documentos
result = es.search(index='mm_dataset', body={
    'query': {'match': {'state': 'CA'}},
    'size': 10
})

for hit in result['hits']['hits']:
    print(hit['_source'])
```

### Exemplo 2: Produzir Mensagem no Kafka

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

producer.send('test-topic', {'message': 'Hello Kafka!'})
producer.flush()
```

### Exemplo 3: Processar com Spark Connect

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum as spark_sum, avg

spark = SparkSession.builder \
    .appName("Example") \
    .remote("sc://localhost:15002") \
    .getOrCreate()

df = spark.read.csv('/opt/spark/work-dir/data/mm_dataset.csv', header=True, inferSchema=True)

# Agregações
agg_df = df.groupBy('State') \
    .agg(
        count('*').alias('total'),
        spark_sum('Count').alias('sum_count'),
        avg('Count').alias('avg_count')
    ) \
    .orderBy(col('sum_count').desc())

agg_df.show(10)
```

### Exemplo 4: Upload para MinIO

```python
from minio import Minio

client = Minio(
    'localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False
)

# Upload arquivo
client.fput_object('my-bucket', 'data.csv', 'local-file.csv')
```

### Exemplo 5: Pipeline Spark + Elasticsearch

```python
from pyspark.sql import SparkSession
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# Processar com Spark
spark = SparkSession.builder.remote("sc://localhost:15002").getOrCreate()
df = spark.read.csv('data.csv', header=True, inferSchema=True)
agg_df = df.groupBy('category').count()
pandas_df = agg_df.toPandas()

# Indexar no Elasticsearch
es = Elasticsearch(['http://localhost:9200'])

def generate_docs():
    for _, row in pandas_df.iterrows():
        yield {
            "_index": "aggregations",
            "_source": {"category": row['category'], "count": int(row['count'])}
        }

bulk(es, generate_docs())
```

## 📁 Estrutura do Projeto

```
airflow_elastic/
├── .devcontainer/          # Configuração DevContainer
│   ├── devcontainer.json
│   └── Dockerfile
├── dags/                   # DAGs do Airflow
│   ├── data_pipeline_example.py
│   ├── kafka_integration_demo.py
│   ├── elasticsearch_indexer.py
│   └── spark_elasticsearch_pipeline.py
├── data/                   # Dados de entrada
│   └── mm_dataset.csv
├── docs/                   # Documentação técnica
│   └── artigo_dags_elasticsearch.md
├── k8s/                    # Kubernetes manifests
│   ├── base/               # Configurações base
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml
│   │   ├── secret.yaml
│   │   ├── pvc.yaml
│   │   ├── postgres.yaml
│   │   ├── redis.yaml
│   │   ├── elasticsearch.yaml
│   │   ├── kafka.yaml
│   │   ├── minio.yaml
│   │   ├── spark.yaml
│   │   ├── airflow-webserver.yaml
│   │   ├── airflow-scheduler.yaml
│   │   ├── airflow-worker.yaml
│   │   ├── hpa.yaml
│   │   ├── ingress.yaml
│   │   └── kustomization.yaml
│   ├── overlays/
│   │   ├── dev/            # Ambiente desenvolvimento
│   │   └── prod/           # Ambiente produção
│   └── README.md
├── logs/                   # Logs do Airflow
├── plugins/                # Plugins customizados
├── config/                 # Configurações
│   └── airflow.cfg
├── spark-connect/          # Configuração Spark
│   ├── Dockerfile
│   └── conf/
├── .env                    # Variáveis de ambiente
├── docker-compose-airflow.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 🔍 Troubleshooting

### Serviços não iniciam

```bash
# Verificar logs
docker-compose -f docker-compose-airflow.yml logs <service-name>

# Reiniciar serviço específico
docker-compose -f docker-compose-airflow.yml restart <service-name>
```

### Elasticsearch não responde

```bash
# Verificar saúde
curl http://localhost:9200/_cluster/health

# Verificar logs
docker logs elasticsearch
```

### Airflow DAG não aparece

```bash
# Verificar erros de parsing
docker exec -it <airflow-scheduler-container> airflow dags list-import-errors

# Forçar atualização
docker exec -it <airflow-scheduler-container> airflow dags reserialize
```

### Kafka não conecta

```bash
# Verificar tópicos
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Testar produção
docker exec -it kafka kafka-console-producer --topic test --bootstrap-server localhost:9092
```

### Limpar ambiente

```bash
# Parar todos os serviços
docker-compose -f docker-compose-airflow.yml down

# Remover volumes (CUIDADO: apaga dados)
docker-compose -f docker-compose-airflow.yml down -v

# Limpar tudo e reiniciar
docker-compose -f docker-compose-airflow.yml down -v
docker system prune -a
docker-compose -f docker-compose-airflow.yml up -d
```

### Problemas de memória

Ajuste recursos no Docker Desktop:
- Settings → Resources → Memory: 8GB+
- Settings → Resources → CPUs: 4+

### Portas em conflito

Verifique portas em uso:
```bash
# Windows
netstat -ano | findstr :<PORT>

# Linux/Mac
lsof -i :<PORT>
```

Portas utilizadas: 2181, 5000, 8030, 8040, 8080, 8081, 8088, 9000, 9001, 9020, 9030, 9092, 9200, 9300, 9600, 15002

## 🚀 Deploy em Produção

### Ambientes Disponíveis

| Ambiente | Réplicas Workers | Elasticsearch Nodes | Custo Estimado/Mês |
|----------|------------------|---------------------|--------------------|
| **Dev** | 1 | 1 | $150-300 |
| **Prod** | 5 | 3 | $800-1500 |

### Recursos Kubernetes

✅ **Infraestrutura**:
- PostgreSQL (metastore)
- Redis (message broker)
- Elasticsearch (busca/análise)
- Kafka + Zookeeper (streaming)
- MinIO (object storage)
- Spark Connect (processamento)

✅ **Airflow**:
- Webserver (UI com LoadBalancer)
- Scheduler (orquestração)
- Worker (execução Celery com HPA)

✅ **Features Avançadas**:
- HorizontalPodAutoscaler (escalonamento automático)
- Ingress com HTTPS (cert-manager)
- PersistentVolumeClaims (armazenamento persistente)
- ConfigMaps e Secrets (configuração segura)

### Clouds Suportadas

- ☁️ **AWS EKS** (Elastic Kubernetes Service)
- ☁️ **GCP GKE** (Google Kubernetes Engine)
- ☁️ **Azure AKS** (Azure Kubernetes Service)
- 🏠 **On-premises** (Kubernetes self-hosted)

**Documentação completa**: [k8s/README.md](k8s/README.md)

## 📖 Documentação Técnica

### Artigos Disponíveis

#### [Pipeline de Dados com Elasticsearch e Apache Airflow](docs/artigo_dags_elasticsearch.md)

Artigo técnico completo sobre as DAGs do Elasticsearch:

**Conteúdo**:
- ✅ Análise detalhada de cada DAG e task
- ✅ Conceitos fundamentais (Idempotência, Bulk Operations, Schema Design)
- ✅ Padrões e boas práticas de engenharia de dados
- ✅ Casos de uso reais (E-commerce, Fintech, IoT, Log Analytics)
- ✅ Otimizações avançadas e tuning de performance
- ✅ Comparações técnicas (Spark vs Pandas, keyword vs text)
- ✅ Métricas e monitoramento

**Público-alvo**:
- Engenheiros de dados iniciantes a avançados
- Desenvolvedores aprendendo Big Data
- Arquitetos de soluções de dados

**Tópicos abordados**:
1. DAG 1: Elasticsearch Indexer (indexação básica)
2. DAG 2: Spark Elasticsearch Pipeline (processamento distribuído)
3. Conceitos fundamentais para engenheiros de dados
4. Padrões e boas práticas
5. Casos de uso reais em produção
6. Próximos passos e evoluções

## 📚 Recursos Adicionais

### Documentação Oficial

- [Documentação Apache Airflow](https://airflow.apache.org/docs/)
- [Documentação Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Documentação Apache Kafka](https://kafka.apache.org/documentation/)
- [Documentação Apache Spark](https://spark.apache.org/docs/latest/)
- [Documentação MinIO](https://min.io/docs/minio/linux/index.html)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

### Guias do Projeto

- [Deploy Kubernetes](k8s/README.md) - Guia completo de deploy em cloud
- [Artigo Elasticsearch DAGs](docs/artigo_dags_elasticsearch.md) - Análise técnica detalhada

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT.

## 👥 Equipe

Desenvolvido pela equipe de Data Engineering.

## 📊 Status do Projeto

- ✅ Docker Compose para desenvolvimento local
- ✅ 4 DAGs funcionais (Kafka, Elasticsearch, Spark)
- ✅ Kubernetes manifests para produção
- ✅ Documentação técnica completa
- ✅ Suporte para AWS, GCP e Azure
- ✅ HPA e autoscaling configurado
- ✅ Ingress com HTTPS
- 🔄 Monitoramento com Prometheus/Grafana (em desenvolvimento)
- 🔄 CI/CD pipeline (em desenvolvimento)

---

## 🎯 Próximos Passos

### Para Iniciantes
1. ✅ Execute as DAGs localmente com Docker
2. ✅ Leia o [artigo técnico](docs/artigo_dags_elasticsearch.md)
3. ✅ Experimente modificar as DAGs
4. ✅ Explore queries no Elasticsearch

### Para Intermediários
1. ✅ Deploy em Kubernetes (ambiente dev)
2. ✅ Implemente novas DAGs
3. ✅ Configure monitoramento
4. ✅ Otimize performance

### Para Avançados
1. ✅ Deploy em produção com alta disponibilidade
2. ✅ Implemente streaming com Kafka
3. ✅ Adicione Machine Learning ao pipeline
4. ✅ Configure observabilidade completa

---

**Nota**: Este projeto fornece ambientes para desenvolvimento (Docker) e produção (Kubernetes). Configure autenticação, SSL/TLS e ajuste recursos conforme necessário.
