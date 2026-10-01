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
2. ARGOCD CONFIGURATION - Manual Setup (SSH Keys for HTTPS Issues)
================================================================================

Due to SSL certificate issues in the WSL environment, use SSH instead of HTTPS.

Option A: Use ArgoCD Web UI with SSH Keys (Recommended)

Step 1: Access ArgoCD UI
- Port-forward ArgoCD server:
  kubectl port-forward -n argocd svc/argocd-server 8080:443

Step 2: Open browser
- Navigate to: http://localhost:8080
- Login with username: admin
- Password: Bait9DThT0lO8AvY

Step 3: Add Repository via SSH with Private Key
- Click "Settings" → "Repositories"
- Click "Connect Repo"
- Select "Via SSH"
- Repository URL: git@github.com:shreyasdell/pipelineagent.git
- Click "Connect"
- Click "SSH Private Key"
- Paste your SSH private key content (from ~/.ssh/id_rsa)
- Click "Connect"

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

Option B: Get SSH Private Key (if you don't have one)

On your host machine (Windows WSL):

Step 1: Generate SSH key (if you don't have one)
```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

Step 2: Copy private key
```bash
cat ~/.ssh/id_rsa
```

Step 3: Add public key to GitHub
- Go to: https://github.com/settings/keys
- Click "New SSH key"
- Paste content of: cat ~/.ssh/id_rsa.pub
- Click "Add SSH key"

Option C: Configure via kubectl with SSH

kubectl create secret generic argocd-ssh-key \\
  --from-file=ssh-privatekey=/path/to/your/private/key \\
  -n argocd

Option D: Alternative - Use HTTPS with Insecure SSL (Development Only)

If SSH is too complex, you can use HTTPS with insecure SSL:

Step 1: In ArgoCD UI, click "Settings" → "Repositories"
Step 2: Click "Connect Repo" → "Via HTTPS"
Step 3: Repository URL: https://github.com/shreyasdell/pipelineagent.git
Step 4: Click "Connect"
Step 5: When prompted about SSL, click "Skip" or "Insecure"
Step 6: This will bypass SSL verification (development only!)

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
3. Configure ArgoCD via Web UI with SSH keys (recommended)
4. Create deployment/manifests/ directory
5. Test with nginx deployment

================================================================================
""")
