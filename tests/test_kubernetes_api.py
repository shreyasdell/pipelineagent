"""
Test Kubernetes API-based infrastructure checks
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.kubernetes_deployment.agent import KubernetesDeploymentAgent
from core.state.models import AgentState
from loguru import logger


async def test_kubernetes_api_check():
    """Test Kubernetes API connectivity check"""
    logger.info("Testing Kubernetes API check...")
    
    try:
        agent = KubernetesDeploymentAgent()
        result = agent._check_kubernetes_api()
        
        logger.info(f"Kubernetes API check result: {result}")
        
        if result.get("available"):
            logger.info(f"✅ Kubernetes API available - {result.get('node_count')} nodes")
            for node in result.get("nodes", []):
                logger.info(f"   Node: {node['name']} - {node['status']}")
            return True
        else:
            logger.error(f"❌ Kubernetes API not available: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Kubernetes API check failed: {e}")
        return False


async def test_gpu_kubernetes_check():
    """Test GPU availability in Kubernetes"""
    logger.info("Testing GPU-in-Kubernetes check...")
    
    try:
        agent = KubernetesDeploymentAgent()
        result = agent._check_gpu_kubernetes()
        
        logger.info(f"GPU-in-Kubernetes check result: {result}")
        
        if result.get("available"):
            logger.info(f"✅ GPU available in Kubernetes")
            for node in result.get("gpu_nodes", []):
                logger.info(f"   Node: {node['name']} - GPU count: {node['gpu_count']}")
            return True
        else:
            logger.warning(f"⚠️ GPU not available in Kubernetes: {result.get('error')}")
            logger.info("   This is expected if GPU addon is not enabled")
            return True  # Not a failure, just not configured
            
    except Exception as e:
        logger.error(f"❌ GPU-in-Kubernetes check failed: {e}")
        return False


async def test_gpu_host_check():
    """Test GPU availability on host"""
    logger.info("Testing GPU host check...")
    
    try:
        agent = KubernetesDeploymentAgent()
        result = agent._check_gpu_host()
        
        logger.info(f"GPU host check result: {result}")
        
        if result.get("available"):
            logger.info(f"✅ GPU available on host")
            gpu_info = result.get("info", {})
            logger.info(f"   GPU Name: {gpu_info.get('name')}")
            logger.info(f"   Driver: {gpu_info.get('driver')}")
            return True
        else:
            logger.warning(f"⚠️ GPU not available on host: {result.get('error')}")
            return True  # Not a failure, just no GPU
            
    except Exception as e:
        logger.error(f"❌ GPU host check failed: {e}")
        return False


async def test_vllm_check():
    """Test vLLM availability"""
    logger.info("Testing vLLM check...")
    
    try:
        agent = KubernetesDeploymentAgent()
        result = agent._check_vllm()
        
        logger.info(f"vLLM check result: {result}")
        
        if result.get("available"):
            logger.info(f"✅ vLLM available - version {result.get('version')}")
            return True
        else:
            logger.warning(f"⚠️ vLLM not available: {result.get('error')}")
            return True  # Not a failure, just not installed
            
    except Exception as e:
        logger.error(f"❌ vLLM check failed: {e}")
        return False


async def test_huggingface_check():
    """Test Hugging Face connectivity"""
    logger.info("Testing Hugging Face check...")
    
    try:
        agent = KubernetesDeploymentAgent()
        result = agent._check_huggingface()
        
        logger.info(f"Hugging Face check result: {result}")
        
        if result.get("available"):
            logger.info(f"✅ Hugging Face available")
            return True
        else:
            logger.warning(f"⚠️ Hugging Face not available: {result.get('error')}")
            return True  # Not a failure, just no token
            
    except Exception as e:
        logger.error(f"❌ Hugging Face check failed: {e}")
        return False


async def test_full_infrastructure_check():
    """Test full infrastructure check"""
    logger.info("Testing full infrastructure check...")
    
    try:
        agent = KubernetesDeploymentAgent()
        
        state = AgentState(
            messages=[],
            deployment_conversation_id="test-123",
            model_id="Qwen/Qwen2.5-7B",
            model_source_path=None,
            latency_requirement="<100ms",
            deployment_type="kubernetes",
            infrastructure_details={},
            errors=[],
            current_state="IDLE",
            state_history=[],
            retry_count=0,
            max_retries=3
        )
        
        result_state = await agent.check_infrastructure(state)
        
        logger.info(f"Full infrastructure check results:")
        logger.info(f"   Kubernetes API: {result_state['infrastructure_available']['kubernetes_api']}")
        logger.info(f"   kubectl CLI: {result_state['infrastructure_available']['kubectl_cli']}")
        logger.info(f"   GPU Host: {result_state['infrastructure_available']['gpu_host']}")
        logger.info(f"   GPU Kubernetes: {result_state['infrastructure_available']['gpu_kubernetes']}")
        logger.info(f"   vLLM: {result_state['infrastructure_available']['vllm']}")
        logger.info(f"   Hugging Face: {result_state['infrastructure_available']['huggingface']}")
        
        logger.info(f"Infrastructure details:")
        logger.info(f"   Kubernetes Available: {result_state['infrastructure_details']['kubernetes_available']}")
        logger.info(f"   GPU Available: {result_state['infrastructure_details']['gpu_available']}")
        logger.info(f"   vLLM Available: {result_state['infrastructure_details']['vllm_available']}")
        logger.info(f"   Hugging Face Available: {result_state['infrastructure_details']['huggingface_available']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Full infrastructure check failed: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Kubernetes API Infrastructure Checks")
    logger.info("=" * 60)
    
    tests = [
        ("Kubernetes API Check", test_kubernetes_api_check),
        ("GPU-in-Kubernetes Check", test_gpu_kubernetes_check),
        ("GPU Host Check", test_gpu_host_check),
        ("vLLM Check", test_vllm_check),
        ("Hugging Face Check", test_huggingface_check),
        ("Full Infrastructure Check", test_full_infrastructure_check)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info("\n" + "=" * 60)
        logger.info(f"Test: {test_name}")
        logger.info("=" * 60)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {test_name}")
    
    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)