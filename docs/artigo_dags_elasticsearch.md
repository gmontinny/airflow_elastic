# 📊 Pipeline de Dados com Elasticsearch e Apache Airflow: Um Guia Completo para Engenheiros de Dados

## 🎯 Introdução

Este artigo explora a implementação de pipelines de dados modernos utilizando **Apache Airflow** para orquestração e **Elasticsearch** como motor de busca e análise. Através de duas DAGs complementares, demonstramos desde a indexação básica até processamento distribuído com **Apache Spark**, fornecendo conhecimento essencial para engenheiros de dados que desejam construir arquiteturas escaláveis e eficientes.

## 📚 Índice

1. [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
2. [DAG 1: Elasticsearch Indexer](#dag-1-elasticsearch-indexer)
3. [DAG 2: Spark Elasticsearch Pipeline](#dag-2-spark-elasticsearch-pipeline)
4. [Conceitos Fundamentais](#conceitos-fundamentais)
5. [Padrões e Boas Práticas](#padrões-e-boas-práticas)
6. [Casos de Uso Reais](#casos-de-uso-reais)
7. [Conclusão](#conclusão)

---

## 🏗️ Visão Geral da Arquitetura

### Stack Tecnológico

```
┌─────────────────┐
│  Apache Airflow │  ← Orquestração de workflows
└────────┬────────┘
         │
         ├──────────────┐
         ▼              ▼
┌─────────────┐  ┌──────────────┐
│ Elasticsearch│  │ Apache Spark │
│  (Indexação) │  │ (Processamento)│
└─────────────┘  └──────────────┘
         │              │
         └──────┬───────┘
                ▼
         ┌──────────────┐
         │  Dados CSV   │
         └──────────────┘
```

### Fluxo de Dados

1. **Ingestão**: Leitura de dados brutos (CSV)
2. **Transformação**: Processamento com Spark (agregações, limpeza)
3. **Indexação**: Armazenamento no Elasticsearch
4. **Análise**: Queries e agregações para insights

---

## 📥 DAG 1: Elasticsearch Indexer

### Objetivo

Demonstrar o processo fundamental de **indexação de dados** no Elasticsearch, estabelecendo a base para operações de busca e análise em tempo real.

### Arquitetura da DAG

```python
check_elasticsearch → create_index → index_csv_data → get_stats
```

### Análise Técnica das Tasks

#### Task 1: `check_elasticsearch_connection`

**Propósito**: Validar conectividade e disponibilidade do cluster Elasticsearch.

```python
def check_elasticsearch_connection():
    es_host = os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')
    es = Elasticsearch([es_host])
    
    if es.ping():
        info = es.info()
        print(f"Cluster: {info['cluster_name']}, Versão: {info['version']['number']}")
        return True
    else:
        raise Exception("❌ Falha ao conectar no Elasticsearch")
```

**Conceitos-chave**:
- **Health Check**: Verificação de disponibilidade antes de operações críticas
- **Fail-fast**: Interrompe pipeline se infraestrutura não está disponível
- **Configuração via Ambiente**: Uso de variáveis de ambiente para flexibilidade

**Por que é importante?**
- Evita falhas silenciosas em produção
- Reduz tempo de troubleshooting
- Implementa princípio de "circuit breaker"

---

#### Task 2: `create_index`

**Propósito**: Criar índice com schema definido (mapping).

```python
def create_index():
    index_name = 'mm_dataset'
    
    mapping = {
        "mappings": {
            "properties": {
                "state": {"type": "keyword"},    # Valores exatos, agregações
                "color": {"type": "keyword"},    # Valores exatos, agregações
                "count": {"type": "integer"}     # Valores numéricos
            }
        }
    }
    
    es.indices.create(index=index_name, body=mapping)
```

**Conceitos-chave**:

1. **Schema Design**:
   - `keyword`: Para campos que não precisam de análise textual (estados, categorias)
   - `integer`: Para valores numéricos que serão agregados
   - Definir tipos corretos otimiza armazenamento e performance

2. **Idempotência**:
   - Verifica se índice já existe antes de criar
   - Evita erros em re-execuções da DAG

**Decisões de Design**:
- **Por que keyword e não text?** 
  - `keyword`: Armazena valor exato, ideal para filtros e agregações
  - `text`: Analisa e tokeniza, ideal para busca full-text
  - Estados e cores são categorias fixas → `keyword`

---

#### Task 3: `index_csv_data`

**Propósito**: Ingestão em massa de dados no Elasticsearch.

```python
def index_csv_data():
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
    
    success, failed = bulk(es, generate_docs(), chunk_size=1000)
```

**Conceitos-chave**:

1. **Bulk API**:
   - Indexa múltiplos documentos em uma única requisição
   - Reduz overhead de rede (1000x mais eficiente que indexação individual)
   - Essencial para ingestão de grandes volumes

2. **Generator Pattern**:
   - Usa `yield` para processar dados sob demanda
   - Evita carregar todo CSV na memória
   - Escalável para arquivos de GB/TB

3. **Error Handling**:
   - Retorna documentos com sucesso e falhas separadamente
   - Permite retry seletivo de falhas

**Performance**:
- **Chunk Size**: 1000 documentos por batch (ajustável)
- **Memory Footprint**: Constante, independente do tamanho do arquivo
- **Throughput**: ~10.000-50.000 docs/segundo (depende do cluster)

---

#### Task 4: `get_index_stats`

**Propósito**: Validar indexação e gerar insights iniciais.

```python
def get_index_stats():
    agg_query = {
        "size": 0,  # Não retorna documentos, apenas agregações
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
```

**Conceitos-chave**:

1. **Aggregations**:
   - `terms`: Agrupa por valores únicos (similar a GROUP BY no SQL)
   - `size: 0`: Otimização para retornar apenas agregações
   - Processamento distribuído no cluster Elasticsearch

2. **Validação de Dados**:
   - Confirma que dados foram indexados corretamente
   - Identifica distribuição de valores
   - Detecta anomalias (ex: estados inválidos)

---

## ⚡ DAG 2: Spark Elasticsearch Pipeline

### Objetivo

Demonstrar **processamento distribuído** com Apache Spark e integração com Elasticsearch para análises complexas e agregações em escala.

### Arquitetura da DAG

```python
process_with_spark_and_index → verify_elasticsearch_indices → create_elasticsearch_visualization
```

### Análise Técnica das Tasks

#### Task 1: `process_with_spark_and_index`

**Propósito**: Processar dados com Spark e indexar agregações no Elasticsearch.

```python
def process_with_spark_and_index():
    # 1. Conectar ao Spark Connect
    spark = SparkSession.builder \
        .appName("SparkElasticsearchIndexer") \
        .remote("sc://spark-connect:15002") \
        .getOrCreate()
    
    # 2. Ler CSV com Spark
    df = spark.read.csv(csv_path, header=True, inferSchema=True)
    
    # 3. Agregações por estado
    state_agg = df.groupBy('State') \
        .agg(
            count('*').alias('total_records'),
            spark_sum('Count').alias('total_count'),
            avg('Count').alias('avg_count')
        ) \
        .orderBy(col('total_count').desc())
    
    # 4. Converter para Pandas
    state_pandas = state_agg.toPandas()
    
    # 5. Indexar no Elasticsearch
    bulk(es, generate_state_docs(), chunk_size=100)
```

**Conceitos-chave**:

### 1. **Spark Connect**

```python
spark_url = 'sc://spark-connect:15002'
spark = SparkSession.builder.remote(spark_url).getOrCreate()
```

**O que é Spark Connect?**
- Protocolo cliente-servidor para Spark (introduzido no Spark 3.4+)
- Separa aplicação cliente do cluster Spark
- Permite execução remota de código Spark

**Vantagens**:
- **Desacoplamento**: Cliente não precisa de JVM completa
- **Escalabilidade**: Múltiplos clientes conectam ao mesmo cluster
- **Segurança**: Isolamento entre cliente e cluster

---

### 2. **Processamento Distribuído**

```python
df = spark.read.csv(csv_path, header=True, inferSchema=True)
```

**Por que Spark?**
- **Paralelização**: Processa dados em múltiplos nós
- **In-Memory**: Mantém dados na memória para operações rápidas
- **Lazy Evaluation**: Otimiza plano de execução antes de executar

**Quando usar Spark vs. Pandas?**

| Critério | Pandas | Spark |
|----------|--------|-------|
| Volume de dados | < 10GB | > 10GB |
| Processamento | Single-node | Distribuído |
| Memória | Limitada à RAM | Escalável |
| Complexidade | Simples | Moderada |

---

### 3. **Agregações Complexas**

```python
state_agg = df.groupBy('State') \
    .agg(
        count('*').alias('total_records'),      # Total de linhas
        spark_sum('Count').alias('total_count'), # Soma de valores
        avg('Count').alias('avg_count')          # Média
    ) \
    .orderBy(col('total_count').desc())
```

**Operações Realizadas**:
1. **groupBy**: Particiona dados por estado (similar a SQL GROUP BY)
2. **agg**: Aplica múltiplas funções de agregação
3. **orderBy**: Ordena resultados (top estados)

**Otimizações do Spark**:
- **Catalyst Optimizer**: Otimiza plano de execução
- **Tungsten**: Gerenciamento eficiente de memória
- **Predicate Pushdown**: Filtra dados na origem

---

### 4. **Integração Spark → Elasticsearch**

```python
# Converter Spark DataFrame → Pandas
state_pandas = state_agg.toPandas()

# Gerar documentos para Elasticsearch
def generate_state_docs():
    for _, row in state_pandas.iterrows():
        yield {
            "_index": "mm_state_aggregations",
            "_source": {
                "state": row['State'],
                "total_records": int(row['total_records']),
                "total_count": int(row['total_count']),
                "avg_count": float(row['avg_count']),
                "processed_at": datetime.now().isoformat()
            }
        }

# Indexar em massa
bulk(es, generate_state_docs(), chunk_size=100)
```

**Fluxo de Dados**:
```
Spark DataFrame → Pandas DataFrame → Python Generator → Elasticsearch Bulk API
```

**Por que converter para Pandas?**
- Elasticsearch Python client trabalha melhor com estruturas Python nativas
- Pandas oferece iteração eficiente sobre linhas
- Volume de agregações é pequeno (< 100 linhas)

**Alternativa para Big Data**:
Para volumes maiores, use `elasticsearch-hadoop` connector:
```python
df.write \
    .format("org.elasticsearch.spark.sql") \
    .option("es.nodes", "elasticsearch") \
    .option("es.port", "9200") \
    .save("mm_state_aggregations")
```

---

#### Task 2: `verify_elasticsearch_indices`

**Propósito**: Validar indexação e exibir amostra de dados.

```python
def verify_elasticsearch_indices():
    indices = ['mm_state_aggregations', 'mm_color_aggregations']
    
    for index in indices:
        count = es.count(index=index)['count']
        
        result = es.search(index=index, body={
            "size": 3,
            "sort": [{"total_count": {"order": "desc"}}]
        })
        
        for hit in result['hits']['hits']:
            print(hit['_source'])
```

**Conceitos-chave**:
- **Validação de Pipeline**: Confirma que dados foram processados corretamente
- **Data Quality**: Verifica integridade dos dados indexados
- **Observabilidade**: Logs estruturados para debugging

---

#### Task 3: `create_elasticsearch_visualization`

**Propósito**: Demonstrar queries analíticas e geração de insights.

```python
def create_elasticsearch_visualization():
    # Top 5 estados
    result = es.search(index='mm_state_aggregations', body={
        "size": 5,
        "sort": [{"total_count": {"order": "desc"}}],
        "query": {"match_all": {}}
    })
    
    # Estatísticas gerais
    state_count = es.count(index='mm_state_aggregations')['count']
    color_count = es.count(index='mm_color_aggregations')['count']
```

**Conceitos-chave**:
- **Analytical Queries**: Queries otimizadas para análise
- **Sorting**: Ordenação eficiente no Elasticsearch
- **Aggregations**: Estatísticas em tempo real

---

## 🧠 Conceitos Fundamentais para Engenheiros de Dados

### 1. **Idempotência em Pipelines**

**Definição**: Uma operação é idempotente se pode ser executada múltiplas vezes sem alterar o resultado além da primeira execução.

**Implementação nas DAGs**:

```python
# ✅ Idempotente
if es.indices.exists(index=index_name):
    es.indices.delete(index=index_name)
es.indices.create(index=index_name)

# ❌ Não idempotente
es.indices.create(index=index_name)  # Falha na segunda execução
```

**Por que é crítico?**
- Permite re-execução segura de DAGs
- Facilita recovery de falhas
- Essencial para ambientes de produção

---

### 2. **Separação de Concerns**

**Princípio**: Cada task deve ter uma responsabilidade única e bem definida.

**Exemplo nas DAGs**:
- ✅ `check_elasticsearch`: Apenas valida conexão
- ✅ `create_index`: Apenas cria índice
- ✅ `index_csv_data`: Apenas indexa dados
- ❌ `do_everything`: Valida, cria, indexa, analisa (anti-pattern)

**Benefícios**:
- Facilita debugging (falha isolada)
- Permite retry granular
- Melhora testabilidade

---

### 3. **Error Handling e Observabilidade**

**Estratégias implementadas**:

```python
# 1. Logging estruturado
print(f"✅ Indexados {success} documentos")
print(f"⚠️ Falhas: {len(failed)}")

# 2. Retries configuráveis
default_args = {
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# 3. Fail-fast
if not es.ping():
    raise Exception("❌ Falha ao conectar no Elasticsearch")
```

**Boas práticas**:
- Use emojis para facilitar scanning de logs
- Retorne métricas quantitativas (contadores, tempos)
- Configure alertas para falhas críticas

---

### 4. **Performance e Escalabilidade**

#### Bulk Operations

```python
# ❌ Lento: 10.000 requisições HTTP
for doc in documents:
    es.index(index='my_index', body=doc)

# ✅ Rápido: 10 requisições HTTP (chunk_size=1000)
bulk(es, generate_docs(), chunk_size=1000)
```

**Impacto**:
- Redução de 99% no tempo de indexação
- Menor carga no cluster Elasticsearch
- Throughput de 10.000+ docs/segundo

#### Memory Management

```python
# ❌ Carrega tudo na memória
with open('large_file.csv') as f:
    data = f.readlines()  # 10GB na RAM

# ✅ Streaming com generator
def read_csv():
    with open('large_file.csv') as f:
        for line in f:
            yield process(line)  # Memória constante
```

---

### 5. **Schema Design no Elasticsearch**

#### Tipos de Dados

| Tipo | Uso | Exemplo |
|------|-----|---------|
| `keyword` | Valores exatos, agregações | Estados, IDs, categorias |
| `text` | Busca full-text | Descrições, comentários |
| `integer` | Números inteiros | Contadores, IDs |
| `float` | Números decimais | Preços, médias |
| `date` | Timestamps | created_at, updated_at |
| `boolean` | Flags | is_active, is_deleted |

#### Exemplo de Mapping Completo

```json
{
  "mappings": {
    "properties": {
      "state": {
        "type": "keyword"
      },
      "description": {
        "type": "text",
        "analyzer": "standard"
      },
      "count": {
        "type": "integer"
      },
      "avg_value": {
        "type": "float"
      },
      "created_at": {
        "type": "date",
        "format": "strict_date_optional_time||epoch_millis"
      },
      "is_active": {
        "type": "boolean"
      }
    }
  }
}
```

---

## 🎯 Padrões e Boas Práticas

### 1. **Configuração via Variáveis de Ambiente**

```python
# ✅ Flexível e seguro
es_host = os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')
spark_url = os.getenv('SPARK_CONNECT_URL', 'sc://spark-connect:15002')

# ❌ Hardcoded
es_host = 'http://elasticsearch:9200'
```

**Vantagens**:
- Diferentes configurações por ambiente (dev, staging, prod)
- Segurança: credenciais não no código
- Facilita deployment

---

### 2. **Dependency Management no Airflow**

```python
# Definir dependências explicitamente
check_es >> create_idx >> index_data >> stats

# Equivalente a:
check_es.set_downstream(create_idx)
create_idx.set_downstream(index_data)
index_data.set_downstream(stats)
```

**Visualização no Airflow UI**:
```
[check_es] → [create_idx] → [index_data] → [stats]
```

---

### 3. **Tagging e Metadata**

```python
with DAG(
    'spark_elasticsearch_pipeline',
    tags=['spark', 'elasticsearch', 'aggregation', 'analytics'],
    description='Pipeline Spark + Elasticsearch para processar e indexar agregações',
) as dag:
    pass
```

**Benefícios**:
- Facilita busca de DAGs no Airflow UI
- Agrupa DAGs relacionadas
- Documenta propósito da DAG

---

### 4. **Validação de Dados**

```python
# Validar antes de processar
if not os.path.exists(csv_path):
    raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")

# Validar após processar
count = es.count(index=index_name)['count']
if count == 0:
    raise ValueError("Nenhum documento foi indexado")
```

---

## 💼 Casos de Uso Reais

### 1. **E-commerce: Análise de Vendas**

**Cenário**: Processar logs de vendas e gerar dashboards em tempo real.

**Pipeline**:
```
Logs (S3) → Spark (agregações) → Elasticsearch → Kibana (visualização)
```

**Agregações**:
- Vendas por região
- Produtos mais vendidos
- Receita por categoria
- Tendências temporais

---

### 2. **Fintech: Detecção de Fraudes**

**Cenário**: Analisar transações e identificar padrões suspeitos.

**Pipeline**:
```
Transações (Kafka) → Spark (ML) → Elasticsearch → Alertas
```

**Features**:
- Agregações por usuário
- Detecção de anomalias
- Scoring de risco
- Busca full-text em histórico

---

### 3. **IoT: Monitoramento de Sensores**

**Cenário**: Processar telemetria de milhões de dispositivos.

**Pipeline**:
```
Sensores (MQTT) → Kafka → Spark → Elasticsearch → Grafana
```

**Métricas**:
- Agregações por dispositivo
- Alertas de threshold
- Análise de séries temporais
- Geolocalização

---

### 4. **Log Analytics**

**Cenário**: Centralizar e analisar logs de aplicações.

**Pipeline**:
```
Apps → Logstash → Elasticsearch → Kibana
```

**Queries**:
- Busca por erros
- Agregações por severidade
- Análise de performance
- Troubleshooting

---

## 📈 Métricas e Monitoramento

### KPIs do Pipeline

```python
# Métricas a monitorar
metrics = {
    'documents_indexed': success_count,
    'indexing_time_seconds': end_time - start_time,
    'throughput_docs_per_second': success_count / (end_time - start_time),
    'error_rate': failed_count / total_count,
    'cluster_health': es.cluster.health()['status']
}
```

### Alertas Recomendados

1. **Pipeline Failures**: DAG falhou > 2 vezes
2. **Performance Degradation**: Throughput < 1000 docs/s
3. **Data Quality**: Error rate > 5%
4. **Cluster Health**: Status = red

---

## 🚀 Otimizações Avançadas

### 1. **Particionamento de Dados**

```python
# Processar dados em partições
df = spark.read.csv(csv_path)
df = df.repartition(10, 'State')  # 10 partições por estado

# Processar cada partição em paralelo
df.groupBy('State').agg(...).write.format('es').save()
```

---

### 2. **Caching no Spark**

```python
# Cache dados frequentemente acessados
df = spark.read.csv(csv_path)
df.cache()  # Mantém na memória

# Múltiplas agregações sem re-ler CSV
state_agg = df.groupBy('State').count()
color_agg = df.groupBy('Color').count()
```

---

### 3. **Índices Otimizados no Elasticsearch**

```json
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "refresh_interval": "30s"
  }
}
```

**Configurações**:
- `shards`: Paralelização (3-5 para clusters pequenos)
- `replicas`: Alta disponibilidade (1-2 réplicas)
- `refresh_interval`: Latência vs. throughput (30s para bulk)

---

## 🎓 Conhecimentos Adquiridos

### Para Iniciantes

1. ✅ Orquestração de workflows com Airflow
2. ✅ Indexação de dados no Elasticsearch
3. ✅ Conceitos de bulk operations
4. ✅ Schema design básico
5. ✅ Error handling e logging

### Para Intermediários

1. ✅ Integração Spark + Elasticsearch
2. ✅ Processamento distribuído
3. ✅ Agregações complexas
4. ✅ Otimização de performance
5. ✅ Padrões de pipeline de dados

### Para Avançados

1. ✅ Arquitetura de sistemas distribuídos
2. ✅ Spark Connect protocol
3. ✅ Tuning de clusters Elasticsearch
4. ✅ Estratégias de particionamento
5. ✅ Observabilidade e monitoramento

---

## 🔮 Próximos Passos

### Evoluções Possíveis

1. **Streaming em Tempo Real**:
   ```python
   # Substituir batch por streaming
   df = spark.readStream.format('kafka').load()
   ```

2. **Machine Learning**:
   ```python
   # Adicionar predições ao pipeline
   model = MLModel.load('model.pkl')
   df = df.withColumn('prediction', model.predict(col('features')))
   ```

3. **Data Quality**:
   ```python
   # Validação com Great Expectations
   from great_expectations.dataset import SparkDFDataset
   ge_df = SparkDFDataset(df)
   ge_df.expect_column_values_to_not_be_null('state')
   ```

4. **Orquestração Avançada**:
   ```python
   # Sensors para aguardar dados
   wait_for_file = FileSensor(
       task_id='wait_for_csv',
       filepath='/data/input.csv'
   )
   ```

---

## 📊 Comparação: Antes vs. Depois

### Sem Pipeline Automatizado

```
❌ Processar dados manualmente
❌ Scripts ad-hoc sem versionamento
❌ Sem retry em falhas
❌ Difícil troubleshooting
❌ Não escalável
```

### Com Pipeline Airflow + Elasticsearch

```
✅ Processamento automatizado e agendado
✅ Código versionado e testável
✅ Retry automático configurável
✅ Logs estruturados e observabilidade
✅ Escalável horizontalmente
✅ Busca e análise em tempo real
✅ Integração com ferramentas de BI
```

---

## 🎯 Conclusão

As DAGs apresentadas demonstram a implementação de pipelines de dados modernos e escaláveis, combinando:

1. **Apache Airflow**: Orquestração robusta com retry, logging e monitoramento
2. **Elasticsearch**: Motor de busca e análise em tempo real
3. **Apache Spark**: Processamento distribuído para grandes volumes

### Principais Aprendizados

- **Idempotência**: Essencial para pipelines confiáveis
- **Separação de Concerns**: Facilita manutenção e debugging
- **Bulk Operations**: Crítico para performance
- **Schema Design**: Impacta diretamente queries e agregações
- **Observabilidade**: Logs estruturados e métricas

### Impacto para Engenheiros de Dados

Este conhecimento permite:
- ✅ Construir pipelines de produção escaláveis
- ✅ Integrar múltiplas tecnologias de Big Data
- ✅ Implementar boas práticas de engenharia
- ✅ Otimizar performance e custos
- ✅ Garantir qualidade e confiabilidade dos dados

### Aplicabilidade

Os padrões demonstrados são aplicáveis a:
- E-commerce (análise de vendas)
- Fintech (detecção de fraudes)
- IoT (telemetria de sensores)
- Log analytics (monitoramento de aplicações)
- Data warehousing (ETL/ELT)

---

## 📚 Referências

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Elasticsearch Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Apache Spark Documentation](https://spark.apache.org/docs/latest/)
- [Spark Connect Protocol](https://spark.apache.org/docs/latest/spark-connect-overview.html)
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/)

---

**Autor**: Data Engineering Team  
**Data**: Janeiro 2025  
**Versão**: 1.0

---

*Este artigo faz parte do projeto Airflow Elastic - Pipeline de Dados Completo*
