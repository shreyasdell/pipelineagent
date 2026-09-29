from typing import Dict, Any, Optional, List
import json
import re
import uuid
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from core.state.models import AgentState
from core.llm.config import get_llm, get_prompt_template
from core.state.persistence import state_manager
from core.config.settings import settings
from loguru import logger


class PrimaryAgent:
    """
    Primary Agent - Orchestrates end-to-end model deployment pipelines
    Manages containerization, serving frameworks, autoscaling, and A/B rollout strategies
    """
    
    def __init__(self):
        self.llm = get_llm()
        self.system_prompt = """You are a Primary Agent for AI model deployment orchestration.
Your task is to analyze deployment requirements and decompose them into sub-tasks for specialized sub-agents.

You need to:
1. Analyze the deployment requirements (model_id, latency_requirement, deployment_type)
2. Determine what sub-tasks are needed
3. Create specific, actionable tasks for each sub-agent
4. Consider the constraint resolver report if available

Sub-agent capabilities:
- Constraint Resolver Agent: Analyzes deployment feasibility given infrastructure constraints
- Inference Optimization Agent: Applies quantization, batching, and hardware-specific optimizations for low-latency inference
- Containerization Sub-Agent: Handles containerization of the model with appropriate runtime environment
- Serving Framework Sub-Agent: Picks and configures serving framework (vLLM, TensorRT-LLM, Triton, etc.)
- Autoscaling Sub-Agent: Configures autoscaling for expected traffic patterns
- A/B Rollout Sub-Agent: Manages canary/blue-green deployment strategies
- Deployment Pipeline Sub-Agent: Handles CI/CD pipeline creation for model packaging and container image builds
- Continuous Integration Agent: Connects to model repositories, forms CI pipelines for the given model and saves CI code to GitHub

IMPORTANT: You must respond with a valid JSON object in the following format:
{{
    "reasoning": "<your reasoning about what needs to be done>",
    "sub_agent_tasks": [
        {{
            "task_id": "<unique task id>",
            "task_name": "<task name>",
            "assigned_to": "<sub-agent name>",
            "description": "<detailed task description>",
            "parameters": {{
                "model_id": "<model id>",
                "latency_requirement": "<latency requirement>",
                "deployment_type": "<deployment type>",
                "additional_context": "<any additional context>"
            }},
            "dependencies": [],
            "priority": "high|medium|low"
        }}
    ]
}}"""
    
    async def orchestrate_deployment(self, state: AgentState) -> AgentState:
        """
        Orchestrate the end-to-end deployment pipeline
        
        Args:
            state: Current agent state with model_id, latency_requirement, deployment_type, etc.
            
        Returns:
            Updated state with decomposed_sub_agent_tasks and final_deployment_report
        """
        logger.info(f"Primary Agent orchestrating deployment for model: {state['model_id']}")
        
        # Update current agent in state
        state["current_agent"] = "primary_agent"
        
        # Generate deployment conversation ID if not provided
        if not state.get("deployment_conversation_id"):
            state["deployment_conversation_id"] = f"dep-{datetime.now().strftime('%Y-%m-%d')}-{str(uuid.uuid4())[:8]}"
            logger.info(f"Generated deployment conversation ID: {state['deployment_conversation_id']}")
        
        # Save state to persistence
        state_manager.save_state(
            state["deployment_conversation_id"],
            state,
            "primary_agent"
        )
        
        try:
            # Step 1: Decompose deployment into sub-tasks
            logger.info("Decomposing deployment into sub-tasks...")
            sub_agent_tasks = await self._decompose_tasks(state)
            state["decomposed_sub_agent_tasks"] = sub_agent_tasks
            
            # Step 2: Execute sub-agent tasks (simulated for now)
            logger.info("Executing sub-agent tasks...")
            task_results = await self._execute_sub_agent_tasks(sub_agent_tasks, state)
            
            # Step 3: Compile final deployment report
            logger.info("Compiling final deployment report...")
            final_report = await self._compile_final_report(state, task_results)
            state["final_deployment_report"] = final_report
            
            # Add message to conversation
            state["messages"].append(AIMessage(
                content=f"Deployment orchestration complete. Report: {json.dumps(final_report, indent=2)}"
            ))
            
            # Save updated state
            state_manager.save_state(
                state["deployment_conversation_id"],
                state,
                "primary_agent"
            )
            
            logger.info(f"Primary Agent orchestration complete for {state['model_id']}")
            
        except Exception as e:
            logger.error(f"Error in deployment orchestration: {e}")
            state["errors"].append(f"Primary Agent error: {str(e)}")
            state["messages"].append(AIMessage(content=f"Error in deployment orchestration: {str(e)}"))
        
        return state
    
    async def _decompose_tasks(self, state: AgentState) -> List[Dict[str, Any]]:
        """
        Decompose deployment requirements into sub-agent tasks using LLM
        
        Args:
            state: Current agent state
            
        Returns:
            List of sub-agent tasks
        """
        # Prepare decomposition prompt
        decomposition_prompt = self._prepare_decomposition_prompt(state)
        
        # Get LLM response
        prompt_template = get_prompt_template(self.system_prompt)
        chain = prompt_template | self.llm
        
        response = await chain.ainvoke({"input": decomposition_prompt})
        
        logger.info(f"Raw LLM response for task decomposition: {response.content[:500]}")
        
        # Parse response into structured tasks
        tasks = self._parse_sub_agent_tasks(response.content, state)
        
        logger.info(f"Decomposed into {len(tasks)} sub-agent tasks")
        return tasks
    
    def _prepare_decomposition_prompt(self, state: AgentState) -> str:
        """Prepare the decomposition prompt for the LLM"""
        prompt = f"""
Deployment Requirements:
- Model ID: {state['model_id']}
- Latency Requirement: {state.get('latency_requirement', 'Not specified')}
- Deployment Type: {state.get('deployment_type', 'Not specified')}
- Deployment Conversation ID: {state['deployment_conversation_id']}
"""
        
        # Add constraint resolver report if available
        if state.get("constraint_resolver_report"):
            prompt += f"""
Constraint Resolver Report:
- Overall Confidence Score: {state['constraint_resolver_report'].get('overall_confidence_score', 'N/A')}%
- Deployment Feasible: {state['constraint_resolver_report'].get('deployment_feasible', 'N/A')}
- Recommended Engine: {state['constraint_resolver_report'].get('engine_type', 'N/A')}
- Recommended Weight Format: {state['constraint_resolver_report'].get('weight_format', 'N/A')}
- Quantization Levels: {state['constraint_resolver_report'].get('quantization_levels_possible', [])}
- Parallelization Options: {state['constraint_resolver_report'].get('parallelization_possible', {})}
"""
        
        # Add infrastructure details if available
        if state.get("infrastructure_details"):
            prompt += f"""
Infrastructure Details:
{self._format_infrastructure_details(state.get('infrastructure_details', {}))}
"""
        
        prompt += """
Please analyze these requirements and decompose the deployment into specific sub-agent tasks.
Consider the constraint resolver recommendations when creating tasks.
"""
        return prompt
    
    def _format_infrastructure_details(self, infra_details: Dict[str, Any]) -> str:
        """Format infrastructure details for the prompt"""
        if not infra_details:
            return "No infrastructure details provided"
        
        formatted = []
        for key, value in infra_details.items():
            formatted.append(f"- {key}: {value}")
        
        return "\n".join(formatted)
    
    def _parse_sub_agent_tasks(self, llm_response: str, state: AgentState) -> List[Dict[str, Any]]:
        """
        Parse LLM response into structured sub-agent tasks
        
        Args:
            llm_response: Raw LLM response
            state: Current agent state
            
        Returns:
            List of parsed sub-agent tasks
        """
        try:
            # Remove markdown code blocks if present
            cleaned_response = llm_response
            cleaned_response = re.sub(r'```json\s*', '', cleaned_response)
            cleaned_response = re.sub(r'```\s*', '', cleaned_response)
            
            # Try to parse the entire response as JSON first
            try:
                parsed_data = json.loads(cleaned_response.strip())
                logger.info(f"Successfully parsed full response as JSON")
            except json.JSONDecodeError:
                # Try to extract JSON object
                first_brace = cleaned_response.find('{')
                last_brace = cleaned_response.rfind('}')
                
                if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
                    json_str = cleaned_response[first_brace:last_brace + 1]
                    logger.info(f"Extracted JSON: {json_str[:200]}...")
                    parsed_data = json.loads(json_str)
                else:
                    # Fallback to default tasks
                    logger.warning("No JSON found in LLM response, using default tasks")
                    return self._create_default_tasks(state)
            
            # Extract and validate tasks
            tasks = parsed_data.get("sub_agent_tasks", [])
            if not tasks:
                logger.warning("No sub_agent_tasks found in response, using default tasks")
                return self._create_default_tasks(state)
            
            # Add task IDs if missing
            for i, task in enumerate(tasks):
                if "task_id" not in task:
                    task["task_id"] = f"task-{i+1}"
                if "dependencies" not in task:
                    task["dependencies"] = []
                if "priority" not in task:
                    task["priority"] = "medium"
            
            logger.info(f"Parsed {len(tasks)} sub-agent tasks from LLM response")
            return tasks
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return self._create_default_tasks(state)
        except Exception as e:
            logger.error(f"Error parsing sub-agent tasks: {e}")
            return self._create_default_tasks(state)
    
    def _create_default_tasks(self, state: AgentState) -> List[Dict[str, Any]]:
        """
        Create default sub-agent tasks when LLM parsing fails
        
        Args:
            state: Current agent state
            
        Returns:
            List of default sub-agent tasks
        """
        return [
            {
                "task_id": "task-1",
                "task_name": "Create CI Pipeline",
                "assigned_to": "ci_agent",
                "description": f"Create GitHub Actions CI pipeline for model {state['model_id']}",
                "parameters": {
                    "model_id": state['model_id'],
                    "latency_requirement": state.get('latency_requirement'),
                    "deployment_type": state.get('deployment_type'),
                    "additional_context": "Generate CI workflows and save to GitHub repository"
                },
                "dependencies": [],
                "priority": "high"
            },
            {
                "task_id": "task-2",
                "task_name": "Create Deployment Pipeline",
                "assigned_to": "deployment_pipeline_agent",
                "description": f"Create deployment pipeline for model {state['model_id']}",
                "parameters": {
                    "model_id": state['model_id'],
                    "latency_requirement": state.get('latency_requirement'),
                    "deployment_type": state.get('deployment_type'),
                    "additional_context": "Generate deployment configs and verify with ArgoCD"
                },
                "dependencies": ["task-1"],
                "priority": "high"
            }
        ]
    
    async def _execute_sub_agent_tasks(self, tasks: List[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
        """
        Execute sub-agent tasks (simulated for now since sub-agents aren't implemented)
        
        Args:
            tasks: List of sub-agent tasks
            state: Current agent state
            
        Returns:
            Dictionary of task results
        """
        task_results = {}
        
        for task in tasks:
            logger.info(f"Executing task: {task['task_name']} (assigned to: {task['assigned_to']})")
            
            # Simulate task execution with mock results
            # In real implementation, this would call the actual sub-agents
            task_results[task['task_id']] = {
                "task_id": task['task_id'],
                "task_name": task['task_name'],
                "assigned_to": task['assigned_to'],
                "status": "completed",
                "result": self._simulate_task_result(task, state),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Task {task['task_id']} completed")
        
        return task_results
    
    def _simulate_task_result(self, task: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """
        Simulate task result for a given task
        
        Args:
            task: Task definition
            state: Current agent state
            
        Returns:
            Simulated task result
        """
        task_type = task['assigned_to']
        model_id = state['model_id']
        
        # Simulate different results based on task type
        if task_type == "ci_agent":
            return {
                "pipeline_id": f"ci-{model_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "github_repository": settings.github_repo or "Not configured",
                "workflows_created": ["build-and-test", "deploy"],
                "workflow_files": {
                    "build-and-test": {
                        "status": "created" if settings.github_repo else "skipped",
                        "file_path": ".github/workflows/build-and-test.yaml"
                    },
                    "deploy": {
                        "status": "created" if settings.github_repo else "skipped",
                        "file_path": ".github/workflows/deploy.yaml"
                    }
                },
                "pipeline_verification": {
                    "overall_status": "success" if settings.github_repo else "skipped",
                    "message": "CI pipeline verified successfully" if settings.github_repo else "GitHub not configured"
                },
                "status": "completed"
            }
        elif task_type == "deployment_pipeline_agent":
            return {
                "deployment_id": f"deploy-{model_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "argocd_application": f"{model_id.replace('_', '-')}",
                "kubernetes_manifests": {
                    "deployment": f"deployment/{model_id}.yaml",
                    "service": f"service/{model_id}.yaml"
                },
                "container_image": f"{settings.default_organization}/{model_id}:latest",
                "argocd_verification": {
                    "overall_status": "success" if settings.argocd_url else "argocd_not_configured",
                    "all_indicators_positive": True if settings.argocd_url else False,
                    "message": "ArgoCD shows all positive indicators" if settings.argocd_url else "ArgoCD not configured"
                },
                "deployment_status": "deployed_and_healthy" if settings.argocd_url else "argocd_not_configured",
                "status": "completed"
            }
        else:
            return {
                "status": "completed",
                "message": f"Task {task['task_name']} completed successfully"
            }
    
    async def _compile_final_report(self, state: AgentState, task_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compile final deployment report from task results
        
        Args:
            state: Current agent state
            task_results: Results from sub-agent tasks
            
        Returns:
            Final deployment report
        """
        model_id = state['model_id']
        deployment_type = state.get('deployment_type', 'standard')
        
        # Extract information from task results
        ci_result = next(
            (r for r in task_results.values() if r['assigned_to'] == 'ci_agent'),
            {}
        )
        deployment_result = next(
            (r for r in task_results.values() if r['assigned_to'] == 'deployment_pipeline_agent'),
            {}
        )
        
        # Generate service endpoint URL using configured base URL
        service_endpoint = f"{settings.service_endpoint_base_url}/{model_id.replace('_', '-')}"
        
        # Compile final report
        final_report = {
            "deployment_conversation_id": state['deployment_conversation_id'],
            "model_id": model_id,
            "deployment_status": "success",
            "deployment_timestamp": datetime.now().isoformat(),
            "service_endpoint": service_endpoint,
            "latency_requirement": state.get('latency_requirement', 'Not specified'),
            "deployment_type": deployment_type,
            "ci_pipeline": {
                "pipeline_id": ci_result.get('result', {}).get('pipeline_id', 'N/A'),
                "github_repository": ci_result.get('result', {}).get('github_repository', 'Not configured'),
                "workflows_created": ci_result.get('result', {}).get('workflows_created', []),
                "workflow_files": ci_result.get('result', {}).get('workflow_files', {}),
                "pipeline_verification": ci_result.get('result', {}).get('pipeline_verification', {})
            },
            "deployment_pipeline": {
                "deployment_id": deployment_result.get('result', {}).get('deployment_id', 'N/A'),
                "argocd_application": deployment_result.get('result', {}).get('argocd_application', 'N/A'),
                "kubernetes_manifests": deployment_result.get('result', {}).get('kubernetes_manifests', {}),
                "container_image": deployment_result.get('result', {}).get('container_image', f"{settings.default_organization}/{model_id}:latest"),
                "argocd_verification": deployment_result.get('result', {}).get('argocd_verification', {}),
                "deployment_status": deployment_result.get('result', {}).get('deployment_status', 'unknown')
            },
            "summary": f"✅ Model {model_id} deployment orchestration complete\n"
                      f"CI Pipeline: {ci_result.get('result', {}).get('pipeline_id', 'N/A')}\n"
                      f"Deployment: {deployment_result.get('result', {}).get('deployment_id', 'N/A')}\n"
                      f"Endpoint: {service_endpoint}\n"
                      f"ArgoCD Status: {deployment_result.get('result', {}).get('argocd_verification', {}).get('overall_status', 'unknown')}",
            "tasks_executed": len(task_results),
            "task_details": task_results
        }
        
        return final_report
