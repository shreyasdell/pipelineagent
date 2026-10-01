from typing import Dict, Any, Optional, List
import json
import re
import yaml
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from core.state.models import AgentState
from core.llm.config import get_llm, get_prompt_template
from core.state.persistence import state_manager
from core.config.settings import settings
from tools.argocd.argocd_client import ArgoCDClient
from tools.huggingface.huggingface_client import HuggingFaceClient
from tools.gitops.github_manifest_manager import GitHubManifestManager
from loguru import logger
import os
from kubernetes import client, config


class KubernetesDeploymentAgent:
    """
    Kubernetes Deployment Agent - Handles Kubernetes deployment for vLLM serving
    Manages MicroK8s deployment, manifest generation, and ArgoCD integration
    """
    
    def __init__(self):
        self.llm = get_llm()
        self.argocd_client = ArgoCDClient()
        self.huggingface_client = HuggingFaceClient()
        self.github_manifest_manager = GitHubManifestManager()
        self._init_kubernetes_client()
        self.system_prompt = """You are a Kubernetes Deployment Agent for AI model deployment.
Your task is to handle Kubernetes deployment for vLLM serving on MicroK8s.

You need to:
1. Analyze deployment requirements and infrastructure details
2. Design Kubernetes deployment configuration for vLLM serving
3. Generate Kubernetes manifests (Deployment, Service, ConfigMap)
4. Create ArgoCD application configuration when available
5. Verify deployment status and health indicators

IMPORTANT: You must respond with a valid JSON object in the following format:
{{
    "reasoning": "<your reasoning about the Kubernetes deployment design>",
    "kubernetes_configuration": {{
        "namespace": "<target namespace>",
        "deployment_name": "<deployment name>",
        "service_name": "<service name>",
        "replicas": <number>,
        "gpu_requirements": {{
            "enabled": <boolean>,
            "gpu_type": "<GPU type>",
            "gpu_memory_gb": <memory in GB>,
            "nvidia_device_plugin": <boolean>
        }},
        "vllm_configuration": {{
            "model_path": "<model path>",
            "model_id": "<model ID>",
            "port": <port number>,
            "gpu_memory_utilization": <percentage>,
            "max_model_len": <context length>,
            "tensor_parallel_size": <number>
        }},
        "resource_requirements": {{
            "cpu": "<CPU request>",
            "memory": "<memory request>",
            "gpu": "<GPU count>"
        }}
    }}
}}
"""
        logger.info("Kubernetes Deployment Agent initialized")
    
    def _init_kubernetes_client(self):
        """Initialize Kubernetes client from kubeconfig"""
        try:
            # Set KUBECONFIG environment variable
            os.environ['KUBECONFIG'] = settings.kubeconfig_path
            
            # Load kubeconfig with explicit file path
            config.load_kube_config(config_file=settings.kubeconfig_path)
            
            # Initialize API clients
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.custom_objects_api = client.CustomObjectsApi()
            
            logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            self.core_v1 = None
            self.apps_v1 = None
            self.custom_objects_api = None
    
    def _check_kubernetes_api(self) -> Dict[str, Any]:
        """Check Kubernetes API connectivity using Kubernetes Python client"""
        try:
            if self.core_v1 is None:
                return {
                    "available": False,
                    "error": "Kubernetes client not initialized"
                }
            
            # Test API connectivity by listing nodes
            nodes = self.core_v1.list_node()
            
            return {
                "available": True,
                "node_count": len(nodes.items),
                "nodes": [{"name": node.metadata.name, "status": node.status.phase} for node in nodes.items]
            }
        except Exception as e:
            logger.error(f"Kubernetes API check failed: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    def _check_kubectl_cli(self) -> Dict[str, Any]:
        """Check kubectl CLI availability (fallback)"""
        try:
            import subprocess
            result = subprocess.run(["kubectl", "version", "--client"], capture_output=True, text=True)
            if result.returncode == 0:
                return {
                    "available": True,
                    "version": result.stdout.strip()
                }
            else:
                return {
                    "available": False,
                    "error": result.stderr
                }
        except FileNotFoundError:
            return {
                "available": False,
                "error": "kubectl command not found"
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    def _check_gpu_host(self) -> Dict[str, Any]:
        """Check GPU availability on host"""
        try:
            import subprocess
            result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
            if result.returncode == 0:
                # Parse GPU info
                lines = result.stdout.split('\n')
                gpu_info = {}
                for line in lines:
                    if 'NVIDIA' in line and 'Driver Version' in line:
                        gpu_info['driver'] = line.split('Driver Version:')[1].split()[0]
                    if 'GPU Name' in line:
                        gpu_info['name'] = line.split('GPU Name:')[1].split('|')[0].strip()
                
                return {
                    "available": True,
                    "info": gpu_info
                }
            else:
                return {
                    "available": False,
                    "error": result.stderr
                }
        except FileNotFoundError:
            return {
                "available": False,
                "error": "nvidia-smi command not found"
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    def _check_gpu_kubernetes(self) -> Dict[str, Any]:
        """Check GPU availability in Kubernetes via API"""
        try:
            if self.core_v1 is None:
                return {
                    "available": False,
                    "error": "Kubernetes client not initialized"
                }
            
            # Check for nvidia-device-plugin pods or gpu-operator
            gpu_pods = []
            
            # Check kube-system for nvidia-device-plugin
            try:
                pods = self.core_v1.list_namespaced_pod("kube-system")
                nvidia_pods = [pod for pod in pods.items if 'nvidia' in pod.metadata.name.lower()]
                gpu_pods.extend(nvidia_pods)
            except Exception:
                pass
            
            # Check gpu-operator-resources namespace
            try:
                pods = self.core_v1.list_namespaced_pod("gpu-operator-resources")
                gpu_pods.extend(pods.items)
            except Exception:
                pass
            
            # Check for runtime classes
            runtime_classes = []
            try:
                from kubernetes import client as k8s_client
                api = k8s_client.NodeV1Api()
                rcs = api.list_runtime_class()
                runtime_classes = [rc.metadata.name for rc in rcs.items if 'nvidia' in rc.metadata.name.lower()]
            except Exception:
                pass
            
            # Check nodes for GPU resources (traditional nvidia.com/gpu)
            nodes = self.core_v1.list_node()
            gpu_nodes = []
            for node in nodes.items:
                if node.status.allocatable and 'nvidia.com/gpu' in node.status.allocatable:
                    gpu_nodes.append({
                        "name": node.metadata.name,
                        "gpu_count": node.status.allocatable['nvidia.com/gpu']
                    })
            
            # Check for GPU runtime test pod
            gpu_available = False
            gpu_method = None
            
            if gpu_nodes:
                gpu_available = True
                gpu_method = "nvidia.com/gpu resource"
            elif runtime_classes:
                gpu_available = True
                gpu_method = "runtime class"
            elif gpu_pods:
                gpu_available = True
                gpu_method = "GPU operator"
            
            return {
                "available": gpu_available,
                "method": gpu_method,
                "nvidia_pods": len(gpu_pods),
                "gpu_nodes": gpu_nodes,
                "runtime_classes": runtime_classes
            }
        except Exception as e:
            logger.error(f"Kubernetes GPU check failed: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    def _check_vllm(self) -> Dict[str, Any]:
        """Check vLLM availability"""
        try:
            import vllm
            return {
                "available": True,
                "version": vllm.__version__
            }
        except ImportError:
            return {
                "available": False,
                "error": "vllm package not installed"
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    def _check_huggingface(self) -> Dict[str, Any]:
        """Check Hugging Face connectivity"""
        try:
            # Test with a simple model info request
            model_info = self.huggingface_client.get_model_info("Qwen/Qwen2.5-7B")
            if model_info:
                return {
                    "available": True,
                    "model_info": model_info
                }
            else:
                return {
                    "available": False,
                    "error": "Failed to retrieve model info"
                }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    async def check_infrastructure(self, state: AgentState) -> AgentState:
        """Check all infrastructure prerequisites"""
        logger.info("Checking infrastructure prerequisites...")
        
        results = {
            "kubernetes_api": self._check_kubernetes_api(),
            "kubectl_cli": self._check_kubectl_cli(),
            "gpu_host": self._check_gpu_host(),
            "gpu_kubernetes": self._check_gpu_kubernetes(),
            "vllm": self._check_vllm(),
            "huggingface": self._check_huggingface()
        }
        
        # Update state
        state["infrastructure_available"] = results
        state["infrastructure_details"] = {
            "kubernetes_available": results["kubernetes_api"].get("available", False),
            "gpu_available": results["gpu_kubernetes"].get("available", False),
            "vllm_available": results["vllm"].get("available", False),
            "huggingface_available": results["huggingface"].get("available", False)
        }
        
        logger.info(f"Infrastructure check results: {results}")
        return state
    
    async def design_deployment(self, state: AgentState) -> AgentState:
        """Design Kubernetes deployment using LLM"""
        logger.info("Designing Kubernetes deployment...")
        
        # Get infrastructure details
        infrastructure = state.get("infrastructure_available", {})
        infrastructure_details = state.get("infrastructure_details", {})
        
        # Build prompt
        prompt = f"""
Design a Kubernetes deployment for vLLM serving with the following requirements:

Model ID: {state['model_id']}
Latency Requirement: {state.get('latency_requirement', 'not specified')}
Deployment Type: {state.get('deployment_type', 'standard')}

Infrastructure Details:
- Kubernetes Available: {infrastructure_details.get('kubernetes_available', False)}
- GPU Available: {infrastructure_details.get('gpu_available', False)}
- vLLM Available: {infrastructure_details.get('vllm_available', False)}
- Hugging Face Available: {infrastructure_details.get('huggingface_available', False)}

GPU Information: {infrastructure.get('gpu_host', {})}
Kubernetes GPU Information: {infrastructure.get('gpu_kubernetes', {})}

Constraint Resolver Report: {state.get('constraint_resolver_report', 'Not available')}

{{
    "reasoning": "<your reasoning about the Kubernetes deployment design>",
    "kubernetes_configuration": {{
        "namespace": "<target namespace>",
        "deployment_name": "<deployment name>",
        "service_name": "<service name>",
        "replicas": <number>,
        "gpu_requirements": {{
            "enabled": <boolean>,
            "gpu_type": "<GPU type>",
            "gpu_memory_gb": <memory in GB>,
            "nvidia_device_plugin": <boolean>
        }},
        "vllm_configuration": {{
            "model_path": "<model path>",
            "model_id": "<model ID>",
            "port": <port number>,
            "gpu_memory_utilization": <percentage>,
            "max_model_len": <context length>,
            "tensor_parallel_size": <number>
        }},
        "resource_requirements": {{
            "cpu": "<CPU requests>",
            "memory": "<memory requests>",
            "gpu": "<GPU requests>"
        }}
    }}
}}"""
    
    async def create_kubernetes_deployment(self, state: AgentState) -> AgentState:
        """
        Create Kubernetes deployment for model deployment
        
        Args:
            state: Current agent state with model_id, deployment details, etc.
            
        Returns:
            Updated state with kubernetes_deployment_report
        """
        logger.info(f"Kubernetes Deployment Agent creating deployment for model: {state['model_id']}")
        
        # Update current agent in state
        state["current_agent"] = "kubernetes_deployment_agent"
        
        # Save state to persistence
        state_manager.save_state(
            state["deployment_conversation_id"],
            state,
            "kubernetes_deployment_agent"
        )
        
        try:
            # Step 1: Check infrastructure prerequisites
            logger.info("Checking infrastructure prerequisites...")
            infrastructure_check = await self._check_infrastructure_prerequisites()
            state["infrastructure_available"] = infrastructure_check
            
            # Step 2: Analyze requirements and design deployment
            logger.info("Analyzing requirements and designing Kubernetes deployment...")
            k8s_design = await self._design_kubernetes_deployment(state)
            
            # Step 3: Generate Kubernetes manifests
            logger.info("Generating Kubernetes manifests...")
            kubernetes_manifests = self._generate_kubernetes_manifests(k8s_design, state)
            state["kubernetes_manifests"] = kubernetes_manifests
            
            # Step 4: Commit manifests to GitHub (GitOps)
            logger.info("Committing manifests to GitHub repository...")
            gitops_result = await self._commit_to_github(kubernetes_manifests, state)
            state["gitops_commit_sha"] = gitops_result.get("commit_sha")
            state["gitops_branch"] = gitops_result.get("branch")
            state["gitops_repository"] = gitops_result.get("repository")
            
            # Step 5: Create ArgoCD application
            logger.info("Creating ArgoCD application...")
            argocd_result = await self._create_argocd_application(kubernetes_manifests, state)
            state["argocd_application"] = argocd_result
            
            # Step 6: Trigger ArgoCD sync
            logger.info("Triggering ArgoCD sync...")
            sync_result = await self._sync_argocd_application(state)
            state["argocd_sync_status"] = sync_result.get("status")
            
            # Step 7: Verify deployment status
            logger.info("Verifying deployment status...")
            deployment_verification = await self._verify_argocd_deployment(state)
            state["argocd_status"] = deployment_verification
            
            # Step 8: Compile final Kubernetes deployment report
            logger.info("Compiling final Kubernetes deployment report...")
            k8s_report = await self._compile_kubernetes_report(state, k8s_design, kubernetes_manifests, gitops_result, argocd_result, sync_result, deployment_verification)
            state["kubernetes_deployment_report"] = k8s_report
            
            # Add message to conversation
            state["messages"].append(AIMessage(
                content=f"Kubernetes deployment created successfully. Deployment status: {deployment_verification.get('overall_status', 'unknown')}"
            ))
            
            # Save updated state
            state_manager.save_state(
                state["deployment_conversation_id"],
                state,
                "kubernetes_deployment_agent"
            )
            
            logger.info(f"Kubernetes Deployment Agent complete for {state['model_id']}")
            
        except Exception as e:
            logger.error(f"Error in Kubernetes deployment creation: {e}")
            state["errors"].append(f"Kubernetes Deployment Agent error: {str(e)}")
            state["messages"].append(AIMessage(content=f"Error in Kubernetes deployment creation: {str(e)}"))
        
        return state
    
    async def _check_infrastructure_prerequisites(self) -> Dict[str, bool]:
        """
        Check infrastructure prerequisites for Kubernetes deployment
        
        Returns:
            Dictionary of infrastructure availability status
        """
        infrastructure_status = {
            "microk8s": False,
            "kubectl": False,
            "gpu": False,
            "argocd": False,
            "huggingface": False
        }
        
        # Use API-based checks instead of subprocess
        infrastructure_status["kubectl"] = self._check_kubectl_cli().get("available", False)
        infrastructure_status["microk8s"] = self._check_kubernetes_api().get("available", False)
        infrastructure_status["gpu"] = self._check_gpu_host().get("available", False)
        
        try:
            # Check ArgoCD
            if settings.argocd_url:
                infrastructure_status["argocd"] = True
                logger.info("ArgoCD configured")
            else:
                logger.warning("ArgoCD not configured")
        except:
            logger.warning("ArgoCD not available")
        
        try:
            # Check Hugging Face connectivity
            model_info = self.huggingface_client.get_model_info("Qwen/Qwen2.5-7B")
            infrastructure_status["huggingface"] = True
            logger.info("Hugging Face accessible")
        except:
            logger.warning("Hugging Face not accessible")
        
        return infrastructure_status
    
    async def _design_kubernetes_deployment(self, state: AgentState) -> Dict[str, Any]:
        """
        Design Kubernetes deployment using LLM analysis
        
        Args:
            state: Current agent state
            
        Returns:
            Kubernetes deployment design configuration
        """
        # Prepare design prompt
        design_prompt = self._prepare_design_prompt(state)
        
        # Get LLM response
        prompt_template = get_prompt_template(self.system_prompt)
        chain = prompt_template | self.llm
        
        response = await chain.ainvoke({"input": design_prompt})
        
        logger.info(f"Raw LLM response for Kubernetes deployment design: {response.content[:500]}")
        
        # Parse response into structured design
        k8s_design = self._parse_kubernetes_design(response.content, state)
        
        logger.info(f"Kubernetes deployment design complete")
        return k8s_design
    
    def _prepare_design_prompt(self, state: AgentState) -> str:
        """Prepare the Kubernetes deployment design prompt for the LLM"""
        prompt = f"""
Kubernetes Deployment Requirements:
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
        
        # Add infrastructure availability
        if state.get("infrastructure_available"):
            infra = state['infrastructure_available']
            prompt += f"""
Infrastructure Availability:
- MicroK8s: {'✅ Available' if infra.get('microk8s') else '❌ Not available'}
- kubectl: {'✅ Available' if infra.get('kubectl') else '❌ Not available'}
- GPU: {'✅ Available' if infra.get('gpu') else '❌ Not available'}
- ArgoCD: {'✅ Available' if infra.get('argocd') else '❌ Not available'}
- Hugging Face: {'✅ Available' if infra.get('huggingface') else '❌ Not available'}
"""
        
        prompt += """
Please design a comprehensive Kubernetes deployment that includes:
1. Namespace configuration
2. vLLM deployment with GPU support
3. Service configuration for endpoint exposure
4. Resource requirements (CPU, memory, GPU)
5. Health check configuration
6. ConfigMap for vLLM configuration

Consider the model characteristics, infrastructure constraints, and serving requirements.
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
    
    def _parse_kubernetes_design(self, llm_response: str, state: AgentState) -> Dict[str, Any]:
        """
        Parse LLM response into structured Kubernetes deployment design
        
        Args:
            llm_response: Raw LLM response
            state: Current agent state
            
        Returns:
            Parsed Kubernetes deployment design
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
                    # Fallback to default design
                    logger.warning("No JSON found in LLM response, using default Kubernetes design")
                    return self._create_default_kubernetes_design(state)
            
            # Validate and structure the parsed data
            return {
                "reasoning": parsed_data.get("reasoning", "Standard Kubernetes deployment design"),
                "kubernetes_configuration": parsed_data.get("kubernetes_configuration", {})
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return self._create_default_kubernetes_design(state)
        except Exception as e:
            logger.error(f"Error parsing Kubernetes design: {e}")
            return self._create_default_kubernetes_design(state)
    
    def _create_default_kubernetes_design(self, state: AgentState) -> Dict[str, Any]:
        """
        Create default Kubernetes deployment design when LLM parsing fails
        
        Args:
            state: Current agent state
            
        Returns:
            Default Kubernetes deployment design
        """
        model_id = state['model_id']
        safe_model_id = model_id.replace('_', '-').replace('/', '-')
        
        # Calculate resources based on infrastructure
        resource_requirements = self._calculate_resource_requirements(state)
        
        return {
            "reasoning": f"Standard Kubernetes deployment for {model_id} using vLLM",
            "kubernetes_configuration": {
                "namespace": settings.default_namespace,
                "deployment_name": safe_model_id,
                "service_name": safe_model_id,
                "replicas": settings.default_replicas,
                "gpu_requirements": {
                    "enabled": resource_requirements.get("gpu_enabled", True),
                    "gpu_type": resource_requirements.get("gpu_type", "NVIDIA"),
                    "gpu_memory_gb": resource_requirements.get("gpu_memory_gb", 8),
                    "nvidia_device_plugin": resource_requirements.get("gpu_enabled", True)
                },
                "vllm_configuration": {
                    "model_path": f"{settings.default_model_path_prefix}/{safe_model_id}",
                    "model_id": model_id,
                    "port": settings.default_service_port,
                    "gpu_memory_utilization": settings.default_gpu_memory_utilization,
                    "max_model_len": settings.default_max_model_len,
                    "tensor_parallel_size": settings.default_tensor_parallel_size
                },
                "resource_requirements": {
                    "cpu": resource_requirements.get("cpu", settings.default_cpu_request),
                    "memory": resource_requirements.get("memory", settings.default_memory_request),
                    "gpu": str(resource_requirements.get("gpu_count", 1))
                }
            }
        }
    
    def _calculate_resource_requirements(self, state: AgentState) -> Dict[str, Any]:
        """
        Calculate resource requirements based on infrastructure and model
        
        Args:
            state: Current agent state with infrastructure details
            
        Returns:
            Calculated resource requirements
        """
        infrastructure = state.get('infrastructure_details', {})
        infrastructure_available = state.get('infrastructure_available', {})
        
        # Get GPU information from infrastructure
        gpu_enabled = infrastructure_available.get('gpu', {}).get('available', False)
        gpu_type = infrastructure_available.get('gpu', {}).get('details', 'NVIDIA')
        gpu_memory_gb = 8  # Default, could be derived from actual GPU
        
        # Calculate CPU based on model size (simplified for Phase 1)
        # In future, this would use actual model size from Hugging Face
        cpu_cores = infrastructure.get('cpu_cores', 4)
        cpu_request = str(max(2, cpu_cores // 2))
        
        # Calculate memory based on available RAM and GPU
        ram_gb = infrastructure.get('ram_gb', 16)
        memory_request = str(max(8, ram_gb // 2)) + 'Gi'
        
        # GPU count
        gpu_count = infrastructure.get('gpu_count', 1)
        
        return {
            "cpu": cpu_request,
            "memory": memory_request,
            "gpu_enabled": gpu_enabled,
            "gpu_type": gpu_type,
            "gpu_memory_gb": gpu_memory_gb,
            "gpu_count": gpu_count
        }
    
    def _generate_kubernetes_manifests(self, k8s_design: Dict[str, Any], state: AgentState) -> Dict[str, str]:
        """
        Generate Kubernetes manifests for vLLM deployment
        
        Args:
            k8s_design: Kubernetes deployment design configuration
            state: Current agent state
            
        Returns:
            Dictionary of Kubernetes manifests
        """
        model_id = state['model_id']
        safe_model_id = model_id.replace('_', '-').replace('/', '-')
        k8s_config = k8s_design.get("kubernetes_configuration", {})
        vllm_config = k8s_config.get("vllm_configuration", {})
        resource_reqs = k8s_config.get("resource_requirements", {})
        gpu_reqs = k8s_config.get("gpu_requirements", {})
        
        namespace = k8s_config.get("namespace", settings.default_namespace)
        deployment_name = k8s_config.get("deployment_name", safe_model_id)
        service_name = k8s_config.get("service_name", safe_model_id)
        replicas = k8s_config.get("replicas", settings.default_replicas)
        
        # Generate Namespace manifest
        namespace_yaml = f"""apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
"""
        
        # Generate ConfigMap for vLLM configuration
        configmap_yaml = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {deployment_name}-config
  namespace: {namespace}
data:
  MODEL_ID: "{vllm_config.get('model_id', model_id)}"
  MODEL_PATH: "{vllm_config.get('model_path', f'/models/{safe_model_id}')}"
  PORT: "{vllm_config.get('port', 8000)}"
  GPU_MEMORY_UTILIZATION: "{vllm_config.get('gpu_memory_utilization', 0.9)}"
  MAX_MODEL_LEN: "{vllm_config.get('max_model_len', 4096)}"
  TENSOR_PARALLEL_SIZE: "{vllm_config.get('tensor_parallel_size', 1)}"
"""
        
        # Generate Deployment manifest
        deployment_yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {deployment_name}
  namespace: {namespace}
  labels:
    app: {deployment_name}
    model: {model_id}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {deployment_name}
  template:
    metadata:
      labels:
        app: {deployment_name}
        model: {model_id}
    spec:
      containers:
      - name: vllm-server
        image: {settings.default_vllm_image}:{settings.vllm_image_tag}
        command: ["python", "-m", "vllm.entrypoints.openai.api_server"]
        args: [
          "--model", "$(MODEL_PATH)",
          "--host", "0.0.0.0",
          "--port", "$(PORT)",
          "--gpu-memory-utilization", "$(GPU_MEMORY_UTILIZATION)",
          "--max-model-len", "$(MAX_MODEL_LEN)"
        ]
        env:
        - name: MODEL_ID
          valueFrom:
            configMapKeyRef:
              name: {deployment_name}-config
              key: MODEL_ID
        - name: MODEL_PATH
          valueFrom:
            configMapKeyRef:
              name: {deployment_name}-config
              key: MODEL_PATH
        - name: PORT
          valueFrom:
            configMapKeyRef:
              name: {deployment_name}-config
              key: PORT
        - name: GPU_MEMORY_UTILIZATION
          valueFrom:
            configMapKeyRef:
              name: {deployment_name}-config
              key: GPU_MEMORY_UTILIZATION
        - name: MAX_MODEL_LEN
          valueFrom:
            configMapKeyRef:
              name: {deployment_name}-config
              key: MAX_MODEL_LEN
        - name: TENSOR_PARALLEL_SIZE
          valueFrom:
            configMapKeyRef:
              name: {deployment_name}-config
              key: TENSOR_PARALLEL_SIZE
        ports:
        - containerPort: {vllm_config.get('port', 8000)}
        resources:
          requests:
            cpu: {resource_reqs.get('cpu', '2')}
            memory: {resource_reqs.get('memory', '8Gi')}
"""
        
        # Add GPU resources if enabled
        if gpu_reqs.get("enabled", False):
            deployment_yaml += f"""          limits:
            nvidia.com/gpu: {gpu_reqs.get('gpu', '1')}
          requests:
            nvidia.com/gpu: {gpu_reqs.get('gpu', '1')}
"""
        else:
            cpu_request = resource_reqs.get('cpu', settings.default_cpu_request)
            memory_request = resource_reqs.get('memory', settings.default_memory_request)
            cpu_limit = str(int(cpu_request) * settings.default_cpu_limit_multiplier)
            memory_limit = str(int(memory_request.replace('Gi', '')) * settings.default_memory_limit_multiplier) + 'Gi'
            
            deployment_yaml += f"""          limits:
            cpu: {cpu_limit}
            memory: {memory_limit}
"""
        
        deployment_yaml += f"""        readinessProbe:
          httpGet:
            path: /health
            port: {vllm_config.get('port', settings.default_service_port)}
          initialDelaySeconds: {settings.health_check_initial_delay}
          periodSeconds: {settings.health_check_period}
        livenessProbe:
          httpGet:
            path: /health
            port: {vllm_config.get('port', settings.default_service_port)}
          initialDelaySeconds: {settings.liveness_check_initial_delay}
          periodSeconds: {settings.liveness_check_period}
"""
        
        # Generate Service manifest
        service_yaml = f"""apiVersion: v1
kind: Service
metadata:
  name: {service_name}
  namespace: {namespace}
  labels:
    app: {deployment_name}
    model: {model_id}
spec:
  type: {settings.default_service_type}
  ports:
  - port: 80
    targetPort: {vllm_config.get('port', settings.default_service_port)}
  selector:
    app: {deployment_name}
"""
        
        # Generate ArgoCD Application manifest
        argocd_app_yaml = f"""apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: {deployment_name}
  namespace: {namespace}
  labels:
    app: {deployment_name}
    model: {model_id}
spec:
  project: default
  source:
    repoURL: {settings.github_repo or 'https://github.com/example/repo'}
    targetRevision: HEAD
    path: deployment/manifests/{safe_model_id}
  destination:
    server: https://kubernetes.default.svc
    namespace: {namespace}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
"""
        
        return {
            "namespace": namespace_yaml,
            "configmap": configmap_yaml,
            "deployment": deployment_yaml,
            "service": service_yaml,
            "argocd_application": argocd_app_yaml
        }
    
    async def _commit_to_github(self, kubernetes_manifests: Dict[str, str], state: AgentState) -> Dict[str, Any]:
        """
        Commit Kubernetes manifests to GitHub repository for GitOps deployment
        
        Args:
            kubernetes_manifests: Kubernetes manifests to commit
            state: Current agent state
            
        Returns:
            GitOps commit result
        """
        model_id = state['model_id']
        
        try:
            commit_result = self.github_manifest_manager.commit_kubernetes_manifests(
                model_id=model_id,
                manifests=kubernetes_manifests,
                repository=settings.github_repo,
                branch="main",
                commit_message=f"Add Kubernetes manifests for model {model_id}"
            )
            
            logger.info(f"GitOps commit result: {commit_result.get('status')}")
            return commit_result
            
        except Exception as e:
            logger.error(f"Error committing to GitHub: {e}")
            return {
                "status": "error",
                "reason": f"Error during GitHub commit: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
    
    async def _create_argocd_application(self, kubernetes_manifests: Dict[str, str], state: AgentState) -> Dict[str, Any]:
        """
        Create ArgoCD application for the deployment
        
        Args:
            kubernetes_manifests: Kubernetes manifests
            state: Current agent state
            
        Returns:
            ArgoCD application creation result
        """
        model_id = state['model_id']
        safe_model_id = model_id.replace('_', '-').replace('/', '')
        namespace = settings.default_namespace
        
        try:
            if not settings.argocd_url:
                logger.warning("ArgoCD URL not configured - skipping ArgoCD application creation")
                return {
                    "status": "skipped",
                    "reason": "ArgoCD URL not configured",
                    "model_id": model_id
                }
            
            # Create ArgoCD application
            app_result = self.argocd_client.create_application(
                app_name=safe_model_id,
                repo_url=settings.github_repo or 'https://github.com/example/repo',
                path=f"deployment/manifests/{safe_model_id}",
                destination_server="https://kubernetes.default.svc",
                destination_namespace=namespace,
                project="default"
            )
            
            logger.info(f"ArgoCD application created: {safe_model_id}")
            return {
                "status": "success",
                "application_name": safe_model_id,
                "application_details": app_result,
                "model_id": model_id
            }
            
        except Exception as e:
            logger.error(f"Error creating ArgoCD application: {e}")
            return {
                "status": "error",
                "reason": f"Error during ArgoCD application creation: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
    
    async def _sync_argocd_application(self, state: AgentState) -> Dict[str, Any]:
        """
        Trigger ArgoCD application sync
        
        Args:
            state: Current agent state
            
        Returns:
            ArgoCD sync result
        """
        model_id = state['model_id']
        safe_model_id = model_id.replace('_', '-').replace('/', '')
        
        try:
            if not settings.argocd_url:
                logger.warning("ArgoCD URL not configured - skipping ArgoCD sync")
                return {
                    "status": "skipped",
                    "reason": "ArgoCD URL not configured",
                    "model_id": model_id
                }
            
            # Trigger sync
            sync_result = self.argocd_client.sync_application(
                app_name=safe_model_id,
                dry_run=False
            )
            
            logger.info(f"ArgoCD sync triggered for {safe_model_id}")
            return {
                "status": "success",
                "sync_details": sync_result,
                "model_id": model_id
            }
            
        except Exception as e:
            logger.error(f"Error triggering ArgoCD sync: {e}")
            return {
                "status": "error",
                "reason": f"Error during ArgoCD sync: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
    
    async def _verify_argocd_deployment(self, state: AgentState) -> Dict[str, Any]:
        """
        Verify deployment status via ArgoCD
        
        Args:
            state: Current agent state
            
        Returns:
            Deployment verification result
        """
        model_id = state['model_id']
        safe_model_id = model_id.replace('_', '-').replace('/', '')
        
        try:
            if not settings.argocd_url:
                logger.warning("ArgoCD URL not configured - using direct kubectl verification")
                return await self._verify_kubernetes_deployment(state)
            
            # Get application status from ArgoCD
            app_status = self.argocd_client.get_application_status(safe_model_id)
            
            sync_status = app_status.get("sync_status")
            health_status = app_status.get("health_status")
            
            all_positive = (
                sync_status == "Synced" and 
                health_status in ["Healthy", "Progressing"]
            )
            
            return {
                "overall_status": "success" if all_positive else "partial",
                "message": f"ArgoCD deployment verification: {'All indicators positive' if all_positive else 'Some indicators not positive'}",
                "model_id": model_id,
                "application_name": safe_model_id,
                "sync_status": sync_status,
                "health_status": health_status,
                "all_indicators_positive": all_positive,
                "details": app_status
            }
            
        except Exception as e:
            logger.error(f"Error verifying ArgoCD deployment: {e}")
            return {
                "overall_status": "error",
                "message": f"Error during ArgoCD verification: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
    
    async def _apply_kubernetes_deployment(self, kubernetes_manifests: Dict[str, str], state: AgentState) -> Dict[str, Any]:
        """
        Apply Kubernetes manifests to MicroK8s
        
        Args:
            kubernetes_manifests: Kubernetes manifests
            state: Current agent state
            
        Returns:
            Deployment application result
        """
        model_id = state['model_id']
        safe_model_id = model_id.replace('_', '-').replace('/', '')
        
        try:
            # Apply namespace using Kubernetes API
            logger.info("Applying namespace...")
            try:
                namespace_manifest = yaml.safe_load(kubernetes_manifests["namespace"])
                self.core_v1.create_namespace(body=namespace_manifest)
            except client.exceptions.ApiException as e:
                if e.status == 409:  # Already exists
                    logger.info("Namespace already exists")
                else:
                    raise
            
            # Apply ConfigMap using Kubernetes API
            logger.info("Applying ConfigMap...")
            try:
                configmap_manifest = yaml.safe_load(kubernetes_manifests["configmap"])
                self.core_v1.create_namespaced_config_map(
                    namespace=namespace,
                    body=configmap_manifest
                )
            except client.exceptions.ApiException as e:
                if e.status == 409:  # Already exists
                    logger.info("ConfigMap already exists, updating...")
                    self.core_v1.replace_namespaced_config_map(
                        name=configmap_manifest.metadata.name,
                        namespace=namespace,
                        body=configmap_manifest
                    )
                else:
                    raise
            
            # Apply Deployment using Kubernetes API
            logger.info("Applying Deployment...")
            try:
                deployment_manifest = yaml.safe_load(kubernetes_manifests["deployment"])
                self.apps_v1.create_namespaced_deployment(
                    namespace=namespace,
                    body=deployment_manifest
                )
            except client.exceptions.ApiException as e:
                if e.status == 409:  # Already exists
                    logger.info("Deployment already exists, updating...")
                    self.apps_v1.replace_namespaced_deployment(
                        name=deployment_manifest.metadata.name,
                        namespace=namespace,
                        body=deployment_manifest
                    )
                else:
                    raise
            
            # Apply Service using Kubernetes API
            logger.info("Applying Service...")
            try:
                service_manifest = yaml.safe_load(kubernetes_manifests["service"])
                self.core_v1.create_namespaced_service(
                    namespace=namespace,
                    body=service_manifest
                )
            except client.exceptions.ApiException as e:
                if e.status == 409:  # Already exists
                    logger.info("Service already exists, updating...")
                    self.core_v1.replace_namespaced_service(
                        name=service_manifest.metadata.name,
                        namespace=namespace,
                        body=service_manifest
                    )
                else:
                    raise
            
            logger.info("Kubernetes manifests applied successfully")
            
            return {
                "status": "applied",
                "message": "All Kubernetes manifests applied successfully",
                "model_id": model_id,
                "deployment_name": safe_model_id
            }
            
        except client.exceptions.ApiException as e:
            logger.error(f"Kubernetes API error: {e}")
            return {
                "status": "failed",
                "message": f"Kubernetes API error: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error in Kubernetes deployment: {e}")
            return {
                "status": "error",
                "message": f"Error during Kubernetes deployment: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
    
    async def _verify_kubernetes_deployment(self, state: AgentState) -> Dict[str, Any]:
        """
        Verify Kubernetes deployment status using Kubernetes API
        
        Args:
            state: Current agent state
            
        Returns:
            Deployment verification result
        """
        model_id = state['model_id']
        safe_model_id = model_id.replace('_', '-').replace('/', '')
        namespace = "model-serving"
        
        try:
            # Check deployment status using Kubernetes API
            logger.info("Checking deployment status...")
            try:
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=safe_model_id,
                    namespace=namespace
                )
                
                # Check deployment conditions
                conditions = deployment.status.conditions or []
                available = any(c.type == "Available" and c.status == "True" for c in conditions)
                ready = deployment.status.ready_replicas or 0
                replicas = deployment.spec.replicas or 1
                
                logger.info(f"Deployment status: {ready}/{replicas} replicas ready")
                deployment_status = "running" if available else "not_ready"
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    logger.warning(f"Deployment not found: {safe_model_id}")
                    deployment_status = "not_found"
                else:
                    raise
            
            # Check pod status using Kubernetes API
            logger.info("Checking pod status...")
            try:
                pods = self.core_v1.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=f"app={safe_model_id}"
                )
                
                if pods.items:
                    pod = pods.items[0]
                    pod_status = pod.status.phase
                    logger.info(f"Pod status: {pod_status}")
                else:
                    pod_status = "not_found"
                    logger.warning("No pods found for deployment")
            except client.exceptions.ApiException as e:
                logger.error(f"Error checking pod status: {e}")
                pod_status = "error"
            
            # Check service status using Kubernetes API
            logger.info("Checking service status...")
            try:
                service = self.core_v1.read_namespaced_service(
                    name=safe_model_id,
                    namespace=namespace
                )
                service_type = service.spec.type
                logger.info(f"Service type: {service_type}")
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    logger.warning(f"Service not found: {safe_model_id}")
                    service_type = "not_found"
                else:
                    raise
            
            # Determine overall status
            if deployment_status == "running" and pod_status == "Running":
                overall_status = "success"
                all_indicators_positive = True
            else:
                overall_status = "partial"
                all_indicators_positive = False
            
            return {
                "overall_status": overall_status,
                "message": f"Kubernetes deployment verification: {overall_status}",
                "model_id": model_id,
                "deployment_name": safe_model_id,
                "deployment_status": deployment_status,
                "pod_phase": pod_status,
                "service_type": service_type,
                "all_indicators_positive": all_indicators_positive,
                "details": {
                    "deployment_status": deployment_status,
                    "pod_phase": pod_status,
                    "service_type": service_type
                }
            }
            
        except client.exceptions.ApiException as e:
            logger.error(f"Kubernetes API error during verification: {e}")
            return {
                "overall_status": "error",
                "message": f"Kubernetes API error: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error verifying Kubernetes deployment: {e}")
            return {
                "overall_status": "error",
                "message": f"Error during deployment verification: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
    
    async def _compile_kubernetes_report(self, state: AgentState, k8s_design: Dict[str, Any], 
                                     kubernetes_manifests: Dict[str, str], gitops_result: Dict[str, Any],
                                     argocd_result: Dict[str, Any], sync_result: Dict[str, Any],
                                     deployment_verification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compile final Kubernetes deployment report
        
        Args:
            state: Current agent state
            k8s_design: Kubernetes deployment design configuration
            kubernetes_manifests: Generated Kubernetes manifests
            gitops_result: GitOps commit result
            argocd_result: ArgoCD application creation result
            sync_result: ArgoCD sync result
            deployment_verification: Deployment verification results
            
        Returns:
            Final Kubernetes deployment report
        """
        model_id = state['model_id']
        safe_model_id = model_id.replace('_', '-').replace('/', '')
        
        k8s_report = {
            "deployment_id": f"k8s-deploy-{model_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "model_id": model_id,
            "created_at": datetime.now().isoformat(),
            "kubernetes_design": {
                "reasoning": k8s_design.get('reasoning'),
                "configuration": k8s_design.get('kubernetes_configuration', {})
            },
            "kubernetes_manifests": {
                "namespace": kubernetes_manifests.get('namespace', ''),
                "configmap": kubernetes_manifests.get('configmap', ''),
                "deployment": kubernetes_manifests.get('deployment', ''),
                "service": kubernetes_manifests.get('service', ''),
                "argocd_application": kubernetes_manifests.get('argocd_application', '')
            },
            "gitops_commit": gitops_result,
            "argocd_application": argocd_result,
            "argocd_sync": sync_result,
            "deployment_verification": deployment_verification,
            "infrastructure_details": state.get('infrastructure_details', {}),
            "deployment_status": self._determine_deployment_status(deployment_verification),
            "service_endpoint": f"http://{safe_model_id}.model-serving.svc.cluster.local/v1/models",
            "next_steps": self._generate_deployment_next_steps(deployment_verification),
            "summary": self._generate_deployment_summary(model_id, deployment_verification)
        }
        
        return k8s_report
    
    def _determine_deployment_status(self, deployment_verification: Dict[str, Any]) -> str:
        """Determine overall deployment status based on verification"""
        if deployment_verification.get('all_indicators_positive'):
            return "deployed_and_healthy"
        elif deployment_verification.get('overall_status') == 'success':
            return "deployed_with_warnings"
        elif deployment_verification.get('overall_status') == 'partial':
            return "deployment_in_progress"
        elif deployment_verification.get('overall_status') == 'not_found':
            return "not_deployed"
        else:
            return "deployment_failed"
    
    def _generate_deployment_next_steps(self, deployment_verification: Dict[str, Any]) -> List[str]:
        """Generate next steps based on deployment verification"""
        next_steps = []
        
        if deployment_verification.get('all_indicators_positive'):
            next_steps.append("Kubernetes deployment verified successfully - all indicators positive")
        elif deployment_verification.get('overall_status') == 'not_found':
            next_steps.extend([
                "Apply Kubernetes manifests to cluster",
                "Monitor deployment progress",
                "Check pod and service status"
            ])
        elif deployment_verification.get('overall_status') == 'partial':
            next_steps.extend([
                "Monitor deployment progress",
                "Check pod logs for issues",
                "Review any synchronization issues"
            ])
        else:
            next_steps.extend([
                "Review deployment errors",
                "Check pod logs for issues",
                "Fix configuration issues and retry deployment"
            ])
        
        return next_steps
    
    def _generate_deployment_summary(self, model_id: str, deployment_verification: Dict[str, Any]) -> str:
        """Generate deployment summary"""
        if deployment_verification.get('all_indicators_positive'):
            return f"✅ Model {model_id} deployed successfully - Kubernetes shows all positive indicators"
        elif deployment_verification.get('overall_status') == 'not_found':
            return f"⏳ Model {model_id} Kubernetes configuration created - awaiting deployment"
        else:
            return f"⚠️ Model {model_id} deployment status: {deployment_verification.get('overall_status', 'unknown')}"