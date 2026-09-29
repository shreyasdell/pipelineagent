import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.deployment_pipeline import DeploymentPipelineAgent
from core.state.models import AgentState
from core.config.settings import settings


async def test_deployment_pipeline_agent():
    """Test the Deployment Pipeline Agent with ArgoCD integration"""
    
    # Initialize agent
    agent = DeploymentPipelineAgent()
    
    # Create test state with deployment requirements
    test_state = AgentState(
        messages=[],
        deployment_conversation_id="test-dep-001",
        model_id="fraud_model_v3",
        model_source_path=None,
        latency_requirement="<100ms",
        deployment_type="canary",
        infrastructure_details={
            "gpu_type": "NVIDIA A100",
            "gpu_memory_gb": 80,
            "gpu_count": 2,
            "cpu_cores": 64,
            "ram_gb": 256
        },
        errors=[]
    )
    
    print("Testing Deployment Pipeline Agent - ArgoCD Integration")
    print("=" * 60)
    print(f"Model ID: {test_state['model_id']}")
    print(f"Deployment Type: {test_state['deployment_type']}")
    print(f"ArgoCD URL: {settings.argocd_url or 'Not configured'}")
    print(f"ArgoCD Username: {settings.argocd_username or 'Not configured'}")
    print()
    
    # Run deployment pipeline creation
    result_state = await agent.create_deployment_pipeline(test_state)
    
    # Display results
    print("=" * 60)
    print("Deployment Pipeline Creation Results")
    print("=" * 60)
    
    if result_state.get('deployment_report'):
        report = result_state['deployment_report']
        print(f"Deployment ID: {report['deployment_id']}")
        print(f"Model ID: {report['model_id']}")
        print(f"Created At: {report['created_at']}")
        print(f"Status: {report['deployment_status']}")
        
        print(f"\nPipeline Design:")
        print(f"  Reasoning: {report['pipeline_design']['reasoning']}")
        print(f"  Stages: {len(report['pipeline_design']['stages'])}")
        
        print(f"\nContainerization:")
        containerization = report['pipeline_design']['containerization']
        print(f"  Base Image: {containerization.get('base_image', 'N/A')}")
        print(f"  Registry: {containerization.get('registry', 'N/A')}")
        print(f"  Image Tag: {containerization.get('image_tag', 'N/A')}")
        
        print(f"\nInfrastructure Requirements:")
        infra = report['pipeline_design']['infrastructure_requirements']
        print(f"  CPU: {infra.get('cpu', 'N/A')}")
        print(f"  Memory: {infra.get('memory', 'N/A')}")
        print(f"  GPU: {infra.get('gpu', 'N/A')}")
        print(f"  Storage: {infra.get('storage', 'N/A')}")
        
        print(f"\nDeployment Configs:")
        configs = report['deployment_configs']
        print(f"  Kubernetes Manifests: {len(configs['kubernetes_manifests'])} files")
        print(f"  ArgoCD Application: {'Generated' if configs['argocd_application'] else 'Not generated'}")
        print(f"  Dockerfile: {'Generated' if configs['dockerfile'] else 'Not generated'}")
        print(f"  Helm Values: {'Generated' if configs['helm_values'] else 'Not generated'}")
        
        print(f"\nArgoCD Verification:")
        verification = report['argocd_verification']
        print(f"  Overall Status: {verification['overall_status']}")
        print(f"  Message: {verification['message']}")
        if verification.get('all_indicators_positive'):
            print(f"  All Indicators Positive: ✅ Yes")
        else:
            print(f"  All Indicators Positive: ❌ No")
        
        if verification.get('details'):
            details = verification['details']
            print(f"  Application Name: {details.get('application_name', 'N/A')}")
            print(f"  Sync Status: {details.get('sync_status', 'N/A')}")
            print(f"  Health Status: {details.get('health_status', 'N/A')}")
        
        print(f"\nService Endpoint: {report['service_endpoint']}")
        
        print(f"\nNext Steps:")
        for i, step in enumerate(report['next_steps'], 1):
            print(f"  {i}. {step}")
        
        print(f"\nSummary:")
        print(f"  {report['summary']}")
    else:
        print("No deployment report generated - check logs for errors")


