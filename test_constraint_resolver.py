import asyncio
from agents.constraint_resolver import ConstraintResolverAgent
from core.state.models import AgentState


async def test_constraint_resolver():
    """Test the Constraint Resolver Agent"""
    
    # Initialize agent
    agent = ConstraintResolverAgent()
    
    # Create test state - can work with just model ID or with actual model files
    test_state = AgentState(
        messages=[],
        deployment_conversation_id="test-dep-001",
        model_id="fraud_model_v3",
        model_source_path=None,  # Can provide path to actual model files here
        latency_requirement="<100ms",
        deployment_type="kubernetes",
        infrastructure_details={
            "gpu_type": "NVIDIA A100",
            "gpu_memory_gb": 80,
            "gpu_count": 2,
            "cpu_cores": 64,
            "ram_gb": 256
        },
        errors=[]
    )
    
    print("Testing Constraint Resolver Agent...")
    print(f"Model ID: {test_state['model_id']}")
    print(f"Model Source Path: {test_state['model_source_path'] or 'None (using model ID only)'}")
    print(f"Latency Requirement: {test_state['latency_requirement']}")
    print(f"Deployment Type: {test_state['deployment_type']}")
    print()
    
    # Run analysis
    result_state = await agent.analyze_constraints(test_state)
    
    # Display results
    if result_state.get('constraint_resolver_report'):
        print("Constraint Analysis Results:")
        print(f"Confidence Score: {result_state['constraint_resolver_report']['overall_confidence_score']}%")
        print(f"Deployment Feasible: {result_state['constraint_resolver_report']['deployment_feasible']}")
        print(f"Recommended Engine: {result_state['constraint_resolver_report']['engine_type']}")
        print(f"Weight Format: {result_state['constraint_resolver_report']['weight_format']}")
        print()
        print("Quantization Options:")
        for quant in result_state['constraint_resolver_report']['quantization_levels_possible']:
            print(f"  - {quant['level']}: {quant['size_gb']}GB, {quant['speed_multiplier']}x speed")
        print()
        print("Parallelization Options:")
        for parallel_type, possible in result_state['constraint_resolver_report']['parallelization_possible'].items():
            status = "✓" if possible else "✗"
            print(f"  {status} {parallel_type}")
        print()
        print("Recommendations:")
        for rec in result_state['constraint_resolver_report']['recommendations']:
            print(f"  - {rec}")
    else:
        print("No constraint resolver report generated - check logs for errors")


async def test_with_model_files():
    """Test with actual model files (when available)"""
    
    # Initialize agent
    agent = ConstraintResolverAgent()
    
    # Create test state with model files
    test_state = AgentState(
        messages=[],
        deployment_conversation_id="test-dep-002",
        model_id="qwen2.5-7b",
        model_source_path="/path/to/your/model/files",  # Replace with actual path
        latency_requirement="<50ms",
        deployment_type="kubernetes",
        infrastructure_details={
            "gpu_type": "NVIDIA A100",
            "gpu_memory_gb": 80,
            "gpu_count": 1,
            "cpu_cores": 32,
            "ram_gb": 128
        },
        errors=[]
    )
    
    print("Testing Constraint Resolver Agent with Model Files...")
    print(f"Model ID: {test_state['model_id']}")
    print(f"Model Source Path: {test_state['model_source_path']}")
    print()
    
    # Run analysis
    result_state = await agent.analyze_constraints(test_state)
    
    # Display results
    if result_state.get('constraint_resolver_report'):
        print("Constraint Analysis Results:")
        print(f"Confidence Score: {result_state['constraint_resolver_report']['overall_confidence_score']}%")
        print(f"Deployment Feasible: {result_state['constraint_resolver_report']['deployment_feasible']}")
        
        if result_state.get('model_artifact'):
            print(f"\nModel Artifact Analysis:")
            artifact = result_state['model_artifact']
            print(f"  Architecture: {artifact.architecture}")
            print(f"  Framework: {artifact.framework}")
            print(f"  Weight Format: {artifact.weight_format}")
            print(f"  Model Size: {artifact.model_size_gb} GB" if artifact.model_size_gb else "  Model Size: Unknown")


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: Constraint Resolver with Model ID only")
    print("=" * 60)
    asyncio.run(test_constraint_resolver())
    
    print("\n" + "=" * 60)
    print("Test 2: Constraint Resolver with Model Files (when available)")
    print("=" * 60)
    print("Note: Update model_source_path with actual model file path")
    # asyncio.run(test_with_model_files())  # Uncomment when you have model files