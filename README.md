# Agentic Pipeline

Agentic AI system for automated model deployment and inferencing using LangChain + LangGraph.

## Phase 1 Architecture

This system uses a multi-agent architecture with LangGraph as the orchestrator and LangChain for LLM integration:

- **LangGraph**: Manages agent coordination and state management
- **LangChain**: Handles LLM calls and tool integration
- **PostgreSQL**: Persistent state storage (optional)
- **MicroK8s**: Kubernetes cluster for deployment
- **GitHub**: CI/CD and GitOps repository
- **Hugging Face**: Model repository and registry
- **vLLM**: High-performance inference serving engine
- **ArgoCD**: GitOps deployment orchestration (when configured)

### Phase 1 Deployment Flow (GitOps)

```
User Request
      ↓
Primary Agent (LangGraph orchestrator)
      ↓
Constraint Resolver Agent (feasibility analysis)
      ↓
Deployment Pipeline Agent (Hugging Face + vLLM config)
      ↓
CI Agent (GitHub Actions)
      ↓
Kubernetes Deployment Agent (manifest generation)
      ↓
GitHub (commit manifests)
      ↓
ArgoCD (create application)
      ↓
ArgoCD (sync to cluster)
      ↓
MicroK8s (apply manifests)
      ↓
vLLM (GPU inference serving)
      ↓
Inference Endpoint
```

### Agent "Brain" Architecture (LLM for Agent Reasoning)

All agents use a local Ollama model as their "agent brain":

```
All Agents (Primary, Constraint Resolver, CI, Deployment Pipeline, Kubernetes)
    ↓
LangChain
    ↓
ChatOllama
    ↓
Ollama Server (http://10.88.0.1:11434)
    ↓
qwen2.5:7b Model
```

**Important**: This is separate from the deployed model being served.

### Deployed Model Architecture (Model Being Deployed)

The model being deployed comes from Hugging Face and is served by vLLM:

```
Hugging Face Hub
    ↓
Model Download
    ↓
vLLM Serving Engine
    ↓
MicroK8s Pod
    ↓
Inference Service
    ↓
Inference Endpoint
```

### Agent Capabilities (Phase 1)

**Primary Agent**
- Orchestrates end-to-end model deployment pipelines using LangGraph
- Generates deployment conversation IDs for tracking
- Manages state transitions and error handling
- Compiles final deployment reports with service endpoints
- Does NOT directly execute sub-agents (LangGraph handles coordination)

**Constraint Resolver Agent**
- Analyzes deployment feasibility given infrastructure constraints
- Recommends quantization levels, parallelization options, and serving frameworks
- Evaluates model requirements against available resources
- Provides confidence scores and technical recommendations

**CI Agent**
- Creates GitHub Actions workflows for automated CI/CD
- Generates build, test, and deployment pipeline configurations
- GitHub-only implementation (no GitLab)
- Provides workflow YAML files ready for repository integration

**Deployment Pipeline Agent**
- Handles Hugging Face model download and configuration
- Generates vLLM serving configuration
- Creates deployment scripts for model download and serving
- Performs health checks on vLLM endpoints

**Kubernetes Deployment Agent**
- Generates Kubernetes manifests (Deployment, Service, ConfigMap, ArgoCD Application)
- Commits manifests to GitHub repository (GitOps)
- Creates ArgoCD application (when configured)
- Triggers ArgoCD sync to MicroK8s cluster
- Configures GPU resources for vLLM pods
- Verifies deployment status and health
- Falls back to direct kubectl if ArgoCD not configured

## Project Structure

