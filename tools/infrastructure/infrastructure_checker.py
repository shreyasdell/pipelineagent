from typing import Dict, Any, Optional
import subprocess
from loguru import logger


class InfrastructureChecker:
    """
    Infrastructure Checker - Verifies infrastructure prerequisites for deployment
    Checks MicroK8s, GPU, ArgoCD, vLLM, and Hugging Face availability
    """
    
    def __init__(self):
        self.checks = {
            "microk8s": self._check_microk8s,
            "kubectl": self._check_kubectl,
            "gpu": self._check_gpu,
            "argocd": self._check_argocd,
            "vllm": self._check_vllm,
            "huggingface": self._check_huggingface
        }
    
    def check_all(self) -> Dict[str, Any]:
        """
        Check all infrastructure components
        
        Returns:
            Dictionary with availability status for each component
        """
        results = {}
        
        for component_name, check_function in self.checks.items():
            try:
                logger.info(f"Checking {component_name}...")
                result = check_function()
                results[component_name] = result
                logger.info(f"{component_name}: {'✅ Available' if result.get('available') else '❌ Not available'} - {result.get('details', '')}")
            except Exception as e:
                logger.error(f"Error checking {component_name}: {e}")
                results[component_name] = {
                    "available": False,
                    "reason": f"Check failed: {str(e)}",
                    "details": ""
                }
        
        # Determine recommended deployment type
        results["recommended_deployment_type"] = self._determine_deployment_type(results)
        
        return results
    
    def _check_microk8s(self) -> Dict[str, Any]:
        """Check MicroK8s availability and status"""
        try:
            # Try to access MicroK8s via kubectl
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Get node information
                node_result = subprocess.run(
                    ["kubectl", "get", "nodes", "-o", "jsonpath={.items[*].status.conditions[*].type}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                return {
                    "available": True,
                    "reason": "MicroK8s cluster accessible",
                    "details": result.stdout[:200] if result.stdout else "Cluster info available"
                }
            else:
                return {
                    "available": False,
                    "reason": "MicroK8s cluster not accessible",
                    "details": result.stderr[:200] if result.stderr else "Unknown error"
                }
        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "reason": "MicroK8s check timed out",
                "details": "kubectl cluster-info command timed out"
            }
        except FileNotFoundError:
            return {
                "available": False,
                "reason": "kubectl not found in PATH",
                "details": "kubectl command not available"
            }
        except Exception as e:
            return {
                "available": False,
                "reason": f"MicroK8s check failed: {str(e)}",
                "details": ""
            }
    
    def _check_kubectl(self) -> Dict[str, Any]:
        """Check kubectl availability and version"""
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_info = result.stdout.strip()
                return {
                    "available": True,
                    "reason": "kubectl available",
                    "details": version_info[:100] if version_info else "kubectl executable"
                }
            else:
                return {
                    "available": False,
                    "reason": "kubectl not working",
                    "details": result.stderr[:200] if result.stderr else "Unknown error"
                }
        except FileNotFoundError:
            return {
                "available": False,
                "reason": "kubectl not found in PATH",
                "details": "kubectl command not available"
            }
        except Exception as e:
            return {
                "available": False,
                "reason": f"kubectl check failed: {str(e)}",
                "details": ""
            }
    
    def _check_gpu(self) -> Dict[str, Any]:
        """Check GPU availability and NVIDIA drivers"""
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse GPU information
                gpu_info = self._parse_nvidia_smi(result.stdout)
                return {
                    "available": True,
                    "reason": "GPU available",
                    "details": gpu_info
                }
            else:
                return {
                    "available": False,
                    "reason": "GPU not available or drivers not installed",
                    "details": result.stderr[:200] if result.stderr else "nvidia-smi failed"
                }
        except FileNotFoundError:
            return {
                "available": False,
                "reason": "nvidia-smi not found",
                "details": "NVIDIA drivers not installed or not in PATH"
            }
        except Exception as e:
            return {
                "available": False,
                "reason": f"GPU check failed: {str(e)}",
                "details": ""
            }
    
    def _parse_nvidia_smi(self, output: str) -> str:
        """Parse nvidia-smi output for GPU information"""
        try:
            lines = output.split('\n')
            for line in lines:
                if 'NVIDIA' in line and 'Driver Version' in line:
                    return line.strip()
            return "NVIDIA GPU detected"
        except:
            return "NVIDIA GPU detected"
    
    def _check_argocd(self) -> Dict[str, Any]:
        """Check ArgoCD CLI and server availability"""
        try:
            result = subprocess.run(
                ["argocd", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_info = result.stdout.strip()
                return {
                    "available": True,
                    "reason": "ArgoCD CLI available",
                    "details": version_info[:100] if version_info else "argocd executable"
                }
            else:
                return {
                    "available": False,
                    "reason": "ArgoCD CLI not working",
                    "details": result.stderr[:200] if result.stderr else "Unknown error"
                }
        except FileNotFoundError:
            return {
                "available": False,
                "reason": "argocd not found in PATH",
                "details": "ArgoCD CLI not installed"
            }
        except Exception as e:
            return {
                "available": False,
                "reason": f"ArgoCD check failed: {str(e)}",
                "details": ""
            }
    
    def _check_vllm(self) -> Dict[str, Any]:
        """Check vLLM installation and availability"""
        try:
            import vllm
            version = vllm.__version__
            return {
                "available": True,
                "reason": "vLLM installed",
                "details": f"vLLM version {version}"
            }
        except ImportError:
            return {
                "available": False,
                "reason": "vLLM not installed",
                "details": "vllm package not found in Python environment"
            }
        except Exception as e:
            return {
                "available": False,
                "reason": f"vLLM check failed: {str(e)}",
                "details": ""
            }
    
    def _check_huggingface(self) -> Dict[str, Any]:
        """Check Hugging Face connectivity"""
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            # Try to get model info as a connectivity test
            model_info = api.model_info("Qwen/Qwen2.5-7B")
            return {
                "available": True,
                "reason": "Hugging Face API accessible",
                "details": f"Successfully connected to Hugging Face"
            }
        except ImportError:
            return {
                "available": False,
                "reason": "huggingface_hub not installed",
                "details": "huggingface_hub package not found"
            }
        except Exception as e:
            return {
                "available": False,
                "reason": f"Hugging Face check failed: {str(e)}",
                "details": ""
            }
    
    def _determine_deployment_type(self, results: Dict[str, Any]) -> str:
        """
        Determine recommended deployment type based on infrastructure availability
        
        Args:
            results: Infrastructure check results
            
        Returns:
            Recommended deployment type: "kubernetes" or "local"
        """
        # Check if Kubernetes path is viable
        kubernetes_requirements = [
            results.get("microk8s", {}).get("available", False),
            results.get("kubectl", {}).get("available", False),
            results.get("gpu", {}).get("available", False)
        ]
        
        if all(kubernetes_requirements):
            return "kubernetes"
        elif results.get("gpu", {}).get("available", False) and results.get("vllm", {}).get("available", False):
            return "local"
        else:
            return "insufficient_infrastructure"
    
    def get_deployment_prerequisites(self, deployment_type: str) -> Dict[str, Any]:
        """
        Get prerequisites for a specific deployment type
        
        Args:
            deployment_type: "kubernetes" or "local"
            
        Returns:
            Dictionary of prerequisites and their status
        """
        if deployment_type == "kubernetes":
            return {
                "required": {
                    "microk8s": "MicroK8s cluster running and accessible",
                    "kubectl": "kubectl command available",
                    "gpu": "NVIDIA GPU with drivers installed",
                    "huggingface": "Hugging Face API access"
                },
                "optional": {
                    "argocd": "ArgoCD for GitOps deployment"
                }
            }
        elif deployment_type == "local":
            return {
                "required": {
                    "gpu": "NVIDIA GPU with drivers installed",
                    "vllm": "vLLM installed in Python environment",
                    "huggingface": "Hugging Face API access"
                },
                "optional": {}
            }
        else:
            return {
                "required": {},
                "optional": {}
            }