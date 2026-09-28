# Agentic Pipeline

Agentic AI system for automated model deployment and inferencing using LangChain + LangGraph.

## Architecture

This system uses a multi-agent architecture with LangGraph as the orchestrator and LangChain for LLM integration:

- **LangGraph**: Manages agent coordination and state management
- **LangChain**: Handles LLM calls and tool integration
- **PostgreSQL**: Persistent state storage
- **Podman**: Container runtime for deployment
- **GitHub**: CI/CD and repository management

## Project Structure

```
agentic-pipeline/
├── agents/                 # Individual agent implementations
│   ├── constraint_resolver/  # Constraint Resolver Agent
│   ├── primary_agent/        # Primary Agent (orchestrator)
│   ├── optimization_agent/   # Inference Optimization Agent
│   ├── ci_agent/             # Continuous Integration Agent
│   ├── deployment_pipeline/  # Deployment Pipeline Agent
│   ├── k8s_deployment/       # Kubernetes Deployment Agent
│   ├── podman_deployment/    # Podman Deployment Agent
│   └── observability/        # Observability Agent
├── core/                   # Shared utilities
│   ├── state/              # LangGraph state management
│   ├── llm/                # LLM integration
│   └── config/             # Configuration management
├── tools/                  # MCP tools, integrations
│   ├── github/
│   ├── podman/
│   └── argocd/
├── deployment/             # Deployment configurations
│   ├── podman/
│   └── kubernetes/
└── test_constraint_resolver.py  # Test script for Constraint Resolver
```

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL
- Podman
- OpenAI API key

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
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/agentic_pipeline
GITHUB_TOKEN=your_github_token_here
GITHUB_REPO=your_org/your_repo
```

### Database Setup

Create PostgreSQL database:
```bash
createdb agentic_pipeline
```

The application will automatically create tables on first run.

## Usage

### Testing Constraint Resolver Agent

The Constraint Resolver Agent is the first fully implemented agent. Test it with:

```bash
python test_constraint_resolver.py
```

This will analyze deployment feasibility for a sample model with the given infrastructure constraints.

### Running Individual Agents

Each agent can be imported and run independently:

```python
from agents.constraint_resolver import ConstraintResolverAgent

agent = ConstraintResolverAgent()
result = await agent.analyze_constraints(state)
```

## Development Workflow

We're building agents incrementally:

1. ✅ **Constraint Resolver Agent** - Analyzes deployment feasibility
2. ⏳ **Primary Agent** - Orchestrates all agents
3. ⏳ **Inference Optimization Agent** - Optimizes model performance
4. ⏳ **CI Agent** - Creates GitHub Actions pipelines
5. ⏳ **Deployment Pipeline Agent** - Handles containerization and deployment

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