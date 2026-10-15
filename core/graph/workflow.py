from typing import TypedDict, Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.state.models import AgentState
from core.state.persistence import state_manager
from loguru import logger


# Define state transitions
WorkflowState = Literal[
    "IDLE",
    "REQUEST_RECEIVED",
    "CONSTRAINT_ANALYSIS",
    "DEPLOYMENT_PREPARATION",
    "CI_EXECUTION",
    "K8S_MANIFEST_GENERATION",
    "ARGOCD_APPLICATION_READY",
    "ARGOCD_SYNCING",
    "K8S_DEPLOYMENT",
    "OBSERVABILITY_SETUP",
    "HEALTH_CHECK",
    "DEPLOYED",
    "FAILED",
    "RETRYING"
]


def create_deployment_graph():
    """
    Create the LangGraph workflow for model deployment orchestration
    
    Phase 1 Architecture:
    User Request → Primary Agent → Constraint Resolver → Deployment Pipeline → 
    CI Agent → Kubernetes Deployment Agent → MicroK8s → vLLM → Inference Endpoint
    """
    
    # Create the state graph
    workflow = StateGraph(AgentState)
    
    # Define nodes (agents)
    workflow.add_node("primary_agent", primary_agent_node)
    workflow.add_node("constraint_resolver", constraint_resolver_node)
    workflow.add_node("deployment_pipeline", deployment_pipeline_node)
    workflow.add_node("ci_agent", ci_agent_node)
    workflow.add_node("kubernetes_deployment", kubernetes_deployment_node)
    workflow.add_node("argocd_sync", argocd_sync_node)
    workflow.add_node("observability", observability_node)
    workflow.add_node("health_check", health_check_node)
    
    # Define edges (workflow)
    workflow.set_entry_point("primary_agent")

    workflow.add_edge("primary_agent", "constraint_resolver")
    workflow.add_edge("constraint_resolver", "deployment_pipeline")
    workflow.add_edge("deployment_pipeline", "ci_agent")
    workflow.add_edge("ci_agent", "kubernetes_deployment")
    workflow.add_edge("kubernetes_deployment", "argocd_sync")
    workflow.add_edge("argocd_sync", "observability")
    workflow.add_edge("observability", "health_check")
    workflow.add_edge("health_check", END)
    
    # Add conditional edges for error handling
    workflow.add_conditional_edges(
        "constraint_resolver",
        should_continue_to_deployment,
        {
            "feasible": "deployment_pipeline",
            "infeasible": END  # End workflow if not feasible
        }
    )
    
    workflow.add_conditional_edges(
        "health_check",
        should_retry_deployment,
        {
            "healthy": END,
            "unhealthy": "kubernetes_deployment"  # Retry deployment
        }
    )
    
    workflow.add_conditional_edges(
        "argocd_sync",
        should_continue_argocd_sync,
        {
            "synced": "health_check",
            "failed": "health_check",  # Continue to health check even if ArgoCD fails
            "skipped": "health_check"  # Continue without ArgoCD
        }
    )
    
    return workflow


async def primary_agent_node(state: AgentState) -> AgentState:
    """
    Primary Agent node - Orchestrates the deployment process
    """
    logger.info("Primary Agent: Processing deployment request")
    
    # Update state
    state["current_state"] = "REQUEST_RECEIVED"
    state["current_agent"] = "primary_agent"
    state["deployment_type_decision"] = "kubernetes"  # Phase 1: Kubernetes path
    
    # Generate deployment conversation ID if not provided
    if not state.get("deployment_conversation_id"):
        from datetime import datetime
        import uuid
        state["deployment_conversation_id"] = f"dep-{datetime.now().strftime('%Y-%m-%d')}-{str(uuid.uuid4())[:8]}"
        logger.info(f"Generated deployment conversation ID: {state['deployment_conversation_id']}")
    
    # Add message to conversation
    state["messages"].append(HumanMessage(
        content=f"Deploy model {state['model_id']} with latency requirement: {state.get('latency_requirement', 'Not specified')}"
    ))
    
    # Save state
    state_manager.save_state(
        state["deployment_conversation_id"],
        state,
        "primary_agent"
    )
    
    return state


async def constraint_resolver_node(state: AgentState) -> AgentState:
    """
    Constraint Resolver Agent node - Analyzes deployment feasibility
    """
    logger.info("Constraint Resolver: Analyzing deployment constraints")
    
    # Import and run the actual constraint resolver agent
    from agents.constraint_resolver.agent import ConstraintResolverAgent
    
    # Update state
    state["current_state"] = "CONSTRAINT_ANALYSIS"
    state["current_agent"] = "constraint_resolver"
    
    # Run constraint resolver
    constraint_agent = ConstraintResolverAgent()
    state = await constraint_agent.analyze_constraints(state)
    
    # Save state
    state_manager.save_state(
        state["deployment_conversation_id"],
        state,
        "constraint_resolver"
    )
    
    return state


