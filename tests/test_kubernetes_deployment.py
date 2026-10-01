import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.kubernetes_deployment.agent import KubernetesDeploymentAgent
from core.state.models import AgentState
from tools.infrastructure.infrastructure_checker import InfrastructureChecker
from loguru import logger


async def test_kubernetes_deployment_agent_creation():
    """Test Kubernetes Deployment Agent creation"""
    logger.info("Testing Kubernetes Deployment Agent creation...")
    
    agent = KubernetesDeploymentAgent()
    
    assert agent is not None, "Agent should be created"
    assert agent.llm is not None, "Agent should have LLM configured"
    assert agent.argocd_client is not None, "Agent should have ArgoCD client"
    assert agent.huggingface_client is not None, "Agent should have HuggingFace client"
    
    logger.info("✅ Kubernetes Deployment Agent created successfully")
    
    return True


async def test_infrastructure_checker():
    """Test infrastructure checker"""
    logger.info("Testing infrastructure checker...")
    
    checker = InfrastructureChecker()
    
    # Check individual components
    logger.info("Checking individual components...")
    
    kubectl_result = checker._check_kubectl()
    logger.info(f"✅ kubectl check: {kubectl_result['available']}")
    
    gpu_result = checker._check_gpu()
    logger.info(f"✅ GPU check: {gpu_result['available']}")
    
    vllm_result = checker._check_vllm()
    logger.info(f"✅ vLLM check: {vllm_result['available']}")
    
    huggingface_result = checker._check_huggingface()
    logger.info(f"✅ Hugging Face check: {huggingface_result['available']}")
    
    # Check all components
    logger.info("Checking all components...")
    all_results = checker.check_all()
    
    logger.info(f"✅ All infrastructure checks completed")
    logger.info(f"Recommended deployment type: {all_results.get('recommended_deployment_type', 'unknown')}")
    
    return True


async def test_kubernetes_manifest_generation():
    """Test Kubernetes manifest generation"""
    logger.info("Testing Kubernetes manifest generation...")
    
    agent = KubernetesDeploymentAgent()
    
    # Create a test state
    test_state = AgentState(
        messages=[],
        deployment_conversation_id="test-k8s-001",
        model_id="Qwen/Qwen2.5-7B",
        latency_requirement="<100ms",
        deployment_type="standard",
        infrastructure_details={
            "gpu_type": "NVIDIA RTX PRO 2000",
            "gpu_memory_gb": 8,
            "gpu_count": 1
        },
        errors=[]
    )
    
    # Create default Kubernetes design
    k8s_design = agent._create_default_kubernetes_design(test_state)
    
    logger.info(f"✅ Default Kubernetes design created")
    logger.info(f"Reasoning: {k8s_design['reasoning']}")
    
    # Generate manifests
    manifests = agent._generate_kubernetes_manifests(k8s_design, test_state)
    
    assert "namespace" in manifests, "Should have namespace manifest"
    assert "configmap" in manifests, "Should have ConfigMap manifest"
    assert "deployment" in manifests, "Should have Deployment manifest"
    assert "service" in manifests, "Should have Service manifest"
    assert "argocd_application" in manifests, "Should have ArgoCD Application manifest"
    
    logger.info("✅ All Kubernetes manifests generated successfully")
    
    # Verify manifest content
    assert "model-serving" in manifests["namespace"], "Namespace should be model-serving"
    assert "Deployment" in manifests["deployment"], "Should contain Deployment resource"
    assert "Service" in manifests["service"], "Should contain Service resource"
    
    logger.info("✅ Manifest content verified")
    
    return True