```
agentic-pipeline/
├── agents/                      # Individual agent implementations
│   ├── constraint_resolver/     # Constraint Resolver Agent ✅
│   ├── primary_agent/           # Primary Agent (orchestrator) ✅
│   ├── ci_agent/                # Continuous Integration Agent ✅
│   ├── deployment_pipeline/     # Deployment Pipeline Agent ✅
│   ├── kubernetes_deployment/   # Kubernetes Deployment Agent ✅
│   ├── optimization_agent/      # Inference Optimization Agent ❌ (Deferred)
│   ├── podman_deployment/       # Podman Deployment Agent ❌ (Deferred)
│   └── observability/           # Observability Agent ❌ (Deferred)
├── core/                       # Shared utilities
│   ├── graph/                  # LangGraph workflow ✅
│   ├── state/                  # LangGraph state management ✅
│   ├── llm/                    # LLM integration ✅
│   ├── models/                 # Model artifacts and data structures ✅
│   └── config/                 # Configuration management ✅
├── tools/                      # MCP tools, integrations
│   ├── github/                 # GitHub integration ✅
│   ├── huggingface/            # Hugging Face integration ✅
│   ├── argocd/                 # ArgoCD integration ✅
│   ├── gitops/                 # GitOps GitHub manifest manager ✅
│   └── infrastructure/         # Infrastructure checker ✅
├── tests/                      # Test suite
│   ├── test_constraint_resolver.py  # Test script for Constraint Resolver ✅
│   ├── test_primary_agent.py        # Test script for Primary Agent ✅
│   ├── test_ci_agent.py             # Test script for CI Agent ✅
│   ├── test_deployment_pipeline.py  # Test script for Deployment Pipeline ✅
│   ├── test_workflow.py            # Test script for LangGraph workflow ✅
│   ├── test_kubernetes_deployment.py # Test script for Kubernetes Deployment ✅
│   └── test_gitops_integration.py  # Test script for GitOps/ArgoCD integration ✅
└── main.py                     # Main entry point ✅
```

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL (optional, for state persistence)
- MicroK8s (for Kubernetes deployment)
- kubectl (configured for MicroK8s)
- NVIDIA GPU with drivers (for vLLM)
- vLLM (inference serving engine)
- GitHub account (for CI/CD)

### Installation

1. Install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Edit `.env` with your configuration:
```bash
# LLM Configuration
LLM_MODEL=qwen2.5:7b
LLM_TEMPERATURE=0.7
OLLAMA_BASE_URL=http://10.88.0.1:11434

# vLLM Configuration
VLLM_BASE_URL=http://localhost:8000/v1

# Database Configuration (optional)
DATABASE_URL=postgresql://user:password@localhost:5432/agentic_pipeline

# GitHub Configuration
GITHUB_TOKEN=your_github_token_here
GITHUB_REPO=your_org/your_repo

# Hugging Face Configuration
HUGGINGFACE_TOKEN=your_huggingface_token_here
HUGGINGFACE_MODEL_ID=Qwen/Qwen2.5-7B

# ArgoCD Configuration (required for GitOps deployment)
ARGOCD_URL=http://localhost:8080
ARGOCD_USERNAME=admin
ARGOCD_PASSWORD=your_argocd_password

# Kubernetes Configuration
DEFAULT_NAMESPACE=model-serving
DEFAULT_REPLICAS=1
DEFAULT_SERVICE_TYPE=LoadBalancer
DEFAULT_SERVICE_PORT=8000

# vLLM Configuration
DEFAULT_VLLM_IMAGE=vllm/vllm-openai
VLLM_IMAGE_TAG=latest
DEFAULT_GPU_MEMORY_UTILIZATION=0.9
DEFAULT_MAX_MODEL_LEN=4096
DEFAULT_TENSOR_PARALLEL_SIZE=1
```

### MicroK8s Setup

Ensure MicroK8s is running and kubectl is configured:
```bash
# Check MicroK8s status
microk8s status

# Enable required addons
microk8s enable dns storage

# Configure kubectl
microk8s config view
```

### Database Setup (Optional)

Create PostgreSQL database for state persistence:
```bash
createdb agentic_pipeline
```

The application will automatically create tables on first run.

## Usage

### Running the Main Application

