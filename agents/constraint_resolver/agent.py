from typing import Dict, Any, Optional
import json
import re
from langchain_core.messages import HumanMessage, AIMessage
from core.state.models import AgentState, ConstraintResolverReport
from core.llm.config import get_llm, get_prompt_template
from core.state.persistence import state_manager
from core.models.model_artifact import ModelArtifactManager
from loguru import logger


class ConstraintResolverAgent:
    """
    Constraint Resolver Agent - Analyzes deployment feasibility
    Determines if model deployment requirements can be met given infrastructure constraints
    """
    
    def __init__(self):
        self.llm = get_llm()
        self.model_manager = ModelArtifactManager()
        self.system_prompt = """You are a Constraint Resolver Agent for AI model deployment. 
Your task is to analyze whether a given model can be successfully deployed given the infrastructure constraints.

Analyze the following aspects:
1. Overall confidence score for deployment possibility (0-100)
2. Quantization levels possible (FP16, FP8, INT8, INT4) with size/speed/accuracy trade-offs
3. Parallelization possibilities (tensor, pipeline, expert, data parallelism)
4. Recommended weight format (safetensors, gguf, onnx, tensorrt engine)
5. Recommended engine type (vllm, tensor-rt-llm, triton, bentoml, sglang, llama.cpp)

Provide specific, technical recommendations based on:
- Model size and architecture
- Available GPU memory and compute
- Latency requirements
- Deployment type (Kubernetes, Docker, etc.)

IMPORTANT: You must respond with a valid JSON object in the following format:
{{
    "overall_confidence_score": <number between 0-100>,
    "quantization_levels_possible": [
        {{"level": "FP16", "size_gb": <number>, "speed_multiplier": <number>, "accuracy_loss": "<description>"}},
        {{"level": "FP8", "size_gb": <number>, "speed_multiplier": <number>, "accuracy_loss": "<description>"}},
        {{"level": "INT8", "size_gb": <number>, "speed_multiplier": <number>, "accuracy_loss": "<description>"}},
        {{"level": "INT4", "size_gb": <number>, "speed_multiplier": <number>, "accuracy_loss": "<description>"}}
    ],
    "parallelization_possible": {{
        "tensor": <boolean>,
        "pipeline": <boolean>,
        "expert": <boolean>,
        "data": <boolean>
    }},
    "weight_format": "<recommended format>",
    "engine_type": "<recommended engine>",
    "deployment_feasible": <boolean>,
    "recommendations": ["<recommendation 1>", "<recommendation 2>", ...]
}}"""
    
    async def analyze_constraints(self, state: AgentState) -> AgentState:
        """
        Analyze deployment constraints and generate feasibility report
        
        Args:
            state: Current agent state with model_id, infrastructure_details, etc.
            
        Returns:
            Updated state with constraint_resolver_report
        """
        logger.info(f"Constraint Resolver analyzing model: {state['model_id']}")
        
        # Update current agent in state
        state["current_agent"] = "constraint_resolver"
        
        # Save state to persistence
        state_manager.save_state(
            state["deployment_conversation_id"],
            state,
            "constraint_resolver"
        )
        
        try:
            # Process model artifact if provided
            model_requirements = {}
            if state.get("model_source_path"):
                logger.info(f"Processing model artifact from: {state['model_source_path']}")
                from pathlib import Path
                model_path = Path(state["model_source_path"])
                if model_path.exists():
                    artifact = self.model_manager._analyze_model(model_path, state["model_id"])
                    state["model_artifact"] = artifact
                    model_requirements = self.model_manager.get_model_requirements(artifact)
                    logger.info(f"Model requirements extracted: {model_requirements}")
            
            # Prepare analysis prompt with model requirements
            analysis_prompt = self._prepare_analysis_prompt(state, model_requirements)
            
            # Get LLM response
            prompt_template = get_prompt_template(self.system_prompt)
            chain = prompt_template | self.llm
            
            response = await chain.ainvoke({"input": analysis_prompt})
            
            # Log the raw LLM response for debugging
            logger.info(f"Raw LLM response: {response.content[:500]}")  # Log first 500 chars
            
            # Parse response into structured report
            constraint_report = self._parse_constraint_report(response.content, state)
            
            # Update state
            state["constraint_resolver_report"] = constraint_report
            confidence_score = constraint_report['overall_confidence_score']
            state["messages"].append(AIMessage(content=f"Constraint analysis complete. Confidence score: {confidence_score}%"))
            
            # Save updated state
            state_manager.save_state(
                state["deployment_conversation_id"],
                state,
                "constraint_resolver"
            )
            
            logger.info(f"Constraint analysis complete for {state['model_id']}: {constraint_report['overall_confidence_score']}% confidence")
            
        except Exception as e:
            logger.error(f"Error in constraint analysis: {e}")
            state["errors"].append(f"Constraint Resolver error: {str(e)}")
            state["messages"].append(AIMessage(content=f"Error in constraint analysis: {str(e)}"))
        
        return state
    
    def _prepare_analysis_prompt(self, state: AgentState, model_requirements: Optional[Dict[str, Any]] = None) -> str:
        """Prepare the analysis prompt for the LLM"""
        prompt = f"""
Model ID: {state['model_id']}
Latency Requirement: {state.get('latency_requirement', 'Not specified')}
Deployment Type: {state.get('deployment_type', 'Not specified')}
"""
        
        # Add model requirements if available
        if model_requirements:
            prompt += f"""
Model Specifications:
- Architecture: {model_requirements.get('architecture', 'Unknown')}
- Framework: {model_requirements.get('framework', 'Unknown')}
- Estimated Memory Required: {model_requirements.get('estimated_memory_gb', 'Unknown')} GB
- Parameter Count: {model_requirements.get('parameter_count', 'Unknown')}
- Context Length: {model_requirements.get('context_length', 'Unknown')}
- Weight Format: {model_requirements.get('supported_formats', ['Unknown'])[0]}
"""
        
        prompt += f"""
Infrastructure Details:
{self._format_infrastructure_details(state.get('infrastructure_details', {}))}

Please analyze if this deployment is feasible and provide detailed recommendations.
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
    
    def _parse_constraint_report(self, llm_response: str, state: AgentState) -> ConstraintResolverReport:
        """
        Parse LLM response into structured constraint report
        
        This method attempts to extract JSON from the LLM response and parse it
        into the structured ConstraintResolverReport format.
        """
        try:
            # Remove markdown code blocks if present
            cleaned_response = llm_response
            # Remove ```json and ``` markers
            cleaned_response = re.sub(r'```json\s*', '', cleaned_response)
            cleaned_response = re.sub(r'```\s*', '', cleaned_response)
            
            # Try to parse the entire response as JSON first
            try:
                parsed_data = json.loads(cleaned_response.strip())
                logger.info(f"Successfully parsed full response as JSON")
            except json.JSONDecodeError:
                # If that fails, try to extract JSON object with proper nesting
                # Find the first { and last } to extract the complete JSON object
                first_brace = cleaned_response.find('{')
                last_brace = cleaned_response.rfind('}')
                
                if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
                    json_str = cleaned_response[first_brace:last_brace + 1]
                    logger.info(f"Extracted JSON: {json_str[:200]}...")  # Log first 200 chars
                    parsed_data = json.loads(json_str)
                else:
                    # If no JSON found, create a basic report from the text response
                    logger.warning("No JSON found in LLM response, creating basic report from text")
                    return self._create_basic_report_from_text(llm_response, state)
                
            # Validate and structure the parsed data
            return {
                "model_id": state["model_id"],
                "overall_confidence_score": float(parsed_data.get("overall_confidence_score", 0)),
                "quantization_levels_possible": parsed_data.get("quantization_levels_possible", []),
                "parallelization_possible": parsed_data.get("parallelization_possible", {}),
                "weight_format": parsed_data.get("weight_format", "safetensors"),
                "engine_type": parsed_data.get("engine_type", "vllm"),
                "deployment_feasible": bool(parsed_data.get("deployment_feasible", False)),
                "recommendations": parsed_data.get("recommendations", [])
            }
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return self._create_basic_report_from_text(llm_response, state)
        except Exception as e:
            logger.error(f"Error parsing constraint report: {e}")
            return self._create_error_report(state, str(e))
    
    def _create_basic_report_from_text(self, text_response: str, state: AgentState) -> ConstraintResolverReport:
        """Create a basic report when JSON parsing fails"""
        # Extract confidence score from text if possible
        confidence_match = re.search(r'confidence[:\s]*(\d+)', text_response, re.IGNORECASE)
        confidence_score = float(confidence_match.group(1)) if confidence_match else 50.0
        
        return {
            "model_id": state["model_id"],
            "overall_confidence_score": confidence_score,
            "quantization_levels_possible": [],
            "parallelization_possible": {},
            "weight_format": "safetensors",
            "engine_type": "vllm",
            "deployment_feasible": confidence_score > 50,
            "recommendations": ["Analysis completed but JSON parsing failed - review text response"]
        }
    
    def _create_error_report(self, state: AgentState, error_message: str) -> ConstraintResolverReport:
        """Create an error report when parsing fails completely"""
        return {
            "model_id": state["model_id"],
            "overall_confidence_score": 0.0,
            "quantization_levels_possible": [],
            "parallelization_possible": {},
            "weight_format": "unknown",
            "engine_type": "unknown",
            "deployment_feasible": False,
            "recommendations": [f"Error during analysis: {error_message}"]
        }