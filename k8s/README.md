# 🚀 Deploy Kubernetes - Airflow Elastic

Estrutura Kubernetes para deploy em nuvem (AWS EKS, GCP GKE, Azure AKS).

## 📁 Estrutura

```
k8s/
├── base/                          # Configurações base
│   ├── namespace.yaml             # Namespace airflow-elastic
│   ├── configmap.yaml             # Variáveis de ambiente
│   ├── secret.yaml                # Credenciais sensíveis
│   ├── pvc.yaml                   # Persistent Volume Claims
│   ├── postgres.yaml              # PostgreSQL (metastore)
│   ├── redis.yaml                 # Redis (message broker)
│   ├── elasticsearch.yaml         # Elasticsearch (busca/análise)
│   ├── kafka.yaml                 # Kafka + Zookeeper (streaming)
│   ├── minio.yaml                 # MinIO (object storage)
│   ├── spark.yaml                 # Spark Connect (processamento)
│   ├── airflow-webserver.yaml     # Airflow UI
│   ├── airflow-scheduler.yaml     # Airflow Scheduler
│   ├── airflow-worker.yaml        # Airflow Workers (Celery)
│   ├── hpa.yaml                   # HorizontalPodAutoscaler
│   ├── ingress.yaml               # Ingress (HTTPS)
│   └── kustomization.yaml         # Kustomize base
│
└── overlays/
    ├── dev/                       # Ambiente de desenvolvimento
    │   ├── kustomization.yaml
    │   └── replica-patch.yaml     # 1 worker, 1 ES node
    │
    └── prod/                      # Ambiente de produção
        ├── kustomization.yaml
        ├── replica-patch.yaml     # 5 workers, 3 ES nodes
        └── resources-patch.yaml   # Recursos aumentados
```

## 🔧 Pré-requisitos

### 1. Ferramentas

```bash
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# kustomize
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash

# helm (opcional)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### 2. Cluster Kubernetes

#### AWS EKS

```bash
# Criar cluster
eksctl create cluster \
  --name airflow-elastic \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.xlarge \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed

# Configurar kubectl
aws eks update-kubeconfig --region us-east-1 --name airflow-elastic
```

#### GCP GKE

```bash
# Criar cluster
gcloud container clusters create airflow-elastic \
  --zone us-central1-a \
  --machine-type n1-standard-4 \
  --num-nodes 3 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 10

# Configurar kubectl
gcloud container clusters get-credentials airflow-elastic --zone us-central1-a
```

#### Azure AKS

```bash
# Criar cluster
az aks create \
  --resource-group airflow-rg \
  --name airflow-elastic \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 10

# Configurar kubectl
az aks get-credentials --resource-group airflow-rg --name airflow-elastic
```

## 🚀 Deploy

### Desenvolvimento

```bash
# Aplicar configurações
kubectl apply -k k8s/overlays/dev/

# Verificar status
kubectl get pods -n airflow-elastic

# Acompanhar logs
kubectl logs -f deployment/airflow-webserver -n airflow-elastic
```

### Produção

```bash
# 1. Atualizar secrets (IMPORTANTE!)
kubectl create secret generic airflow-secrets \
  --from-literal=MINIO_ACCESS_KEY=<seu-access-key> \
  --from-literal=MINIO_SECRET_KEY=<seu-secret-key> \
  --from-literal=AIRFLOW_WWW_USER_PASSWORD=<senha-forte> \
  --from-literal=POSTGRES_PASSWORD=<senha-forte> \
  -n airflow-elastic \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Atualizar domínios no ingress.yaml
# Editar: airflow.example.com → seu-dominio.com

# 3. Aplicar configurações
kubectl apply -k k8s/overlays/prod/

# 4. Verificar status
kubectl get all -n airflow-elastic
```

## 🔍 Verificação

### Verificar Pods

```bash
kubectl get pods -n airflow-elastic -w
```

Todos os pods devem estar `Running`:
- postgres-xxx
- redis-xxx
- elasticsearch-xxx
- kafka-xxx
- zookeeper-xxx
- minio-xxx
- spark-connect-xxx
- airflow-webserver-xxx
- airflow-scheduler-xxx
- airflow-worker-xxx (2-5 réplicas)

### Verificar Services

```bash
kubectl get svc -n airflow-elastic
```

### Verificar Ingress

```bash
kubectl get ingress -n airflow-elastic
```

### Acessar Logs

```bash
# Airflow Webserver
kubectl logs -f deployment/airflow-webserver -n airflow-elastic

# Airflow Scheduler
kubectl logs -f deployment/airflow-scheduler -n airflow-elastic

# Airflow Worker
kubectl logs -f deployment/airflow-worker -n airflow-elastic

