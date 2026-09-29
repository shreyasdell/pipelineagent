# Setup Guide for Agentic Pipeline

This guide covers the external service setup required for the Agentic Pipeline system.

## GitHub Setup

The CI Agent uses GitHub to create and manage CI/CD pipelines. Here's what you need to configure:

### 1. GitHub Personal Access Token

Create a GitHub Personal Access Token with the following permissions:

**Required Scopes:**
- `repo` - Full control of private repositories
- `workflow` - Ability to update GitHub Actions workflows
- `admin:org` - If you need to create repositories in organizations

**Steps:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select the required scopes listed above
4. Generate and copy the token

### 2. GitHub Repository

You need a GitHub repository where the CI Agent will:
- Create GitHub Actions workflow files
- Create branches for CI pipeline changes
- Create pull requests for review
- Verify pipeline execution

**Repository Requirements:**
- Can be existing or new
- Should have a `main` branch (or configure your default branch)
- Enable GitHub Actions in repository settings

### 3. Environment Configuration

Add the following to your `.env` file:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPO=your-username/your-repo-name
```

**Format:** `GITHUB_REPO=owner/repository-name`

### 4. What the CI Agent Does with GitHub

Once configured, the CI Agent will:
1. Create a feature branch for CI pipeline changes
2. Add GitHub Actions workflow files (`.github/workflows/*.yaml`)
3. Create a pull request for review
4. Verify workflow execution status
5. Monitor pipeline runs

### 5. GitHub Secrets Configuration

For the CI pipelines to work properly, you'll need to configure these GitHub Secrets in your repository:

**Required Secrets:**
- `DOCKER_REGISTRY_USERNAME` - Container registry username
- `DOCKER_REGISTRY_PASSWORD` - Container registry password/token
- `KUBE_CONFIG` - Kubernetes configuration (base64 encoded)
- `API_ENDPOINT` - API endpoint for deployment

**Optional Secrets:**
- `ARGOCD_URL` - ArgoCD server URL
- `ARGOCD_USERNAME` - ArgoCD username
- `ARGOCD_PASSWORD` - ArgoCD password

### 6. Branch Protection (Recommended)

Set up branch protection rules for your main branch:
- Require pull request reviews before merging
- Require status checks to pass before merging
- Enable automatic deletion of branches after merge

## ArgoCD Setup

The Deployment Pipeline Agent uses ArgoCD for GitOps-based deployment management.

### 1. ArgoCD Installation

If you don't have ArgoCD installed, you can install it on Kubernetes:

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### 2. Initial ArgoCD Setup

**Default Credentials:**
- Username: `admin`
- Password: (auto-generated, retrieve with: `argocd admin initial-password -n argocd`)

**Change the default password:**
```bash
argocd account update-password --account admin --current-password <initial-password> --new-password <new-password>
```

### 3. ArgoCD Configuration

Add the following to your `.env` file:

```bash
# Argo CD Configuration
ARGOCD_URL=https://argocd.your-domain.com
ARGOCD_USERNAME=admin
ARGOCD_PASSWORD=your-secure-password
```

**Important Notes:**
- Use HTTPS for production environments
- For development, you can use `http://localhost:8080` with port-forwarding
- Ensure the ArgoCD URL is accessible from where the agent runs

### 4. Git Repository Integration

ArgoCD needs to connect to your Git repository to sync deployments:

**Steps:**
1. In ArgoCD UI, go to Settings → Repositories
2. Connect your Git repository (GitHub/GitLab)
3. Provide repository URL and authentication (SSH key or token)
4. Test the connection

### 5. Create ArgoCD Project

Create a project in ArgoCD for your model deployments:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: model-serving
  namespace: argocd
spec:
  description: Model serving deployments
  sourceRepos:
  - '*'
  destinations:
  - namespace: model-serving
    server: https://kubernetes.default.svc
  clusterResourceWhitelist:
  - group: '*'
    kind: '*'
```

### 6. What the Deployment Agent Does with ArgoCD

Once configured, the Deployment Pipeline Agent will:
1. Generate Kubernetes manifests for model deployment
2. Create ArgoCD Application manifests
3. Verify deployment status through ArgoCD API
4. Check sync status and health indicators
5. Monitor deployment progress

### 7. ArgoCD Application Structure

The agent will create applications with this structure:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: your-model-name
spec:
  project: model-serving
  source:
    repoURL: https://github.com/your-org/your-repo
    targetRevision: HEAD
    path: deployment/your-model-name
  destination:
    server: https://kubernetes.default.svc
    namespace: model-serving
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### 8. SSL/TLS Configuration

**For Development:**
- The agent currently disables SSL verification (`verify=False`)
- This is acceptable for development environments

**For Production:**
- Use proper SSL certificates
- Update the ArgoCD client to enable SSL verification
- Configure proper CA certificates

## Kubernetes Setup

### 1. Namespace Creation

Create the namespace for model serving:

```bash
kubectl create namespace model-serving
```

### 2. Service Account (Optional)

Create a service account with appropriate permissions:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: model-serving-sa
  namespace: model-serving
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: model-serving-role
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: model-serving-binding
subjects:
- kind: ServiceAccount
  name: model-serving-sa
  namespace: model-serving
roleRef:
  kind: ClusterRole
  name: model-serving-role
  apiGroup: rbac.authorization.k8s.io
```

## Container Registry Setup

### 1. Registry Configuration

Configure your container registry in `.env`:

```bash
# Primary Agent Configuration
DEFAULT_CONTAINER_REGISTRY=docker.io
DEFAULT_ORGANIZATION=your-organization
```

### 2. Registry Authentication

For private registries, configure authentication:

**Docker Hub:**
```bash
docker login
# Add credentials to GitHub Secrets or Kubernetes secrets
```

**GitHub Container Registry:**
```bash
echo "GITHUB_TOKEN" | docker login ghcr.io -u USERNAME --password-stdin
```

**GitLab Container Registry:**
```bash
docker login registry.gitlab.com
```

## Database Setup

### 1. PostgreSQL Installation

The system uses PostgreSQL for state persistence.

**Using Docker:**
```bash
docker run -d \
  --name agentic-pipeline-db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=agentic_pipeline \
  -p 5432:5432 \
  postgres:15
```

**Using Podman:**
```bash
podman run -d \
  --name agentic-pipeline-db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=agentic_pipeline \
  -p 5432:5432 \
  postgres:15
```

### 2. Database Configuration

Update `.env` with database credentials:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/agentic_pipeline
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=agentic_pipeline
```

## Verification Steps

### 1. Test GitHub Connection

```python
from tools.github.github_client import GitHubClient
from core.config.settings import settings

client = GitHubClient()
try:
    repos = client._make_request("GET", "/user/repos")
    print("GitHub connection successful!")
except Exception as e:
    print(f"GitHub connection failed: {e}")
```

### 2. Test ArgoCD Connection

```python
from tools.argocd.argocd_client import ArgoCDClient
from core.config.settings import settings

client = ArgoCDClient()
try:
    apps = client.list_applications()
    print(f"ArgoCD connection successful! Found {len(apps)} applications")
except Exception as e:
    print(f"ArgoCD connection failed: {e}")
```

### 3. Test Database Connection

```python
from sqlalchemy import create_engine
from core.config.settings import settings

try:
    engine = create_engine(settings.database_url)
    connection = engine.connect()
    print("Database connection successful!")
    connection.close()
except Exception as e:
    print(f"Database connection failed: {e}")
```

## Troubleshooting

### GitHub Issues

**Problem:** "GitHub token not provided"
- **Solution:** Add `GITHUB_TOKEN` to your `.env` file

**Problem:** "Repository not configured"
- **Solution:** Add `GITHUB_REPO=owner/repo` to your `.env` file

**Problem:** "Authentication failed"
- **Solution:** Verify your GitHub token has the required scopes

### ArgoCD Issues

**Problem:** "ArgoCD URL not configured"
- **Solution:** Add `ARGOCD_URL` to your `.env` file

**Problem:** "Authentication failed"
- **Solution:** Verify ArgoCD username and password are correct

**Problem:** "SSL verification error"
- **Solution:** For development, the agent disables SSL verification. For production, configure proper SSL certificates.

### Database Issues

**Problem:** "Database connection failed"
- **Solution:** Ensure PostgreSQL is running and accessible at the configured URL

**Problem:** "Table does not exist"
- **Solution:** The application creates tables automatically on first run. If this fails, check database permissions.

## Security Best Practices

1. **Never commit `.env` file** to version control
2. **Use strong passwords** for all services
3. **Rotate access tokens** regularly
4. **Use read-only tokens** where possible
5. **Enable audit logging** on all services
6. **Use separate environments** (dev, staging, production)
7. **Implement proper RBAC** in Kubernetes
8. **Use secrets management** (AWS Secrets Manager, HashiCorp Vault, etc.)

## Next Steps

1. Configure GitHub access token and repository
2. Set up ArgoCD on your Kubernetes cluster
3. Configure PostgreSQL database
4. Update your `.env` file with all credentials
5. Run the verification steps above
6. Test with a sample model deployment

For questions or issues, refer to the main README.md or create an issue in the repository.