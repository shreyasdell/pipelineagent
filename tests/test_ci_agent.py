import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.ci_agent import CIAgent
from core.state.models import AgentState
from core.config.settings import settings


async def test_ci_agent():
    """Test the CI Agent with pipeline creation and GitHub integration"""
    
    # Initialize agent
    agent = CIAgent()
    
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
    
    print("Testing CI Agent - GitHub Actions Pipeline Creation")
    print("=" * 60)
    print(f"Model ID: {test_state['model_id']}")
    print(f"Deployment Type: {test_state['deployment_type']}")
    print(f"GitHub Repository: {settings.github_repo or 'Not configured'}")
    print(f"GitHub Token: {'Configured' if settings.github_token else 'Not configured'}")
    print()
    
    # Run pipeline creation
    result_state = await agent.create_ci_pipeline(test_state)
    
    # Display results
    print("=" * 60)
    print("CI/CD Pipeline Creation Results")
    print("=" * 60)
    
    if result_state.get('ci_pipeline'):
        pipeline = result_state['ci_pipeline']
        print(f"Pipeline ID: {pipeline['pipeline_id']}")
        print(f"Model ID: {pipeline['model_id']}")
        print(f"Created At: {pipeline['created_at']}")
        print(f"Status: {pipeline['status']}")
        
        print(f"\nPipeline Design:")
        print(f"  Reasoning: {pipeline['pipeline_design']['reasoning']}")
        print(f"  Testing Strategy: {pipeline['pipeline_design']['testing_strategy']}")
        print(f"  Deployment Strategy: {pipeline['pipeline_design']['deployment_strategy']}")
        
        print(f"\nSecurity Considerations:")
        for consideration in pipeline['pipeline_design']['security_considerations']:
            print(f"  - {consideration}")
        
        print(f"\nGitHub Workflows Generated ({len(pipeline['github_workflows'])}):")
        for workflow_name in pipeline['github_workflows'].keys():
            print(f"  - {workflow_name}")
        
        print(f"\nGitHub Workflow Files Status:")
        for workflow_name, file_info in pipeline['github_workflow_files'].items():
            print(f"  {workflow_name}:")
            print(f"    Status: {file_info['status']}")
            print(f"    File Path: {file_info['file_path']}")
            if file_info.get('branch'):
                print(f"    Branch: {file_info['branch']}")
            if file_info.get('pull_request'):
                print(f"    Pull Request: {file_info['pull_request']['url']} (#{file_info['pull_request']['number']})")
            if file_info.get('error'):
                print(f"    Error: {file_info['error']}")
        
        print(f"\nPipeline Verification:")
        verification = pipeline['pipeline_verification']
        print(f"  Overall Status: {verification['overall_status']}")
        print(f"  Message: {verification['message']}")
        if verification.get('github_repository'):
            print(f"  GitHub Repository: {verification['github_repository']}")
        
        if verification.get('workflow_verifications'):
            print(f"  Workflow Verifications:")
            for workflow_name, workflow_verification in verification['workflow_verifications'].items():
                print(f"    {workflow_name}:")
                print(f"      Verified: {workflow_verification.get('verified', 'N/A')}")
                print(f"      Status: {workflow_verification.get('status', 'N/A')}")
                print(f"      Message: {workflow_verification.get('message', 'N/A')}")
        
        print(f"\nWorkflow Configuration:")
        print(f"  GitHub Repository: {pipeline['configuration']['github_repository']}")
        print(f"  Default Branch: {pipeline['configuration']['default_branch']}")
        print(f"  Environments: {', '.join(pipeline['configuration']['environments'])}")
        
        print(f"\nRequired Secrets:")
        for secret in pipeline['configuration']['secrets_required']:
            print(f"  - {secret}")
        
        print(f"\nNext Steps:")
        for i, step in enumerate(pipeline['next_steps'], 1):
            print(f"  {i}. {step}")
        
        print(f"\nSample Workflow YAML (first workflow):")
        first_workflow_name = list(pipeline['github_workflows'].keys())[0]
        first_workflow_yaml = pipeline['github_workflows'][first_workflow_name]
        print("```yaml")
        print(first_workflow_yaml[:500] + "..." if len(first_workflow_yaml) > 500 else first_workflow_yaml)
        print("```")
    else:
        print("No CI pipeline generated - check logs for errors")


