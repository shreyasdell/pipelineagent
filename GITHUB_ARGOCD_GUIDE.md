"""
Guide for GitHub Token and ArgoCD Configuration
"""

print("""
================================================================================
GitHub Token and ArgoCD Configuration Guide
================================================================================

1. GITHUB TOKEN - Where to get it
================================================================================

Step 1: Go to GitHub Settings
- Navigate to: https://github.com/settings/tokens
- Click "Generate new token" (classic)
- Or "Generate new token" (fine-grained)

Step 2: Configure Token
- Note: "classic" is easier for this use case
- Name: "AgenticPipeline GitOps"
- Expiration: 90 days (or no expiration for development)
- Scopes: Check "repo" (full control of private repositories)
- Click "Generate token"
- Copy the token (starts with "ghp_")

Step 3: Add to .env
Add to /workspaces/AgenticPipeline/.env:
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO=shreyasdell/pipelineagent

================================================================================
2. ARGOCD CONFIGURATION - Manual Setup (SSH for SSL Issues)
================================================================================

Due to SSL certificate issues in the WSL environment, use SSH instead of HTTPS.

Option A: Use ArgoCD Web UI with SSH (Recommended)

Step 1: Access ArgoCD UI
- Port-forward ArgoCD server:
  kubectl port-forward -n argocd svc/argocd-server 8080:443

Step 2: Open browser
- Navigate to: http://localhost:8080
- Login with username: admin
- Password: Bait9DThT0lO8AvY

Step 3: Add Repository via SSH
- Click "Settings" → "Repositories"
- Click "Connect Repo"
- Select "Via SSH"
- Repository URL: git@github.com:shreyasdell/pipelineagent.git
- Click "Connect"
- If prompted for SSH key, skip for now (use default)

Step 4: Create Application
- Click "New App"
- Application Name: agentic-pipeline-gitops
- Project: default
- Sync Policy: Automatic
- Repository URL: git@github.com:shreyasdell/pipelineagent.git
- Revision: HEAD
- Path: deployment/manifests
- Destination: https://kubernetes.default.svc
- Namespace: model-serving
- Click "Create"

Option B: Configure SSH Keys in ArgoCD (If SSH fails)

If SSH connection fails, you may need to add your SSH key to ArgoCD:

Step 1: Get your SSH public key
- On your host machine: cat ~/.ssh/id_rsa.pub

Step 2: Add SSH key to ArgoCD
- In ArgoCD UI: Settings → Repositories
- Click "Connect Repo" → "Via SSH"
- Click "SSH Private Key"
- Paste your private key content
- Click "Connect"

Option C: Configure via kubectl with SSH

kubectl create secret generic argocd-ssh-key \
  --from-file=ssh-privatekey=/path/to/your/private/key \
  -n argocd

================================================================================
3. DIRECTORY STRUCTURE
================================================================================

Your repository should have this structure:

pipelineagent/
├── agents/              # Source code
├── core/                # Source code
├── tools/               # Source code
├── tests/               # Source code
├── deployment/          # GitOps manifests (create this directory)
│   └── manifests/      # ArgoCD watches this
│       └── {model_id}/
│           ├── deployment.yaml
│           ├── service.yaml
│           └── configmap.yaml

================================================================================
4. NEXT STEPS
================================================================================

1. Get GitHub token from: https://github.com/settings/tokens
2. Add to .env:
   GITHUB_TOKEN=ghp_your_token_here
   GITHUB_REPO=shreyasdell/pipelineagent
3. Configure ArgoCD via Web UI (recommended)
4. Create deployment/manifests/ directory
5. Test with nginx deployment

================================================================================
""")