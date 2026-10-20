# ArgoCD Application Examples

This directory contains ArgoCD Application manifests for deploying models using the Helm chart.

## Available Applications

- `phi3-mini-application.yaml` - Microsoft Phi-3-mini-4k-instruct
- `embeddinggemma-application.yaml` - Google EmbeddingGemma-2

## How to Use

### 1. Apply an Application

Apply the ArgoCD Application manifest:

```bash
kubectl apply -f deployment/helm/argocd-examples/phi3-mini-application.yaml
```

### 2. Create a New Application

To deploy a new model:

1. Create a values file for your model in `deployment/helm/values/your-model.yaml`
2. Copy one of the existing application manifests and customize it:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: your-model  # Unique application name
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/shreyasdell/pipelineagent.git
    targetRevision: main
    path: deployment/helm
    helm:
      valueFiles:
        - values/your-model.yaml  # Your values file
  destination:
    server: https://kubernetes.default.svc
    namespace: your-namespace  # Target namespace
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

3. Apply the manifest:

```bash
kubectl apply -f deployment/helm/argocd-examples/your-model-application.yaml
```

### 3. Sync the Application

The application will sync automatically if `automated.syncPolicy` is enabled. To manually sync:

```bash
argocd app sync phi3-mini
```

Or use the ArgoCD UI at https://172.24.52.99:32066

### 4. View Application Status

```bash
argocd app get phi3-mini
```

## Key Configuration

### repoURL
Update this to your fork of the repository:

```yaml
repoURL: https://github.com/your-org/pipelineagent.git
```

### targetRevision
The Git branch to track:

```yaml
targetRevision: main  # or your branch name
```

### valueFiles
The values file to use for this model:

```yaml
helm:
  valueFiles:
    - values/phi3-mini.yaml
```

### destination.namespace
The Kubernetes namespace where the model will be deployed:

```yaml
destination:
  namespace: sglang-serving
```

## Sync Policy Options

- `prune: true` - Automatically delete resources that are removed from the chart
- `selfHeal: true` - Automatically re-sync if the cluster state drifts from Git
- `CreateNamespace=true` - Create the namespace if it doesn't exist

## Troubleshooting

### Application Not Syncing

Check application status:

```bash
argocd app get phi3-mini
```

Check application logs:

```bash
argocd app logs phi3-mini
```

### Sync Failed

Check the ArgoCD UI for detailed error messages, or:

```bash
argocd app sync phi3-mini --debug
```

### Namespace Already Exists

If the namespace already exists and you don't want ArgoCD to manage it, remove `CreateNamespace=true` from syncOptions:

```yaml
syncOptions:
  - ServerSideApply=true
```