async def test_ci_agent_with_constraint_report():
    """Test CI Agent with constraint resolver report integration"""
    
    # Initialize agent
    agent = CIAgent()
    
    # Create test state with constraint resolver report
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
        constraint_resolver_report={
            "model_id": "qwen2.5-7b",
            "overall_confidence_score": 85,
            "quantization_levels_possible": [
                {"level": "FP16", "size_gb": 14.5, "speed_multiplier": 1.0, "accuracy_loss": "none"},
                {"level": "INT8", "size_gb": 7.2, "speed_multiplier": 1.5, "accuracy_loss": "minimal"}
            ],
            "parallelization_possible": {
                "tensor": True,
                "pipeline": False,
                "expert": False,
                "data": True
            },
            "weight_format": "safetensors",
            "engine_type": "vllm",
            "deployment_feasible": True,
            "recommendations": [
                "Use vLLM with tensor parallelism for optimal performance",
                "Consider INT8 quantization to reduce memory footprint"
            ]
        },
        errors=[]
    )
    
    print("\n" + "=" * 60)
    print("Testing CI Agent with Constraint Resolver Report")
    print("=" * 60)
    print(f"Model ID: {test_state['model_id']}")
    print(f"Latency Requirement: {test_state['latency_requirement']}")
    print(f"Constraint Confidence: {test_state['constraint_resolver_report']['overall_confidence_score']}%")
    print(f"Recommended Engine: {test_state['constraint_resolver_report']['engine_type']}")
    print()
    
    # Run pipeline creation
    result_state = await agent.create_ci_pipeline(test_state)
    
    # Display results
    if result_state.get('ci_pipeline'):
        pipeline = result_state['ci_pipeline']
        print(f"\nCI Pipeline Created:")
        print(f"  Pipeline ID: {pipeline['pipeline_id']}")
        print(f"  Status: {pipeline['status']}")
        print(f"  Workflows Generated: {len(pipeline['github_workflows'])}")
        print(f"  Testing Strategy: {pipeline['pipeline_design']['testing_strategy']}")
        print(f"  Deployment Strategy: {pipeline['pipeline_design']['deployment_strategy']}")
        
        if pipeline.get('pipeline_verification'):
            verification = pipeline['pipeline_verification']
            print(f"  Verification Status: {verification['overall_status']}")
            print(f"  Verification Message: {verification['message']}")


async def test_ci_agent_different_deployment_types():
    """Test CI Agent with different deployment types"""
    
    agent = CIAgent()
    
    test_cases = [
        {
            "model_id": "canary_model",
            "deployment_type": "canary",
            "description": "Canary deployment with gradual rollout"
        },
        {
            "model_id": "blue_green_model",
            "deployment_type": "blue_green",
            "description": "Blue-green deployment with instant switch"
        },
        {
            "model_id": "standard_model",
            "deployment_type": "standard",
            "description": "Standard deployment with basic CI/CD"
        }
    ]
    
    print("\n" + "=" * 60)
    print("Testing CI Agent with Different Deployment Types")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['description']}")
        print(f"  Model: {test_case['model_id']}")
        print(f"  Deployment: {test_case['deployment_type']}")
        
        test_state = AgentState(
            messages=[],
            deployment_conversation_id=f"test-dep-{i:03d}",
            model_id=test_case['model_id'],
            deployment_type=test_case['deployment_type'],
            errors=[]
        )
        
        result_state = await agent.create_ci_pipeline(test_state)
        
        if result_state.get('ci_pipeline'):
            pipeline = result_state['ci_pipeline']
            print(f"  Result:")
            print(f"    Pipeline ID: {pipeline['pipeline_id']}")
            print(f"    Status: {pipeline['status']}")
            print(f"    Workflows: {len(pipeline['github_workflows'])}")
            print(f"    Strategy: {pipeline['pipeline_design']['deployment_strategy']}")
            
            if pipeline.get('pipeline_verification'):
                verification = pipeline['pipeline_verification']
                print(f"    Verification: {verification['overall_status']}")


async def test_ci_agent_workflow_yaml_generation():
    """Test the GitHub Actions YAML generation specifically"""
    
    agent = CIAgent()
    
    test_state = AgentState(
        messages=[],
        deployment_conversation_id="test-dep-yaml",
        model_id="test_model",
        deployment_type="canary",
        errors=[]
    )
    
    print("\n" + "=" * 60)
    print("Testing GitHub Actions YAML Generation")
    print("=" * 60)
    
    result_state = await agent.create_ci_pipeline(test_state)
    
    if result_state.get('ci_pipeline'):
        pipeline = result_state['ci_pipeline']
        
        print(f"\nGenerated {len(pipeline['github_workflows'])} workflow files:")
        for workflow_name, yaml_content in pipeline['github_workflows'].items():
            print(f"\n{'=' * 40}")
            print(f"Workflow: {workflow_name}")
            print(f"File: {pipeline['workflow_files'][workflow_name]}")
            print(f"{'=' * 40}")
            print(yaml_content)


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: CI Agent Basic Pipeline Creation")
    print("=" * 60)
    asyncio.run(test_ci_agent())
    
    print("\n" + "=" * 60)
    print("Test 2: CI Agent with Constraint Resolver Report")
    print("=" * 60)
    asyncio.run(test_ci_agent_with_constraint_report())
    
    print("\n" + "=" * 60)
    print("Test 3: CI Agent with Different Deployment Types")
    print("=" * 60)
    asyncio.run(test_ci_agent_different_deployment_types())
    
    print("\n" + "=" * 60)
    print("Test 4: CI Agent Workflow YAML Generation")
    print("=" * 60)
    asyncio.run(test_ci_agent_workflow_yaml_generation())