async def test_deployment_pipeline_with_ci():
    """Test Deployment Pipeline Agent with CI pipeline integration"""
    
    # Initialize agent
    agent = DeploymentPipelineAgent()
    
    # Create test state with CI pipeline
    test_state = AgentState(
        messages=[],
        deployment_conversation_id="test-dep-002",
        model_id="qwen2.5-7b",
        model_source_path=None,
        latency_requirement="<50ms",
        deployment_type="standard",
        infrastructure_details={
            "gpu_type": "NVIDIA A100",
            "gpu_memory_gb": 40,
            "gpu_count": 1,
            "cpu_cores": 32,
            "ram_gb": 128
        },
        ci_pipeline={
            "pipeline_id": "ci-qwen2.5-7b-20240101120000",
            "github_repository": "your-org/models",
            "workflows_created": ["build-and-test", "deploy"],
            "pipeline_verification": {
                "overall_status": "success",
                "message": "CI pipeline verified successfully"
            }
        },
        errors=[]
    )
    
    print("\n" + "=" * 60)
    print("Testing Deployment Pipeline Agent with CI Pipeline")
    print("=" * 60)
    print(f"Model ID: {test_state['model_id']}")
    print(f"CI Pipeline ID: {test_state['ci_pipeline']['pipeline_id']}")
    print()
    
    # Run deployment pipeline creation
    result_state = await agent.create_deployment_pipeline(test_state)
    
    # Display results
    if result_state.get('deployment_report'):
        report = result_state['deployment_report']
        print(f"\nDeployment Report:")
        print(f"  Deployment ID: {report['deployment_id']}")
        print(f"  Status: {report['deployment_status']}")
        print(f"  ArgoCD Verification: {report['argocd_verification']['overall_status']}")
        print(f"  Summary: {report['summary']}")


async def test_deployment_pipeline_manifests():
    """Test the deployment configuration generation specifically"""
    
    agent = DeploymentPipelineAgent()
    
    test_state = AgentState(
        messages=[],
        deployment_conversation_id="test-dep-manifests",
        model_id="test_model",
        deployment_type="canary",
        errors=[]
    )
    
    print("\n" + "=" * 60)
    print("Testing Deployment Configuration Generation")
    print("=" * 60)
    
    result_state = await agent.create_deployment_pipeline(test_state)
    
    if result_state.get('deployment_report'):
        report = result_state['deployment_report']
        configs = report['deployment_configs']
        
        print(f"\nKubernetes Deployment Manifest:")
        print("```yaml")
        print(configs['kubernetes_manifests']['deployment'][:400] + "..." if len(configs['kubernetes_manifests']['deployment']) > 400 else configs['kubernetes_manifests']['deployment'])
        print("```")
        
        print(f"\nKubernetes Service Manifest:")
        print("```yaml")
        print(configs['kubernetes_manifests']['service'][:300] + "..." if len(configs['kubernetes_manifests']['service']) > 300 else configs['kubernetes_manifests']['service'])
        print("```")
        
        print(f"\nArgoCD Application Manifest:")
        print("```yaml")
        print(configs['argocd_application'][:400] + "..." if len(configs['argocd_application']) > 400 else configs['argocd_application'])
        print("```")
        
        print(f"\nDockerfile:")
        print("```dockerfile")
        print(configs['dockerfile'][:300] + "..." if len(configs['dockerfile']) > 300 else configs['dockerfile'])
        print("```")


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: Deployment Pipeline Agent Basic")
    print("=" * 60)
    asyncio.run(test_deployment_pipeline_agent())
    
    print("\n" + "=" * 60)
    print("Test 2: Deployment Pipeline Agent with CI Pipeline")
    print("=" * 60)
    asyncio.run(test_deployment_pipeline_with_ci())
    
    print("\n" + "=" * 60)
    print("Test 3: Deployment Configuration Generation")
    print("=" * 60)
    asyncio.run(test_deployment_pipeline_manifests())