Run the complete deployment workflow:
```bash
python main.py
```

This will:
1. Check infrastructure prerequisites
2. Run the LangGraph workflow
3. Deploy a model to MicroK8s
4. Provide deployment results

### Testing Components

All tests are located in the `tests/` directory:

```bash
# Test LangGraph workflow
python tests/test_workflow.py

# Test Kubernetes Deployment Agent
python tests/test_kubernetes_deployment.py

# Test Constraint Resolver Agent
python tests/test_constraint_resolver.py

# Test Primary Agent
python tests/test_primary_agent.py

# Test CI Agent
python tests/test_ci_agent.py

# Test Deployment Pipeline Agent
python tests/test_deployment_pipeline.py
```

### Infrastructure Verification

Check infrastructure prerequisites:
```python
from tools.infrastructure.infrastructure_checker import InfrastructureChecker

checker = InfrastructureChecker()
results = checker.check_all()
print(results)
```

### Running Individual Agents

Each agent can be imported and run independently:

```python
from agents.constraint_resolver import ConstraintResolverAgent
from agents.primary_agent import PrimaryAgent
from agents.ci_agent import CIAgent
from agents.deployment_pipeline import DeploymentPipelineAgent
from agents.kubernetes_deployment import KubernetesDeploymentAgent

# Constraint Resolver
constraint_agent = ConstraintResolverAgent()
result = await constraint_agent.analyze_constraints(state)

# Primary Agent
primary_agent = PrimaryAgent()
result = await primary_agent.orchestrate_deployment(state)

# CI Agent
ci_agent = CIAgent()
result = await ci_agent.create_ci_pipeline(state)

# Deployment Pipeline Agent
deployment_agent = DeploymentPipelineAgent()
result = await deployment_agent.create_deployment_pipeline(state)

# Kubernetes Deployment Agent
k8s_agent = KubernetesDeploymentAgent()
result = await k8s_agent.create_kubernetes_deployment(state)
```

## State Management

Agent states are persisted to PostgreSQL using the StateManager in `core/state/persistence.py`. States can be:

- Saved: `state_manager.save_state(conversation_id, state, current_agent)`
- Loaded: `state_manager.load_state(conversation_id)`
- Deleted: `state_manager.delete_state(conversation_id)`

## Development Workflow

### Phase 1 (Current - COMPLETE)
- ✅ **Constraint Resolver Agent** - Analyzes deployment feasibility
- ✅ **Primary Agent** - Orchestrates end-to-end deployment pipelines with LangGraph
- ✅ **CI Agent** - Creates GitHub Actions pipelines for automated CI/CD
- ✅ **Deployment Pipeline Agent** - Handles Hugging Face + vLLM deployment
- ✅ **Kubernetes Deployment Agent** - Manages MicroK8s deployment with GitOps
- ✅ **LangGraph Workflow** - State machine orchestration with ArgoCD sync
- ✅ **Infrastructure Checker** - Prerequisite verification
- ✅ **GitOps Integration** - GitHub manifest commits
- ✅ **ArgoCD Integration** - Application creation and sync
- ✅ **Configuration Management** - Settings-based defaults
- ✅ **Resource Calculation** - Infrastructure-derived resource requirements

### Deferred (Future Phases)
- ❌ **Inference Optimization Agent** - Model performance optimization (DEFERRED)
- ❌ **Docker Deployment Agent** - Container-based deployment (DEFERRED)
- ❌ **Observability Agent** - Monitoring and metrics (DEFERRED)
- ❌ **Autoscaling Agent** - Dynamic scaling (DEFERRED)
- ❌ **A/B Rollout Agent** - Canary and blue-green deployments (DEFERRED)

### Key Implementation Details

