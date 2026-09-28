from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from core.config.settings import settings


def get_llm():
    """Get configured LLM instance using local Ollama for development"""
    return ChatOllama(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        base_url=settings.ollama_base_url
    )


def get_vllm_llm():
    """Get configured LLM instance using vLLM for production deployment"""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        base_url=settings.vllm_base_url,
        api_key="dummy"  # vLLM doesn't require real API key but OpenAI client expects one
    )


def get_prompt_template(system_prompt: str, human_prompt: str = "{input}"):
    """Create a chat prompt template"""
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt)
    ])