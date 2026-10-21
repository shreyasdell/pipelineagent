# SGLang Model Serving Helm Chart

A reusable Helm chart for deploying HuggingFace models with SGLang on Kubernetes with GPU support.

## Chart Structure

```
deployment/helm/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default values
├── values/                 # Model-specific values files
│   ├── phi3-mini.yaml      # Microsoft Phi-3-mini-4k-instruct
│   ├── embeddinggemma.yaml # Google EmbeddingGemma-2
│   └── sample-model.yaml   # Template for new models
├── templates/              # Kubernetes resource templates
│   ├── deployment.yaml     # Deployment with GPU support
│   ├── service.yaml        # ClusterIP service
│   ├── pvc.yaml            # Persistent volume claim for model storage
│   ├── configmap.yaml      # Configuration for model ID, path, port
│   └── namespace.yaml      # Namespace (optional)
└── README.md               # This file
```

## Prerequisites

- Kubernetes cluster with GPU support (NVIDIA)
- Helm 3.x installed
- kubectl configured for your cluster
- Sufficient GPU resources available

## Quick Start

### 1. Deploy an Existing Model

Deploy Phi-3-mini-4k-instruct:

```bash
helm install phi3-mini deployment/helm \
  -f deployment/helm/values/phi3-mini.yaml \
  --namespace sglang-serving \
  --create-namespace
```

Deploy EmbeddingGemma-2:

```bash
helm install embeddinggemma deployment/helm \
  -f deployment/helm/values/embeddinggemma.yaml \
  --namespace sglang-deploy \
  --create-namespace
```

### 2. Add a New Model

1. Copy the sample values file:

```bash
cp deployment/helm/values/sample-model.yaml deployment/helm/values/your-model.yaml
```

2. Edit the values file with your model configuration:

```yaml
model:
  id: "your-org/your-model-name"  # HuggingFace model ID
  name: "your-model-name"         # Kubernetes resource name
  storagePath: "/models/your-model"

deployment:
  name: "your-model-name"
  replicas: 1

# ... customize other values as needed
```

3. Deploy your model:

```bash
helm install your-model deployment/helm \
  -f deployment/helm/values/your-model.yaml \
  --namespace model-serving \
  --create-namespace
```

### 3. Render Templates (Dry Run)

To see what manifests will be generated without deploying:

```bash
helm template model-serving deployment/helm \
  -f deployment/helm/values/phi3-mini.yaml
```

### 4. Upgrade a Deployment

To update an existing deployment:

```bash
helm upgrade phi3-mini deployment/helm \
  -f deployment/helm/values/phi3-mini.yaml
```

### 5. Uninstall a Deployment

```bash
helm uninstall phi3-mini --namespace sglang-serving
```

## Configuration

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `model.id` | HuggingFace model ID (used in ConfigMap/env vars) | `microsoft/Phi-3-mini-4k-instruct` |
| `model.name` | Kubernetes resource name | `phi-3-mini-4k-instruct` |
| `model.storagePath` | Model storage path in PVC | `/models/phi3-mini` |
| `deployment.replicas` | Number of replicas | `1` |
| `deployment.runtimeClass` | Kubernetes runtime class | `nvidia` |
| `container.image` | SGLang container image | `lmsysorg/sglang:latest` |
| `container.port` | Container port | `8000` |

### Label Sanitization

Kubernetes labels have strict naming requirements (RFC 1123):
- Must be 63 characters or less
- Must consist of alphanumeric characters, `-`, or `.`
- Must start and end with alphanumeric characters

The Helm chart automatically sanitizes the `model.id` when used in Kubernetes labels:
- Converts to lowercase
- Replaces `/`, `_`, and `.` with `-`
- Removes invalid characters
- Limits to 63 characters

**Example:**
- Original model ID: `microsoft/Phi-3-mini-4k-instruct`
- Label value: `microsoft-phi-3-mini-4k-instruct`

The original model ID is preserved in ConfigMap data and environment variables for use by the application.

| `resources.requests.cpu` | CPU request | `4` |
| `resources.requests.memory` | Memory request | `16Gi` |
| `resources.requests.nvidia.com/gpu` | GPU request | `1` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `8000` |
| `pvc.size` | PVC storage size | `50Gi` |
| `namespace.name` | Namespace name | `sglang-serving` |
| `namespace.create` | Create namespace if not exists | `true` |

### Customizing Resources

Adjust CPU, memory, and GPU resources based on your model requirements:

```yaml
resources:
  requests:
    cpu: 8              # Increase for larger models
    memory: 32Gi        # Increase for larger models
    nvidia.com/gpu: 2   # Multiple GPUs for large models
  limits:
    nvidia.com/gpu: 2
```

### Customizing Health Checks

Adjust health check timing based on model startup time:

```yaml
healthCheck:
  livenessProbe:
    path: /health
    initialDelaySeconds: 120  # Increase for slow-loading models
    periodSeconds: 30
  readinessProbe:
    path: /health
    initialDelaySeconds: 60
    periodSeconds: 10
```

### Adding Environment Variables

Add custom environment variables:

```yaml
env:
  - name: NVIDIA_VISIBLE_DEVICES
    value: "all"
  - name: CUSTOM_ENV_VAR
    value: "custom-value"
```

## ArgoCD Integration

This Helm chart is designed to work seamlessly with ArgoCD. See `deployment/helm/argocd-examples/` for ArgoCD Application manifests.

### ArgoCD Application Example

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: phi3-mini
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/pipelineagent.git
    targetRevision: main
    path: deployment/helm
    helm:
      valueFiles:
        - values/phi3-mini.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: sglang-serving
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

## Migration from Static Manifests

If you have existing static manifests in `deployment/manifests/`, you can migrate them to Helm:

1. Compare your existing manifests with the Helm templates
2. Create a values file that matches your existing configuration
3. Validate by rendering templates:

```bash
helm template model-serving deployment/helm \
  -f deployment/helm/values/your-model.yaml > rendered-manifests.yaml
```

4. Compare with your existing manifests:

```bash
diff deployment/manifests/your-model/deployment.yaml rendered-manifests.yaml
```

5. Once validated, deploy with Helm and remove the static manifests

## Troubleshooting

### Pod Not Starting

Check pod logs:

```bash
kubectl logs -n sglang-serving deployment/phi-3-mini-4k-instruct
```

Check pod events:

```bash
kubectl describe pod -n sglang-serving -l app=phi-3-mini-4k-instruct
```

### GPU Not Available

Check GPU nodes:

```bash
kubectl get nodes -o json | jq '.items[].status.allocatable'
```

Check nvidia-device-plugin:

```bash
kubectl get pods -n kube-system | grep nvidia
```

### Model Download Failing

Ensure HuggingFace token is configured if using private models:

```yaml
env:
  - name: HF_TOKEN
    valueFrom:
      secretKeyRef:
        name: huggingface-secret
        key: token
```

## Best Practices

1. **Use separate namespaces** for different models to isolate resources
2. **Set appropriate resource limits** to prevent resource exhaustion
3. **Monitor GPU utilization** using DCGM-exporter and Prometheus
4. **Use persistent volumes** for model storage to avoid re-downloading
5. **Configure health checks** based on model startup time
6. **Use ArgoCD for GitOps** to manage deployments declaratively

## Support

For issues or questions:
- Check the main project documentation
- Review ArgoCD examples in `deployment/helm/argocd-examples/`
- Validate your values files by rendering templates before deploying