**LangGraph State Machine:**
```
IDLE → REQUEST_RECEIVED → CONSTRAINT_ANALYSIS → DEPLOYMENT_PREPARATION → 
CI_EXECUTION → K8S_MANIFEST_GENERATION → ARGOCD_APPLICATION_READY → 
ARGOCD_SYNCING → K8S_DEPLOYMENT → VLLM_STARTING → HEALTH_CHECK → DEPLOYED
```

**Conditional Edges:**
- Constraint Resolver: feasible → continue, infeasible → FAILED
- ArgoCD Sync: synced → health_check, failed → retry, skipped → health_check
- Health Check: healthy → DEPLOYED, unhealthy → retry

**GitOps Flow:**
1. Kubernetes manifests generated
2. Manifests committed to GitHub repository
3. ArgoCD application created
4. ArgoCD sync triggered
5. MicroK8s applies manifests
6. Deployment verified

**Fallback Behavior:**
- If ArgoCD not configured: skips GitOps, uses direct kubectl verification
- If GitHub not configured: fails gracefully with clear error
- If GPU not available: uses CPU-only deployment

## How to Use

### Quick Start

1. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your GitHub token, ArgoCD credentials, etc.
   ```

2. **Run the Main Application:**
   ```bash
   python main.py
   ```

   This will:
   - Check infrastructure prerequisites
   - Run the LangGraph workflow
   - Deploy a model to MicroK8s via GitOps
   - Provide deployment results with inference endpoint

3. **Test Individual Components:**
   ```bash
   # Test LangGraph workflow
   python tests/test_workflow.py
   
   # Test Kubernetes deployment
   python tests/test_kubernetes_deployment.py
   
   # Test GitOps integration
   python tests/test_gitops_integration.py
   ```

### Custom Deployment

To deploy a specific model, modify the model_id in `main.py`:

```python
model_id = "your-org/your-model"  # Change this
latency_requirement = "<100ms"    # Optional
deployment_type = "standard"      # Optional
```

### Infrastructure Requirements

**Required for Full GitOps Flow:**
- ✅ MicroK8s running and accessible via kubectl
- ✅ GitHub repository with write access
- ✅ ArgoCD server configured
- ✅ GPU with NVIDIA drivers (for vLLM)
- ✅ vLLM installed

**Minimum for Development:**
- ✅ MicroK8s accessible via kubectl
- ⚠️ GitHub token (for GitOps)
- ⚠️ ArgoCD server (for GitOps)
- ✅ GPU (for vLLM)
- ✅ vLLM installed

### Current Limitations

**Untested Components (Infrastructure Not Available):**
- ⚠️ ArgoCD server not configured - GitOps sync not tested
- ⚠️ GitHub token not configured - manifest commits not tested
- ⚠️ MicroK8s cluster-info timeout - cluster access issues

**Known Issues:**
- MicroK8s cluster-info command times out (network/connectivity issue)
- ArgoCD server needs to be set up for full GitOps flow
- GitHub token required for actual manifest commits

**What Works:**
- ✅ LangGraph workflow execution
- ✅ State machine transitions
- ✅ Agent coordination
- ✅ Manifest generation
- ✅ Infrastructure checking
- ✅ Resource calculation
- ✅ Configuration management
- ✅ Error handling and fallbacks

### Next Steps for Full Deployment

1. **Configure ArgoCD:**
   ```bash
   # Install ArgoCD server
   argocd install
   
   # Configure credentials in .env
   ARGOCD_URL=http://localhost:8080
   ARGOCD_USERNAME=admin
   ARGOCD_PASSWORD=your_password
   ```

2. **Configure GitHub:**
   ```bash
   # Add GitHub token to .env
   GITHUB_TOKEN=ghp_your_token_here
   GITHUB_REPO=your_org/your_repo
   ```

3. **Fix MicroK8s Access:**
   ```bash
   # Investigate cluster-info timeout
   kubectl cluster-info
   # May need to check network configuration
   ```

4. **Run Full Deployment:**
   ```bash
   python main.py
   # Should now execute full GitOps flow
   ```

## License

MIT