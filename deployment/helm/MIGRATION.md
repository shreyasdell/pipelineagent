# Migration Guide: From Static Manifests to Helm

This guide explains how to migrate from static Kubernetes manifests to the new Helm-based deployment model.

## Overview

Previously, each model required a separate folder with static manifests:
```
deployment/manifests/
├── microsoft-Phi-3-mini-4k-instruct/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── pvc.yaml
│   ├── configmap.yaml
│   └── namespace.yaml
└── google-embeddinggemma-2/
    ├── deployment.yaml
    ├── service.yaml
    ├── pvc.yaml
    ├── configmap.yaml
    └── namespace.yaml
```

Now, a single Helm chart with values files handles all models:
```
deployment/helm/
├── Chart.yaml
├── values.yaml
├── values/
│   ├── phi3-mini.yaml
│   ├── embeddinggemma.yaml
│   └── sample-model.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── pvc.yaml
│   ├── configmap.yaml
│   └── namespace.yaml
└── argocd-examples/
    ├── phi3-mini-application.yaml
    ├── embeddinggemma-application.yaml
    └── README.md
```

## Benefits

1. **Single Source of Truth**: One Helm chart for all models
2. **Parameterization**: Change model configuration via values files
3. **Easier Maintenance**: Update templates once, apply to all models
4. **ArgoCD Integration**: Native Helm support in ArgoCD
5. **Validation**: Helm template validation before deployment
6. **Reusability**: Add new models by creating a values file

## Migration Steps

### Step 1: Verify Helm Chart

Render templates for your existing models to ensure they match:

```bash
# Render Phi-3-mini
helm template phi3-mini deployment/helm \
  -f deployment/helm/values/phi3-mini.yaml \
  > /tmp/phi3-mini-rendered.yaml

# Render EmbeddingGemma
helm template embeddinggemma deployment/helm \
  -f deployment/helm/values/embeddinggemma.yaml \
  > /tmp/embeddinggemma-rendered.yaml
```

Compare with existing manifests:
```bash
diff deployment/manifests/microsoft-Phi-3-mini-4k-instruct/deployment.yaml \
  <(awk '/^apiVersion: apps/,/^---$/' /tmp/phi3-mini-rendered.yaml)
```

### Step 2: Deploy with Helm (Local Testing)

Deploy a model using Helm to test locally:

```bash
helm install phi3-mini deployment/helm \
  -f deployment/helm/values/phi3-mini.yaml \
  --namespace sglang-serving \
  --create-namespace
```

Verify the deployment:
```bash
kubectl get deployment -n sglang-serving
kubectl get pods -n sglang-serving
kubectl get svc -n sglang-serving
```

### Step 3: Update ArgoCD Applications

Replace static manifest-based ArgoCD applications with Helm-based ones:

**Old (Static Manifests):**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: phi3-mini
spec:
  source:
    repoURL: https://github.com/shreyasdell/pipelineagent.git
    path: deployment/manifests/microsoft-Phi-3-mini-4k-instruct
```

**New (Helm Chart):**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: phi3-mini
spec:
  source:
    repoURL: https://github.com/shreyasdell/pipelineagent.git
    path: deployment/helm
    helm:
      valueFiles:
        - values/phi3-mini.yaml
```

Apply the new ArgoCD application:
```bash
kubectl apply -f deployment/helm/argocd-examples/phi3-mini-application.yaml
```

### Step 4: Remove Old Deployments

Once the Helm-based deployment is verified and working:

```bash
# Delete old static manifest-based deployment
kubectl delete deployment phi-3-mini-4k-instruct -n sglang-serving
kubectl delete service phi-3-mini-4k-instruct-service -n sglang-serving
kubectl delete pvc phi-3-mini-4k-instruct-models-pvc -n sglang-serving
kubectl delete configmap phi-3-mini-4k-instruct-config -n sglang-serving
# Note: Don't delete namespace if other resources exist

# Or use Helm to uninstall
helm uninstall phi3-mini -n sglang-serving
```

### Step 5: Clean Up Old Manifests (Optional)

After successful migration, you can remove the old static manifests:

```bash
# Backup first
cp -r deployment/manifests deployment/manifests.backup

# Remove old manifests
rm -rf deployment/manifests/microsoft-Phi-3-mini-4k-instruct
rm -rf deployment/manifests/google-embeddinggemma-2
```

## Adding a New Model

### Old Way (Static Manifests)

1. Create a new folder: `deployment/manifests/your-model/`
2. Copy and edit 5 YAML files
3. Update resource names, labels, and configurations
4. Commit and push to GitHub
5. Create ArgoCD application pointing to the folder

### New Way (Helm)

1. Create a values file:
```bash
cp deployment/helm/values/sample-model.yaml deployment/helm/values/your-model.yaml
```

2. Edit the values file with your model configuration:
```yaml
model:
  id: "your-org/your-model"
  name: "your-model"
  storagePath: "/models/your-model"

deployment:
  name: "your-model"
  replicas: 1

# ... customize other values
```

3. Deploy:
```bash
helm install your-model deployment/helm \
  -f deployment/helm/values/your-model.yaml \
  --namespace model-serving \
  --create-namespace
```

Or create an ArgoCD application:
```bash
cp deployment/helm/argocd-examples/phi3-mini-application.yaml \
   deployment/helm/argocd-examples/your-model-application.yaml
```

Edit the application to use your values file and apply it.

## Validation Checklist

- [ ] Helm templates render successfully
- [ ] Rendered manifests match existing deployments (except formatting)
- [ ] Helm deployment works locally
- [ ] Pods start successfully
- [ ] Service is accessible
- [ ] ArgoCD application syncs correctly
- [ ] Health checks pass
- [ ] Model is accessible via service endpoint

## Rollback Plan

If you need to rollback to static manifests:

1. Uninstall Helm release:
```bash
helm uninstall your-model -n your-namespace
```

2. Restore static manifests from backup:
```bash
cp -r deployment/manifests.backup deployment/manifests
```

3. Apply static manifests:
```bash
kubectl apply -f deployment/manifests/your-model/
```

4. Update ArgoCD application to point to static manifest path

## Troubleshooting

### Helm Template Validation Error

If `helm template` fails:
```bash
helm template your-model deployment/helm \
  -f deployment/helm/values/your-model.yaml \
  --debug
```

### ArgoCD Sync Fails

Check ArgoCD application logs:
```bash
argocd app get your-model
argocd app logs your-model
```

Ensure the Helm chart path is correct in the ArgoCD application.

### Resource Name Conflicts

If you have both static and Helm deployments, they may conflict. Uninstall one before deploying the other:
```bash
# Uninstall static deployment
kubectl delete -f deployment/manifests/your-model/

# Or uninstall Helm release
helm uninstall your-model -n your-namespace
```

## Summary

The Helm-based deployment model provides:
- ✅ Single reusable chart for all models
- ✅ Parameterized configuration via values files
- ✅ Easier maintenance and updates
- ✅ Native ArgoCD integration
- ✅ Faster model onboarding

The migration is straightforward and can be done incrementally, one model at a time.
