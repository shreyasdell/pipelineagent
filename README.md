# Agentic Pipeline

Agentic AI system for automated model deployment and inferencing using LangChain + LangGraph.

## Architecture

This system uses a multi-agent architecture with LangGraph as the orchestrator and LangChain for LLM integration:

- **LangGraph**: Manages agent coordination and state management
- **LangChain**: Handles LLM calls and tool integration
- **PostgreSQL**: Persistent state storage
- **Podman**: Container runtime for deployment
- **GitHub**: CI/CD and repository management

### Agent Capabilities

**Primary Agent**
- Orchestrates end-to-end model deployment pipelines
- Decomposes deployment requirements into sub-agent tasks
- Manages containerization, serving frameworks, autoscaling, and A/B rollout strategies
- Generates deployment conversation IDs for tracking
- Compiles final deployment reports with service endpoints and latency metrics

**CI Agent**
- Creates GitHub Actions workflows for automated CI/CD
- Generates build, test, and deployment pipeline configurations
- Implements security best practices and testing strategies
- Supports canary, blue-green, and standard deployment strategies
- Provides workflow YAML files ready for repository integration

**Constraint Resolver Agent**
- Analyzes deployment feasibility given infrastructure constraints
- Recommends quantization levels, parallelization options, and serving frameworks
- Evaluates model requirements against available resources
- Provides confidence scores and technical recommendations

## Project Structure

```
agentic-pipeline/
├── agents/                 # Individual agent implementations
│   ├── constraint_resolver/  # Constraint Resolver Agent ✅
│   ├── primary_agent/        # Primary Agent (orchestrator) ✅
│   ├── ci_agent/             # Continuous Integration Agent ✅
│   ├── optimization_agent/   # Inference Optimization Agent ⏳
│   ├── deployment_pipeline/  # Deployment Pipeline Agent ⏳
│   ├── k8s_deployment/       # Kubernetes Deployment Agent ⏳
│   ├── podman_deployment/    # Podman Deployment Agent ⏳
│   └── observability/        # Observability Agent ⏳
├── core/                   # Shared utilities
│   ├── state/              # LangGraph state management
│   ├── llm/                # LLM integration
│   ├── models/             # Model artifacts and data structures
│   └── config/             # Configuration management
├── tools/                  # MCP tools, integrations
│   ├── github/
│   ├── podman/
│   └── argocd/
├── deployment/             # Deployment configurations
│   ├── podman/
│   └── kubernetes/
└── tests/                  # Test suite
    ├── test_constraint_resolver.py  # Test script for Constraint Resolver
    ├── test_primary_agent.py        # Test script for Primary Agent
    ├── test_ci_agent.py             # Test script for CI Agent
    └── test_deployment_pipeline.py  # Test script for Deployment Pipeline Agent
```

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL
- Podman
- Ollama (for local LLM) or vLLM (for production LLM serving)

### Installation

1. Install dependencies:
```bash
poetry install
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
OLLAMA_BASE_URL=http://127.0.0.1:11434

# Primary Agent Configuration
DEFAULT_CONTAINER_REGISTRY=docker.io
DEFAULT_ORGANIZATION=your-org
DEFAULT_BASE_IMAGE=nvidia/cuda:12.1.0-runtime-ubuntu22.04
SERVICE_ENDPOINT_BASE_URL=https://api.example.com/inference

# Serving Framework Configuration
SERVING_FRAMEWORK_PRIORITY=tensorrt-llm,vllm,triton,bentoml,sglang,llama.cpp

# Autoscaling Configuration
DEFAULT_MIN_REPLICAS=2
DEFAULT_MAX_REPLICAS=10
DEFAULT_TARGET_CPU_UTILIZATION=70
DEFAULT_TARGET_MEMORY_UTILIZATION=80

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/agentic_pipeline
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=agentic_pipeline

# GitHub Configuration
GITHUB_TOKEN=your_github_token_here
GITHUB_REPO=your_org/your_repo
```

### Database Setup

Create PostgreSQL database:
```bash
createdb agentic_pipeline
```

The application will automatically create tables on first run.

### Starting vLLM (Optional for Production)

For production LLM serving, you can start vLLM instead of using Ollama:

```bash
bash start_vllm.sh
```

This will start the vLLM server with Qwen 2.5 7B model on port 8000.

## Usage

### Testing Agents

All tests are located in the `tests/` directory for modularity:

```bash
# Test Constraint Resolver Agent
python tests/test_constraint_resolver.py

# Test Primary Agent
python tests/test_primary_agent.py

# Test CI Agent
python tests/test_ci_agent.py

# Test Deployment Pipeline Agent
python tests/test_deployment_pipeline.py
```

### Testing Constraint Resolver Agent

The Constraint Resolver Agent analyzes deployment feasibility. This will analyze deployment feasibility for a sample model with the given infrastructure constraints.

### Testing Primary Agent

The Primary Agent orchestrates end-to-end deployment pipelines. This will demonstrate task decomposition, sub-agent coordination, and final deployment report generation.

### Testing CI Agent

The CI Agent creates GitHub Actions pipelines for automated CI/CD. This will generate GitHub Actions workflows for build, test, and deployment stages, and save them to GitHub if configured.

### Testing Deployment Pipeline Agent

The Deployment Pipeline Agent handles CI/CD pipeline creation for model packaging and container image builds, with ArgoCD integration for deployment verification.

### Running Individual Agents

Each agent can be imported and run independently:

```python
from agents.constraint_resolver import ConstraintResolverAgent
from agents.primary_agent import PrimaryAgent
from agents.ci_agent import CIAgent
from agents.deployment_pipeline import DeploymentPipelineAgent

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
```

## Development Workflow

We're building agents incrementally:

1. ✅ **Constraint Resolver Agent** - Analyzes deployment feasibility
2. ✅ **Primary Agent** - Orchestrates end-to-end deployment pipelines with task decomposition
3. ✅ **CI Agent** - Creates GitHub Actions pipelines for automated CI/CD
4. ⏳ **Inference Optimization Agent** - Optimizes model performance
5. ⏳ **Deployment Pipeline Agent** - Handles containerization and deployment
6. ⏳ **Sub-agents** - Containerization, Serving Framework, Autoscaling, A/B Rollout agents

## State Management

Agent states are persisted to PostgreSQL using the StateManager in `core/state/persistence.py`. States can be:

- Saved: `state_manager.save_state(conversation_id, state, current_agent)`
- Loaded: `state_manager.load_state(conversation_id)`
- Deleted: `state_manager.delete_state(conversation_id)`

## Deployment

The system is designed for containerized deployment using Podman:

```bash
# Build containers
podman build -t agentic-pipeline .

# Run with Podman Compose
podman-compose up
```

## Migration to Remote Lab

The codebase is designed to be portable:

1. All configuration is environment-based
2. State persistence uses standard PostgreSQL
3. Container runtime is Podman (daemonless, rootless)
4. No hard-coded paths or dependencies

To migrate to your remote lab:

1. Copy the entire project directory
2. Update `.env` with remote lab configurations
3. Ensure PostgreSQL is available
4. Install Podman on the remote lab
5. Run the same commands

## License

MIT