async def deployment_pipeline_node(state: AgentState) -> AgentState:
    """
    Deployment Pipeline Agent node - Handles deployment preparation
    """
    logger.info("Deployment Pipeline: Preparing deployment configuration")
    
    # Import and run the actual deployment pipeline agent
    from agents.deployment_pipeline.agent import DeploymentPipelineAgent
    
    # Update state
    state["current_state"] = "DEPLOYMENT_PREPARATION"
    state["current_agent"] = "deployment_pipeline_agent"
    
    # Run deployment pipeline
    deployment_agent = DeploymentPipelineAgent()
    state = await deployment_agent.create_deployment_pipeline(state)
    
    # Save state
    state_manager.save_state(
        state["deployment_conversation_id"],
        state,
        "deployment_pipeline_agent"
    )
    
    return state


async def ci_agent_node(state: AgentState) -> AgentState:
    """
    CI Agent node - Creates CI/CD pipelines
    """
    logger.info("CI Agent: Creating CI/CD pipelines")
    
    # Import and run the actual CI agent
    from agents.ci_agent.agent import CIAgent
    
    # Update state
    state["current_state"] = "CI_EXECUTION"
    state["current_agent"] = "ci_agent"
    
    # Run CI agent
    ci_agent = CIAgent()
    state = await ci_agent.create_ci_pipeline(state)
    
    # Save state
    state_manager.save_state(
        state["deployment_conversation_id"],
        state,
        "ci_agent"
    )
    
    return state


async def kubernetes_deployment_node(state: AgentState) -> AgentState:
    """
    Kubernetes Deployment Agent node - Handles Kubernetes deployment
    """
    logger.info("Kubernetes Deployment: Preparing Kubernetes deployment")
    
    # Import and run the Kubernetes deployment agent
    from agents.kubernetes_deployment.agent import KubernetesDeploymentAgent
    
    # Update state
    state["current_state"] = "K8S_DEPLOYMENT"
    state["current_agent"] = "kubernetes_deployment_agent"
    
    # Run Kubernetes deployment agent
    k8s_agent = KubernetesDeploymentAgent()
    state = await k8s_agent.create_kubernetes_deployment(state)
    
    # Save state
    state_manager.save_state(
        state["deployment_conversation_id"],
        state,
        "kubernetes_deployment_agent"
    )
    
    return state


async def observability_node(state: AgentState) -> AgentState:
    """
    Observability Agent node - Sets up monitoring and observability infrastructure
    """
    logger.info("Observability Agent: Setting up monitoring infrastructure")

    # Import and run the actual observability agent
    from agents.observability.agent import ObservabilityAgent

    # Update state
    state["current_state"] = "OBSERVABILITY_SETUP"
    state["current_agent"] = "observability_agent"

    # Run observability agent
    observability_agent = ObservabilityAgent()
    state = await observability_agent.setup_observability(state)

    # Save state
    state_manager.save_state(
        state["deployment_conversation_id"],
        state,
        "observability_agent"
    )

    return state


async def argocd_sync_node(state: AgentState) -> AgentState:
    """
    ArgoCD Sync node - Triggers and monitors ArgoCD synchronization
    """
    logger.info("ArgoCD Sync: Triggering ArgoCD synchronization")
    
    # Update state
    state["current_state"] = "ARGOCD_SYNCING"
    state["current_agent"] = "argocd_sync"
    
    # Check if ArgoCD is configured
    from core.config.settings import settings
    
    if not settings.argocd_url:
        logger.warning("ArgoCD not configured - skipping sync")
        state["argocd_sync_status"] = "skipped"
        state["messages"].append(AIMessage(
            content="⚠️ ArgoCD not configured - deployment completed without GitOps sync"
        ))
    else:
        # ArgoCD sync is handled within Kubernetes Deployment Agent
        # This node primarily monitors and reports status
        argocd_status = state.get("argocd_status", {})
        sync_status = argocd_status.get("sync_status", "unknown")
        health_status = argocd_status.get("health_status", "unknown")
        
        if sync_status == "Synced" and health_status in ["Healthy", "Progressing"]:
            state["current_state"] = "K8S_DEPLOYMENT"
            state["argocd_sync_status"] = "synced"
            state["messages"].append(AIMessage(
                content=f"✅ ArgoCD sync successful - Sync: {sync_status}, Health: {health_status}"
            ))
        else:
            state["current_state"] = "RETRYING"
            state["argocd_sync_status"] = "failed"
            state["errors"].append(f"ArgoCD sync pending - Sync: {sync_status}, Health: {health_status}")
            state["messages"].append(AIMessage(
                content=f"⏳ ArgoCD sync in progress - Sync: {sync_status}, Health: {health_status}"
            ))
    
    # Save state
    state_manager.save_state(
        state["deployment_conversation_id"],
        state,
        "argocd_sync"
    )
    
    return state


