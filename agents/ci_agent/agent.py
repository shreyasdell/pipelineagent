from typing import Dict, Any, Optional, List
import json
import re
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from core.state.models import AgentState
from core.llm.config import get_llm, get_prompt_template
from core.state.persistence import state_manager
from core.config.settings import settings
from tools.github.github_client import GitHubClient
from loguru import logger


class CIAgent:
    """
    CI Agent - Creates GitHub Actions pipelines for CI/CD
    Handles automated testing, building, and deployment workflows
    """
    
    def __init__(self):
        self.llm = get_llm()
        self.github_client = GitHubClient()
        self.system_prompt = """You are a CI/CD Agent for AI model deployment.
Your task is to create GitHub Actions workflows for automated CI/CD pipelines.

You need to:
1. Analyze the deployment requirements and model characteristics
2. Design appropriate CI/CD workflows (build, test, deploy stages)
3. Generate GitHub Actions YAML configurations
4. Consider security best practices, testing requirements, and deployment strategies

Workflow stages to consider:
- Build: Container image building, model artifact preparation
- Test: Model validation, integration tests, security scanning
- Deploy: Staging deployment, production deployment, rollback capabilities
- Monitor: Health checks, performance monitoring, alerting

IMPORTANT: You must respond with a valid JSON object in the following format:
{{
    "reasoning": "<your reasoning about the CI/CD pipeline design>",
    "workflows": [
        {{
            "workflow_name": "<workflow name>",
            "trigger_events": ["push", "pull_request", "manual"],
            "stages": [
                {{
                    "stage_name": "<stage name>",
                    "jobs": [
                        {{
                            "job_name": "<job name>",
                            "description": "<job description>",
                            "steps": [
                                {{
                                    "step_name": "<step name>",
                                    "action": "<GitHub Action or shell command>",
                                    "parameters": {{
                                        "key": "value"
                                    }}
                                }}
                            ]
                        }}
                    ]
                }}
            ]
        }}
    ],
    "security_considerations": ["<security consideration 1>", "<security consideration 2>"],
    "testing_strategy": "<testing strategy description>",
    "deployment_strategy": "<deployment strategy description>"
}}"""
    
    async def create_ci_pipeline(self, state: AgentState) -> AgentState:
        """
        Create CI/CD pipeline for model deployment and save to GitHub repository
        
        Args:
            state: Current agent state with model_id, deployment details, etc.
            
        Returns:
            Updated state with ci_pipeline configuration
        """
        logger.info(f"CI Agent creating pipeline for model: {state['model_id']}")
        
        # Update current agent in state
        state["current_agent"] = "ci_agent"
        
        # Save state to persistence
        state_manager.save_state(
            state["deployment_conversation_id"],
            state,
            "ci_agent"
        )
        
        try:
            # Step 1: Analyze requirements and design pipeline
            logger.info("Analyzing requirements and designing CI/CD pipeline...")
            pipeline_design = await self._design_pipeline(state)
            
            # Step 2: Generate GitHub Actions workflows
            logger.info("Generating GitHub Actions workflows...")
            github_workflows = self._generate_github_workflows(pipeline_design, state)
            
            # Step 3: Save workflows to GitHub repository
            logger.info("Saving workflows to GitHub repository...")
            github_workflow_files = await self._save_workflows_to_github(github_workflows, state)
            
            # Step 4: Verify CI pipeline in GitHub
            logger.info("Verifying CI pipeline in GitHub...")
            pipeline_verification = await self._verify_ci_pipeline_in_github(github_workflows, state)
            
            # Step 5: Compile final CI pipeline configuration
            logger.info("Compiling final CI pipeline configuration...")
            ci_pipeline = await self._compile_ci_pipeline(state, pipeline_design, github_workflows, github_workflow_files, pipeline_verification)
            state["ci_pipeline"] = ci_pipeline
            
            # Add message to conversation
            state["messages"].append(AIMessage(
                content=f"CI/CD pipeline created and saved to GitHub. Workflows: {len(github_workflows)}, Verification: {pipeline_verification.get('overall_status', 'unknown')}"
            ))
            
            # Save updated state
            state_manager.save_state(
                state["deployment_conversation_id"],
                state,
                "ci_agent"
            )
            
            logger.info(f"CI Agent pipeline creation complete for {state['model_id']}")
            
        except Exception as e:
            logger.error(f"Error in CI pipeline creation: {e}")
            state["errors"].append(f"CI Agent error: {str(e)}")
            state["messages"].append(AIMessage(content=f"Error in CI pipeline creation: {str(e)}"))
        
        return state
    
    async def _design_pipeline(self, state: AgentState) -> Dict[str, Any]:
        """
        Design CI/CD pipeline using LLM analysis
        
        Args:
            state: Current agent state
            
        Returns:
            Pipeline design configuration
        """
        # Prepare design prompt
        design_prompt = self._prepare_design_prompt(state)
        
        # Get LLM response
        prompt_template = get_prompt_template(self.system_prompt)
        chain = prompt_template | self.llm
        
        response = await chain.ainvoke({"input": design_prompt})
        
        logger.info(f"Raw LLM response for pipeline design: {response.content[:500]}")
        
        # Parse response into structured design
        pipeline_design = self._parse_pipeline_design(response.content, state)
        
        logger.info(f"Pipeline design complete with {len(pipeline_design.get('workflows', []))} workflows")
        return pipeline_design
    
    def _prepare_design_prompt(self, state: AgentState) -> str:
        """Prepare the pipeline design prompt for the LLM"""
        prompt = f"""
CI/CD Pipeline Requirements:
- Model ID: {state['model_id']}
- Deployment Type: {state.get('deployment_type', 'standard')}
- Latency Requirement: {state.get('latency_requirement', 'Not specified')}
- Deployment Conversation ID: {state['deployment_conversation_id']}
"""
        
        # Add constraint resolver report if available
        if state.get("constraint_resolver_report"):
            prompt += f"""
Model Characteristics:
- Recommended Engine: {state['constraint_resolver_report'].get('engine_type', 'N/A')}
- Weight Format: {state['constraint_resolver_report'].get('weight_format', 'N/A')}
- Quantization Options: {state['constraint_resolver_report'].get('quantization_levels_possible', [])}
- Parallelization: {state['constraint_resolver_report'].get('parallelization_possible', {})}
"""
        
        # Add infrastructure details if available
        if state.get("infrastructure_details"):
            prompt += f"""
Infrastructure Details:
{self._format_infrastructure_details(state.get('infrastructure_details', {}))}
"""
        
        # Add GitHub repository information if available
        if settings.github_repo:
            prompt += f"""
GitHub Repository: {settings.github_repo}
"""
        
        prompt += """
Please design a comprehensive CI/CD pipeline that includes:
1. Automated building and testing
2. Security scanning and validation
3. Staging and production deployment
4. Monitoring and rollback capabilities

Consider the model characteristics and infrastructure constraints when designing the pipeline.
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
    
    def _parse_pipeline_design(self, llm_response: str, state: AgentState) -> Dict[str, Any]:
        """
        Parse LLM response into structured pipeline design
        
        Args:
            llm_response: Raw LLM response
            state: Current agent state
            
        Returns:
            Parsed pipeline design
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
                    # Fallback to default pipeline design
                    logger.warning("No JSON found in LLM response, using default pipeline design")
                    return self._create_default_pipeline_design(state)
            
            # Validate and structure the parsed data
            return {
                "reasoning": parsed_data.get("reasoning", "Standard CI/CD pipeline design"),
                "workflows": parsed_data.get("workflows", []),
                "security_considerations": parsed_data.get("security_considerations", []),
                "testing_strategy": parsed_data.get("testing_strategy", "Standard testing approach"),
                "deployment_strategy": parsed_data.get("deployment_strategy", "Standard deployment approach")
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return self._create_default_pipeline_design(state)
        except Exception as e:
            logger.error(f"Error parsing pipeline design: {e}")
            return self._create_default_pipeline_design(state)
    
    def _create_default_pipeline_design(self, state: AgentState) -> Dict[str, Any]:
        """
        Create default pipeline design when LLM parsing fails
        
        Args:
            state: Current agent state
            
        Returns:
            Default pipeline design
        """
        deployment_type = state.get('deployment_type', 'standard')
        
        return {
            "reasoning": f"Standard CI/CD pipeline for {deployment_type} deployment of {state['model_id']}",
            "workflows": [
                {
                    "workflow_name": "build-and-test",
                    "trigger_events": ["push", "pull_request"],
                    "stages": [
                        {
                            "stage_name": "build",
                            "jobs": [
                                {
                                    "job_name": "build-container",
                                    "description": "Build container image for model",
                                    "steps": [
                                        {
                                            "step_name": "checkout",
                                            "action": "actions/checkout@v3",
                                            "parameters": {}
                                        },
                                        {
                                            "step_name": "build-image",
                                            "action": "docker/build-push-action@v5",
                                            "parameters": {
                                                "context": ".",
                                                "push": False,
                                                "tags": f"{settings.default_organization}/{state['model_id']}:latest"
                                            }
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "stage_name": "test",
                            "jobs": [
                                {
                                    "job_name": "model-validation",
                                    "description": "Validate model artifacts and configuration",
                                    "steps": [
                                        {
                                            "step_name": "run-tests",
                                            "action": "shell",
                                            "parameters": {
                                                "command": "python -m pytest tests/"
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    "workflow_name": "deploy",
                    "trigger_events": ["push", "workflow_dispatch"],
                    "stages": [
                        {
                            "stage_name": "deploy-staging",
                            "jobs": [
                                {
                                    "job_name": "deploy-to-staging",
                                    "description": "Deploy model to staging environment",
                                    "steps": [
                                        {
                                            "step_name": "deploy",
                                            "action": "shell",
                                            "parameters": {
                                                "command": f"kubectl apply -f deployment/staging/{state['model_id']}.yaml"
                                            }
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "stage_name": "deploy-production",
                            "jobs": [
                                {
                                    "job_name": "deploy-to-production",
                                    "description": "Deploy model to production environment",
                                    "steps": [
                                        {
                                            "step_name": "deploy",
                                            "action": "shell",
                                            "parameters": {
                                                "command": f"kubectl apply -f deployment/production/{state['model_id']}.yaml"
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            "security_considerations": [
                "Use GitHub Secrets for sensitive credentials",
                "Implement container vulnerability scanning",
                "Enable branch protection rules",
                "Use signed commits and tags"
            ],
            "testing_strategy": "Automated testing with unit tests, integration tests, and model validation",
            "deployment_strategy": f"{deployment_type} deployment with automated rollback capabilities"
        }
    
    def _generate_github_workflows(self, pipeline_design: Dict[str, Any], state: AgentState) -> Dict[str, str]:
        """
        Generate GitHub Actions YAML workflows from pipeline design
        
        Args:
            pipeline_design: Pipeline design configuration
            state: Current agent state
            
        Returns:
            Dictionary mapping workflow names to YAML content
        """
        workflows = {}
        model_id = state['model_id']
        
        for workflow in pipeline_design.get('workflows', []):
            workflow_name = workflow['workflow_name']
            yaml_content = self._generate_workflow_yaml(workflow, model_id)
            workflows[workflow_name] = yaml_content
        
        logger.info(f"Generated {len(workflows)} GitHub Actions workflows")
        return workflows
    
    def _generate_workflow_yaml(self, workflow: Dict[str, Any], model_id: str) -> str:
        """
        Generate GitHub Actions YAML for a single workflow
        
        Args:
            workflow: Workflow configuration
            model_id: Model identifier
            
        Returns:
            YAML content for the workflow
        """
        yaml_lines = []
        
        # Workflow header
        yaml_lines.append(f"name: {workflow['workflow_name']}")
        yaml_lines.append("")
        
        # Triggers
        yaml_lines.append("on:")
        for trigger in workflow.get('trigger_events', ['push']):
            if trigger == 'push':
                yaml_lines.append("  push:")
                yaml_lines.append("    branches: [ main, develop ]")
            elif trigger == 'pull_request':
                yaml_lines.append("  pull_request:")
                yaml_lines.append("    branches: [ main ]")
            elif trigger == 'workflow_dispatch':
                yaml_lines.append("  workflow_dispatch:")
        yaml_lines.append("")
        
        # Jobs
        yaml_lines.append("jobs:")
        
        for stage in workflow.get('stages', []):
            for job in stage.get('jobs', []):
                job_name = job['job_name']
                yaml_lines.append(f"  {job_name}:")
                yaml_lines.append(f"    runs-on: ubuntu-latest")
                yaml_lines.append("")
                yaml_lines.append("    steps:")
                
                for step in job.get('steps', []):
                    step_name = step['step_name']
                    action = step['action']
                    parameters = step.get('parameters', {})
                    
                    yaml_lines.append(f"      - name: {step_name}")
                    
                    if action == 'shell':
                        yaml_lines.append("        run: |")
                        command = parameters.get('command', 'echo "No command specified"')
                        for line in command.split('\n'):
                            yaml_lines.append(f"          {line}")
                    elif action.startswith('actions/'):
                        yaml_lines.append(f"        uses: {action}")
                        if parameters:
                            yaml_lines.append("        with:")
                            for key, value in parameters.items():
                                yaml_lines.append(f"          {key}: {value}")
                    else:
                        yaml_lines.append(f"        uses: {action}")
                        if parameters:
                            yaml_lines.append("        with:")
                            for key, value in parameters.items():
                                yaml_lines.append(f"          {key}: {value}")
                
                yaml_lines.append("")
        
        return '\n'.join(yaml_lines)
    
    async def _save_workflows_to_github(self, github_workflows: Dict[str, str], state: AgentState) -> Dict[str, Any]:
        """
        Save generated workflows to GitHub repository
        
        Args:
            github_workflows: Dictionary of workflow names to YAML content
            state: Current agent state
            
        Returns:
            Dictionary of workflow file creation results
        """
        workflow_files = {}
        
        if not settings.github_repo:
            logger.warning("GitHub repository not configured - skipping workflow file creation")
            for workflow_name in github_workflows.keys():
                workflow_files[workflow_name] = {
                    "status": "skipped",
                    "message": "GitHub repository not configured",
                    "file_path": f".github/workflows/{workflow_name}.yaml"
                }
            return workflow_files
        
        try:
            # Create a feature branch for CI pipeline changes
            branch_name = f"ci-pipeline-{state['model_id']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                self.github_client.create_branch(branch_name)
                logger.info(f"Created branch: {branch_name}")
            except Exception as e:
                logger.warning(f"Could not create branch {branch_name}: {e}, using main branch")
                branch_name = "main"
            
            # Save each workflow file
            for workflow_name, yaml_content in github_workflows.items():
                try:
                    result = self.github_client.create_workflow_file(
                        workflow_name=workflow_name,
                        workflow_content=yaml_content,
                        branch=branch_name
                    )
                    
                    workflow_files[workflow_name] = {
                        "status": "created",
                        "message": "Workflow file created successfully",
                        "file_path": f".github/workflows/{workflow_name}.yaml",
                        "branch": branch_name,
                        "commit_url": result.get("content", {}).get("html_url"),
                        "sha": result.get("content", {}).get("sha")
                    }
                    logger.info(f"Workflow file {workflow_name}.yaml created successfully")
                    
                except Exception as e:
                    logger.error(f"Failed to create workflow file {workflow_name}.yaml: {e}")
                    workflow_files[workflow_name] = {
                        "status": "failed",
                        "message": f"Failed to create workflow file: {str(e)}",
                        "file_path": f".github/workflows/{workflow_name}.yaml",
                        "error": str(e)
                    }
            
            # Create pull request if we used a feature branch
            if branch_name != "main":
                try:
                    pr = self.github_client.create_pull_request(
                        title=f"Add CI/CD pipeline for {state['model_id']}",
                        head=branch_name,
                        base="main",
                        body=f"This PR adds GitHub Actions workflows for CI/CD pipeline of model {state['model_id']}\n\n"
                             f"Workflows added:\n" + 
                             "\n".join([f"- {name}" for name in github_workflows.keys()])
                    )
                    logger.info(f"Pull request created: {pr.get('html_url')}")
                    
                    # Add PR info to workflow files
                    for workflow_name in workflow_files:
                        workflow_files[workflow_name]["pull_request"] = {
                            "url": pr.get("html_url"),
                            "number": pr.get("number"),
                            "state": pr.get("state")
                        }
                        
                except Exception as e:
                    logger.warning(f"Could not create pull request: {e}")
            
        except Exception as e:
            logger.error(f"Error saving workflows to GitHub: {e}")
            for workflow_name in github_workflows.keys():
                workflow_files[workflow_name] = {
                    "status": "error",
                    "message": f"Error saving to GitHub: {str(e)}",
                    "file_path": f".github/workflows/{workflow_name}.yaml",
                    "error": str(e)
                }
        
        return workflow_files
    
    async def _verify_ci_pipeline_in_github(self, github_workflows: Dict[str, str], state: AgentState) -> Dict[str, Any]:
        """
        Verify CI pipeline status in GitHub repository
        
        Args:
            github_workflows: Dictionary of workflow names to YAML content
            state: Current agent state
            
        Returns:
            Verification results for all workflows
        """
        verification_results = {}
        
        if not settings.github_repo:
            logger.warning("GitHub repository not configured - skipping pipeline verification")
            return {
                "overall_status": "skipped",
                "message": "GitHub repository not configured",
                "workflow_verifications": {}
            }
        
        try:
            for workflow_name in github_workflows.keys():
                try:
                    verification = self.github_client.verify_ci_pipeline(workflow_name)
                    verification_results[workflow_name] = verification
                    logger.info(f"Workflow {workflow_name} verification: {verification['status']}")
                except Exception as e:
                    logger.error(f"Failed to verify workflow {workflow_name}: {e}")
                    verification_results[workflow_name] = {
                        "verified": False,
                        "status": "error",
                        "message": f"Verification failed: {str(e)}",
                        "error": str(e)
                    }
            
            # Determine overall status
            all_verified = all(v.get("verified", False) for v in verification_results.values())
            any_errors = any(v.get("status") == "error" for v in verification_results.values())
            
            if all_verified:
                overall_status = "success"
                message = "All workflows verified successfully"
            elif any_errors:
                overall_status = "error"
                message = "Some workflows encountered errors during verification"
            else:
                overall_status = "partial"
                message = "Some workflows not yet verified (no runs or in progress)"
            
            return {
                "overall_status": overall_status,
                "message": message,
                "workflow_verifications": verification_results,
                "github_repository": settings.github_repo
            }
            
        except Exception as e:
            logger.error(f"Error verifying CI pipeline in GitHub: {e}")
            return {
                "overall_status": "error",
                "message": f"Error during verification: {str(e)}",
                "error": str(e),
                "workflow_verifications": verification_results
            }
    
    async def _compile_ci_pipeline(self, state: AgentState, pipeline_design: Dict[str, Any], github_workflows: Dict[str, str], github_workflow_files: Dict[str, Any], pipeline_verification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compile final CI pipeline configuration
        
        Args:
            state: Current agent state
            pipeline_design: Pipeline design configuration
            github_workflows: Generated GitHub Actions workflows
            github_workflow_files: Results of saving workflows to GitHub
            pipeline_verification: Verification results from GitHub
            
        Returns:
            Final CI pipeline configuration
        """
        model_id = state['model_id']
        
        ci_pipeline = {
            "pipeline_id": f"ci-{model_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "model_id": model_id,
            "created_at": datetime.now().isoformat(),
            "pipeline_design": {
                "reasoning": pipeline_design.get('reasoning'),
                "testing_strategy": pipeline_design.get('testing_strategy'),
                "deployment_strategy": pipeline_design.get('deployment_strategy'),
                "security_considerations": pipeline_design.get('security_considerations', [])
            },
            "github_workflows": github_workflows,
            "github_workflow_files": github_workflow_files,
            "pipeline_verification": pipeline_verification,
            "configuration": {
                "github_repository": settings.github_repo or "Not configured",
                "default_branch": "main",
                "environments": ["staging", "production"],
                "secrets_required": [
                    "DOCKER_REGISTRY_USERNAME",
                    "DOCKER_REGISTRY_PASSWORD",
                    "KUBE_CONFIG",
                    "API_ENDPOINT"
                ]
            },
            "next_steps": self._generate_next_steps(github_workflow_files, pipeline_verification),
            "status": self._determine_pipeline_status(github_workflow_files, pipeline_verification)
        }
        
        return ci_pipeline
    
    def _generate_next_steps(self, github_workflow_files: Dict[str, Any], pipeline_verification: Dict[str, Any]) -> List[str]:
        """Generate next steps based on workflow file creation and verification status"""
        next_steps = []
        
        # Check if GitHub is configured
        if not settings.github_repo:
            next_steps.extend([
                "Configure GitHub repository in settings",
                "Set up GitHub personal access token",
                "Re-run CI Agent to save workflows to GitHub"
            ])
            return next_steps
        
        # Check workflow file creation status
        created_files = [name for name, result in github_workflow_files.items() if result.get("status") == "created"]
        failed_files = [name for name, result in github_workflow_files.items() if result.get("status") in ["failed", "error"]]
        
        if created_files:
            next_steps.append(f"Review created workflow files: {', '.join(created_files)}")
        
        if failed_files:
            next_steps.append(f"Fix failed workflow files: {', '.join(failed_files)}")
        
        # Check if PR was created
        has_pr = any(result.get("pull_request") for result in github_workflow_files.values())
        if has_pr:
            next_steps.append("Review and merge the pull request for CI pipeline")
        else:
            next_steps.append("Merge workflow files to main branch")
        
        # Check verification status
        if pipeline_verification.get("overall_status") == "success":
            next_steps.append("CI pipeline verified successfully - ready for use")
        elif pipeline_verification.get("overall_status") == "partial":
            next_steps.append("Trigger workflows manually to verify functionality")
        elif pipeline_verification.get("overall_status") == "error":
            next_steps.append("Review verification errors and fix workflow configurations")
        
        # Standard next steps
        next_steps.extend([
            "Configure GitHub Secrets for credentials",
            "Enable branch protection rules",
            "Test workflows with sample commits"
        ])
        
        return next_steps
    
    def _determine_pipeline_status(self, github_workflow_files: Dict[str, Any], pipeline_verification: Dict[str, Any]) -> str:
        """Determine overall pipeline status based on file creation and verification"""
        if not settings.github_repo:
            return "github_not_configured"
        
        # Check if any files failed to create
        if any(result.get("status") in ["failed", "error"] for result in github_workflow_files.values()):
            return "creation_failed"
        
        # Check verification status
        verification_status = pipeline_verification.get("overall_status")
        if verification_status == "success":
            return "verified_and_ready"
        elif verification_status == "partial":
            return "created_pending_verification"
        elif verification_status == "error":
            return "verification_failed"
        
        return "created"
