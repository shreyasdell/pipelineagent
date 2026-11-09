#!/bin/bash

# Agentic Pipeline Infrastructure Setup Script
# This script automates MicroK8s installation and configuration for the Agentic Pipeline
# Usage: sudo ./setup-infrastructure.sh

set -e  # Exit on error

echo "=========================================="
echo "Agentic Pipeline Infrastructure Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root (use sudo)"
    exit 1
fi

# Step 1: Install MicroK8s
echo ""
echo "Step 1: Installing MicroK8s..."
if command -v microk8s &> /dev/null; then
    print_warning "MicroK8s already installed, skipping installation"
    microk8s status
else
    print_info "Installing MicroK8s..."
    snap install microk8s --classic
    print_success "MicroK8s installed"
fi

# Step 2: Wait for MicroK8s to be ready
echo ""
echo "Step 2: Waiting for MicroK8s to be ready..."
microk8s status --wait-ready
print_success "MicroK8s is ready"

# Step 3: Enable required addons
echo ""
echo "Step 3: Enabling MicroK8s addons..."
addons=("dns" "helm3" "storage" "registry")
for addon in "${addons[@]}"; do
    print_info "Enabling $addon..."
    microk8s enable $addon
    print_success "$addon enabled"
done

# Step 4: Enable NVIDIA GPU addon (if GPU available)
echo ""
echo "Step 4: Checking for GPU availability..."
if command -v nvidia-smi &> /dev/null; then
    print_info "NVIDIA GPU detected, enabling NVIDIA addon..."
    microk8s enable nvidia
    print_success "NVIDIA addon enabled"
else
    print_warning "No NVIDIA GPU detected, skipping NVIDIA addon"
fi

# Step 5: Configure kubectl
echo ""
echo "Step 5: Configuring kubectl..."
mkdir -p ~/.kube
microk8s config > ~/.kube/config
chmod 600 ~/.kube/config
print_success "kubectl configured"

# Also configure for the project workspace
mkdir -p /workspaces/AgenticPipeline/.kube
microk8s config > /workspaces/AgenticPipeline/.kube/config
chmod 600 /workspaces/AgenticPipeline/.kube/config
print_success "kubectl configured for workspace"

# Step 6: Verify cluster access
echo ""
echo "Step 6: Verifying cluster access..."
if kubectl cluster-info &> /dev/null; then
    print_success "Cluster accessible via kubectl"
else
    print_error "Cluster not accessible via kubectl"
    exit 1
fi

# Step 7: Install ArgoCD
echo ""
echo "Step 7: Installing ArgoCD..."
if [ -f "/workspaces/AgenticPipeline/cluster-backup.yaml" ]; then
    print_info "Installing ArgoCD from cluster-backup.yaml..."
    kubectl apply -f /workspaces/AgenticPipeline/cluster-backup.yaml
    print_success "ArgoCD installed from backup"
else
    print_warning "cluster-backup.yaml not found, installing ArgoCD via manifest..."
    # Create argocd namespace
    kubectl create namespace argocd || true
    
    # Install ArgoCD
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    print_success "ArgoCD installed from official manifest"
fi

# Step 8: Wait for ArgoCD to be ready
echo ""
echo "Step 8: Waiting for ArgoCD to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s || {
    print_warning "ArgoCD pods not ready within timeout, but installation may still be in progress"
}

# Step 9: Expose ArgoCD service
echo ""
echo "Step 9: Exposing ArgoCD service..."
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort"}}' || true
print_success "ArgoCD service exposed as NodePort"

# Step 10: Get ArgoCD credentials
echo ""
echo "Step 10: Getting ArgoCD credentials..."
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
print_success "ArgoCD initial admin password retrieved"
print_info "Username: admin"
print_info "Password: $ARGOCD_PASSWORD"

# Step 11: Install ArgoCD CLI
echo ""
echo "Step 11: Installing ArgoCD CLI..."
if command -v argocd &> /dev/null; then
    print_warning "ArgoCD CLI already installed"
else
    print_info "Downloading ArgoCD CLI..."
    VERSION=$(curl -s https://api.github.com/repos/argoproj/argo-cd/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/download/$VERSION/argocd-linux-amd64
    install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
    rm argocd-linux-amd64
    print_success "ArgoCD CLI installed"
fi

# Step 12: Configure ArgoCD CLI
echo ""
echo "Step 12: Configuring ArgoCD CLI..."
ARGOCD_SERVER=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$ARGOCD_SERVER" ]; then
    ARGOCD_SERVER="172.24.52.99"  # Use known IP if loadBalancer not available
fi
ARGOCD_PORT=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.spec.ports[0].nodePort}')
if [ -z "$ARGOCD_PORT" ]; then
    ARGOCD_PORT="30232"  # Default port
fi

argocd login $ARGOCD_SERVER:$ARGOCD_PORT --username admin --password $ARGOCD_PASSWORD --insecure || {
    print_warning "ArgoCD login failed, you may need to configure manually"
}
print_success "ArgoCD CLI configured"

# Step 13: Verify GPU operator
echo ""
echo "Step 13: Verifying GPU operator..."
if kubectl get pods -n gpu-operator-resources &> /dev/null; then
    print_info "GPU operator namespace exists"
    kubectl get pods -n gpu-operator-resources
    print_success "GPU operator pods listed"
else
    print_warning "GPU operator namespace not found"
fi

# Step 14: Create model-serving namespace
echo ""
echo "Step 14: Creating model-serving namespace..."
kubectl create namespace model-serving || true
print_success "model-serving namespace created"

# Step 15: Final verification
echo ""
echo "=========================================="
echo "Infrastructure Setup Complete!"
echo "=========================================="
echo ""
print_info "MicroK8s Status:"
microk8s status
echo ""
print_info "Cluster Nodes:"
kubectl get nodes
echo ""
print_info "ArgoCD Status:"
kubectl get pods -n argocd
echo ""
print_info "Namespaces:"
kubectl get namespaces
echo ""
print_success "Setup complete! You can now run the Agentic Pipeline."
echo ""
print_info "To access ArgoCD UI:"
echo "  URL: http://$ARGOCD_SERVER:$ARGOCD_PORT"
echo "  Username: admin"
echo "  Password: $ARGOCD_PASSWORD"
echo ""
print_info "To verify GPU:"
echo "  kubectl get pods -n gpu-operator-resources"
echo ""