async def test_deployment_type_decision():
    """Test deployment type decision logic"""
    logger.info("Testing deployment type decision logic...")
    
    checker = InfrastructureChecker()
    
    # Test Kubernetes path
    kubernetes_results = {
        "microk8s": {"available": True},
        "kubectl": {"available": True},
        "gpu": {"available": True},
        "vllm": {"available": True},
        "huggingface": {"available": True}
    }
    
    decision = checker._determine_deployment_type(kubernetes_results)
    assert decision == "kubernetes", f"Expected 'kubernetes', got '{decision}'"
    logger.info("✅ Kubernetes path decision correct")
    
    # Test local path
    local_results = {
        "microk8s": {"available": False},
        "kubectl": {"available": False},
        "gpu": {"available": True},
        "vllm": {"available": True},
        "huggingface": {"available": True}
    }
    
    decision = checker._determine_deployment_type(local_results)
    assert decision == "local", f"Expected 'local', got '{decision}'"
    logger.info("✅ Local path decision correct")
    
    # Test insufficient infrastructure
    insufficient_results = {
        "microk8s": {"available": False},
        "kubectl": {"available": False},
        "gpu": {"available": False},
        "vllm": {"available": False},
        "huggingface": {"available": False}
    }
    
    decision = checker._determine_deployment_type(insufficient_results)
    assert decision == "insufficient_infrastructure", f"Expected 'insufficient_infrastructure', got '{decision}'"
    logger.info("✅ Insufficient infrastructure decision correct")
    
    return True


async def test_deployment_prerequisites():
    """Test deployment prerequisites"""
    logger.info("Testing deployment prerequisites...")
    
    checker = InfrastructureChecker()
    
    # Test Kubernetes prerequisites
    k8s_prereqs = checker.get_deployment_prerequisites("kubernetes")
    
    assert "required" in k8s_prereqs, "Should have required prerequisites"
    assert "optional" in k8s_prereqs, "Should have optional prerequisites"
    assert "microk8s" in k8s_prereqs["required"], "Should require microk8s"
    assert "kubectl" in k8s_prereqs["required"], "Should require kubectl"
    assert "gpu" in k8s_prereqs["required"], "Should require GPU"
    
    logger.info("✅ Kubernetes prerequisites correct")
    
    # Test local prerequisites
    local_prereqs = checker.get_deployment_prerequisites("local")
    
    assert "required" in local_prereqs, "Should have required prerequisites"
    assert "vllm" in local_prereqs["required"], "Should require vLLM"
    assert "gpu" in local_prereqs["required"], "Should require GPU"
    
    logger.info("✅ Local prerequisites correct")
    
    return True


async def test_kubernetes_deployment_design_parsing():
    """Test Kubernetes deployment design parsing"""
    logger.info("Testing Kubernetes deployment design parsing...")
    
    agent = KubernetesDeploymentAgent()
    
    # Test with valid JSON
    valid_json = """{
        "reasoning": "Test reasoning",
        "kubernetes_configuration": {
            "namespace": "test-namespace",
            "deployment_name": "test-deployment"
        }
    }"""
    
    test_state = AgentState(
        messages=[],
        deployment_conversation_id="test",
        model_id="test-model",
        errors=[]
    )
    
    parsed = agent._parse_kubernetes_design(valid_json, test_state)
    
    assert parsed["reasoning"] == "Test reasoning", "Should parse reasoning"
    assert "kubernetes_configuration" in parsed, "Should have kubernetes_configuration"
    logger.info("✅ Valid JSON parsing successful")
    
    # Test with invalid JSON (should use default)
    invalid_json = "This is not valid JSON"
    
    parsed = agent._parse_kubernetes_design(invalid_json, test_state)
    
    assert parsed is not None, "Should return default design for invalid JSON"
    assert "kubernetes_configuration" in parsed, "Default should have kubernetes_configuration"
    logger.info("✅ Invalid JSON fallback successful")
    
    return True


async def main():
    """Run all Kubernetes deployment tests"""
    logger.info("=" * 60)
    logger.info("Kubernetes Deployment Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Agent Creation", test_kubernetes_deployment_agent_creation),
        ("Infrastructure Checker", test_infrastructure_checker),
        ("Manifest Generation", test_kubernetes_manifest_generation),
        ("Deployment Type Decision", test_deployment_type_decision),
        ("Deployment Prerequisites", test_deployment_prerequisites),
        ("Design Parsing", test_kubernetes_deployment_design_parsing)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Test: {test_name}")
        logger.info('=' * 60)
        
        try:
            result = await test_func()
            results.append((test_name, "PASSED"))
            logger.info(f"✅ {test_name} PASSED")
        except Exception as e:
            results.append((test_name, "FAILED"))
            logger.error(f"❌ {test_name} FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    for test_name, status in results:
        status_icon = "✅" if status == "PASSED" else "❌"
        logger.info(f"{status_icon} {test_name}: {status}")
    
    passed = sum(1 for _, status in results if status == "PASSED")
    total = len(results)
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)