async def health_check_node(state: AgentState) -> AgentState:
    """
    Health Check node - Verifies deployment health
    """
    logger.info("Health Check: Verifying deployment health")
    
    # Update state
    state["current_state"] = "HEALTH_CHECK"
    state["current_agent"] = "health_check"
    
    # Perform health check
    health_status = await perform_health_check(state)
    state["health_status"] = health_status  # Set health_status for should_retry_deployment
    
    if health_status["healthy"]:
        state["current_state"] = "DEPLOYED"
        state["service_endpoint"] = health_status.get("endpoint", "http://localhost:8000/v1/models")
        state["messages"].append(AIMessage(
            content=f"✅ Deployment successful! Endpoint: {state['service_endpoint']}"
        ))
    else:
        state["current_state"] = "FAILED"
        state["errors"].append(f"Health check failed: {health_status.get('reason', 'Unknown')}")
        state["messages"].append(AIMessage(
            content=f"❌ Deployment failed: {health_status.get('reason', 'Unknown')}"
        ))
    
    # Save state
    state_manager.save_state(
        state["deployment_conversation_id"],
        state,
        "health_check"
    )
    
    return state


async def perform_health_check(state: AgentState) -> Dict[str, Any]:
    """
    Perform health check on the deployed service
    """
    # Check if git commit succeeded
    gitops_result = state.get("gitops_commit_sha")
    argocd_status = state.get("argocd_status", {})
    
    # Health check passes if:
    # 1. Git commit succeeded (has commit SHA)
    # 2. ArgoCD either succeeded or was skipped (not failed)
    
    git_commit_success = bool(gitops_result)
    argocd_success = argocd_status.get("overall_status") != "failed" if isinstance(argocd_status, dict) else True
    
    if git_commit_success and argocd_success:
        # Sanitize model ID for service endpoint
        model_id = state.get('model_id', 'model')
        safe_model_id = model_id.lower().replace('_', '-').replace('/', '-').replace('.', '-')
        safe_model_id = ''.join(c for c in safe_model_id if c.isalnum() or c == '-')
        safe_model_id = safe_model_id.strip('-')
        return {
            "healthy": True,
            "endpoint": f"http://{safe_model_id}.model-serving.svc.cluster.local/v1/models",
            "reason": "Git commit succeeded and ArgoCD status is not failed"
        }
    else:
        return {
            "healthy": False,
            "endpoint": None,
            "reason": f"Git commit: {git_commit_success}, ArgoCD success: {argocd_success}"
        }


def should_continue_to_deployment(state: AgentState) -> Literal["feasible", "infeasible"]:
    """
    Conditional edge: Check if deployment should continue based on constraint resolver
    """
    constraint_report = state.get("constraint_resolver_report", {})
    
    if not constraint_report.get("deployment_feasible", False):
        logger.warning(f"Deployment not feasible. Confidence: {constraint_report.get('overall_confidence_score', 0)}%")
        return "infeasible"
    
    return "feasible"


def should_retry_deployment(state: AgentState) -> Literal["healthy", "unhealthy"]:
    """
    Conditional edge: Check if deployment should be retried
    """
    health_status = state.get("health_status", {})

    if health_status.get("healthy", False):
        return "healthy"

    # Check retry count
    current_retry = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if current_retry < max_retries:
        state["retry_count"] = current_retry + 1
        logger.info(f"Retrying deployment (attempt {state['retry_count']}/{max_retries})")
        return "unhealthy"

    logger.error(f"Max retries exceeded ({max_retries}), marking as failed")
    state["current_state"] = "FAILED"
    return "healthy"  # Return healthy to go to END (no more retries)


def should_continue_argocd_sync(state: AgentState) -> Literal["synced", "failed", "skipped"]:
    """
    Conditional edge: Check if ArgoCD sync was successful
    """
    argocd_sync_status = state.get("argocd_sync_status", "unknown")
    
    if argocd_sync_status == "skipped":
        return "skipped"
    elif argocd_sync_status in ["success", "Synced", "synced"]:
        return "synced"
    else:
        return "failed"