# Elasticsearch
kubectl logs -f statefulset/elasticsearch -n airflow-elastic
```

## 🌐 Acesso aos Serviços

### Via Port-Forward (Desenvolvimento)

```bash
# Airflow UI
kubectl port-forward svc/airflow-webserver-service 8080:8080 -n airflow-elastic
# Acesse: http://localhost:8080

# MinIO Console
kubectl port-forward svc/minio-service 9001:9001 -n airflow-elastic
# Acesse: http://localhost:9001

# Elasticsearch
kubectl port-forward svc/elasticsearch-service 9200:9200 -n airflow-elastic
# Acesse: http://localhost:9200
```

### Via LoadBalancer (Produção)

```bash
# Obter IP externo
kubectl get svc airflow-webserver-service -n airflow-elastic

# Configurar DNS
# A record: airflow.example.com → EXTERNAL-IP
```

### Via Ingress (Produção com HTTPS)

```bash
# Instalar cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Criar ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: seu-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Acesse: https://airflow.example.com
```

## 📊 Monitoramento

### Métricas de Recursos

```bash
# CPU e Memória por pod
kubectl top pods -n airflow-elastic

# CPU e Memória por node
kubectl top nodes
```

### HPA Status

```bash
# Verificar autoscaling
kubectl get hpa -n airflow-elastic

# Detalhes do HPA
kubectl describe hpa airflow-worker-hpa -n airflow-elastic
```

### Events

```bash
# Eventos do namespace
kubectl get events -n airflow-elastic --sort-by='.lastTimestamp'
```

## 🔧 Troubleshooting

### Pod não inicia

```bash
# Descrever pod
kubectl describe pod <pod-name> -n airflow-elastic

# Verificar logs
kubectl logs <pod-name> -n airflow-elastic

# Logs do container anterior (se crashou)
kubectl logs <pod-name> -n airflow-elastic --previous
```

### PVC não monta

```bash
# Verificar PVC
kubectl get pvc -n airflow-elastic

# Descrever PVC
kubectl describe pvc postgres-pvc -n airflow-elastic

# Verificar StorageClass
kubectl get storageclass
```

### Service não responde

```bash
# Testar conectividade interna
kubectl run -it --rm debug --image=busybox --restart=Never -n airflow-elastic -- sh
# Dentro do pod:
wget -O- http://elasticsearch-service:9200
```

### Reiniciar Deployment

```bash
kubectl rollout restart deployment/airflow-webserver -n airflow-elastic
kubectl rollout restart deployment/airflow-scheduler -n airflow-elastic
kubectl rollout restart deployment/airflow-worker -n airflow-elastic
```

## 🗑️ Limpeza

### Remover aplicação

```bash
# Desenvolvimento
kubectl delete -k k8s/overlays/dev/

# Produção
kubectl delete -k k8s/overlays/prod/

# Remover namespace (remove tudo)
kubectl delete namespace airflow-elastic
```

### Remover cluster

```bash
# AWS EKS
eksctl delete cluster --name airflow-elastic --region us-east-1

# GCP GKE
gcloud container clusters delete airflow-elastic --zone us-central1-a

# Azure AKS
az aks delete --resource-group airflow-rg --name airflow-elastic
```

## 📈 Recursos por Ambiente

### Desenvolvimento

| Componente | Réplicas | CPU | Memória |
|------------|----------|-----|---------|
| Airflow Worker | 1 | 1 core | 2Gi |
| Elasticsearch | 1 | 1 core | 4Gi |
| Kafka | 1 | 500m | 1Gi |
| Total | - | ~6 cores | ~16Gi |

**Custo estimado**: $150-300/mês

### Produção

| Componente | Réplicas | CPU | Memória |
|------------|----------|-----|---------|
| Airflow Worker | 5 | 2 cores | 4Gi |
| Elasticsearch | 3 | 2 cores | 8Gi |
| Kafka | 3 | 1 core | 2Gi |
| Total | - | ~30 cores | ~80Gi |

**Custo estimado**: $800-1500/mês

## 🔐 Segurança

### Boas Práticas

1. **Secrets**: Use AWS Secrets Manager, GCP Secret Manager ou Azure Key Vault
2. **RBAC**: Configure roles e service accounts
3. **Network Policies**: Isole comunicação entre pods
4. **Pod Security**: Use SecurityContext e PodSecurityPolicy
5. **TLS**: Habilite HTTPS em todos os serviços

### Exemplo: Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: airflow-network-policy
  namespace: airflow-elastic
spec:
  podSelector:
    matchLabels:
      app: airflow-webserver
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 8080
```

## 📚 Referências

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize](https://kustomize.io/)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [GKE Best Practices](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [Azure AKS Best Practices](https://learn.microsoft.com/en-us/azure/aks/best-practices)

---

**Autor**: Data Engineering Team  
**Versão**: 1.0  
**Data**: Janeiro 2025
