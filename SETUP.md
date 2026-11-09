# Infrastructure Setup Guide

This guide explains how to set up the infrastructure required for the Agentic Pipeline.

## Quick Setup (Automated)

The easiest way to set up the infrastructure is to use the automated setup script:

```bash
sudo ./setup-infrastructure.sh
```

This script will:
1. Install MicroK8s
2. Enable required addons (dns, helm3, storage, registry)
3. Enable NVIDIA GPU addon (if GPU available)
4. Configure kubectl
5. Install ArgoCD
6. Configure ArgoCD CLI
7. Create required namespaces

**Estimated time: 10-15 minutes** (mostly waiting for downloads and cluster startup)

## Manual Setup

If you prefer to set up the infrastructure manually, follow these steps:

### 1. Install MicroK8s

```bash
sudo snap install microk8s --classic
microk8s status --wait-ready
```

### 2. Enable MicroK8s Addons

```bash
microk8s enable dns
microk8s enable helm3
microk8s enable storage
microk8s enable registry
```

### 3. Enable GPU Support (Optional)

If you have an NVIDIA GPU:

```bash
microk8s enable nvidia
```

### 4. Configure kubectl

```bash
mkdir -p ~/.kube
microk8s config > ~/.kube/config
chmod 600 ~/.kube/config
```

Also configure for the project workspace:

```bash
mkdir -p /workspaces/AgenticPipeline/.kube
microk8s config > /workspaces/AgenticPipeline/.kube/config
chmod 600 /workspaces/AgenticPipeline/.kube/config
```

### 5. Install ArgoCD

From backup (if available):

```bash
kubectl apply -f cluster-backup.yaml
```

Or from official manifest:

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### 6. Expose ArgoCD Service

```bash
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort"}}'
```

### 7. Install ArgoCD CLI

```bash
VERSION=$(curl -s https://api.github.com/repos/argoproj/argo-cd/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/download/$VERSION/argocd-linux-amd64
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
rm argocd-linux-amd64
```

### 8. Get ArgoCD Credentials

```bash
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
echo "Username: admin"
echo "Password: $ARGOCD_PASSWORD"
```

### 9. Login to ArgoCD

```bash
argocd login <server-ip>:<port> --username admin --password $ARGOCD_PASSWORD --insecure
```

### 10. Create Required Namespaces

```bash
kubectl create namespace model-serving
```

## Verification

After setup, verify everything is working:

```bash
# Check MicroK8s status
microk8s status

# Check cluster nodes
kubectl get nodes

# Check ArgoCD pods
kubectl get pods -n argocd

# Check GPU operator (if enabled)
kubectl get pods -n gpu-operator-resources

# Check namespaces
kubectl get namespaces
```

## Reinstalling Infrastructure

If you need to reinstall the infrastructure (e.g., after removing MicroK8s to save space):

1. **No code changes needed** - Your pipeline code is already in the repo
2. **Just run the setup script** - It will reinstall everything
3. **Configuration preserved** - Your `.env` and settings remain

```bash
sudo ./setup-infrastructure.sh
```

## Troubleshooting

### MicroK8s not starting

```bash
microk8s stop
microk8s start
microk8s status --wait-ready
```

### GPU operator pods not running

```bash
microk8s disable nvidia
microk8s enable nvidia
# Wait 2-3 minutes
kubectl get pods -n gpu-operator-resources
```

### ArgoCD not accessible

Check the service:

```bash
kubectl get svc -n argocd
kubectl describe svc argocd-server -n argocd
```

### kubectl not working

Check kubeconfig:

```bash
kubectl cluster-info
# If failing, reconfigure:
microk8s config > ~/.kube/config
```

## Alternative Kubernetes Distributions

If MicroK8s is not suitable due to storage constraints, consider these alternatives:

- **k3d** - Docker-based, very lightweight (~100MB)
- **minikube** - With minimal driver
- **kind** - Docker-based Kubernetes
- **k3s** - Lightweight Kubernetes

The pipeline code is Kubernetes-compatible and should work with any of these distributions with minimal configuration changes.
