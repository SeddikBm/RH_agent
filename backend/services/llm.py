"""
Service LLM — Wrapper autour de OpenAI via LangChain.
Fournit des appels structurés (Pydantic output) avec retry.
"""
import json
from typing import Optional, Type, TypeVar

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings

settings = get_settings()

T = TypeVar("T", bound=BaseModel)


def get_llm(temperature: float = 0.1) -> ChatOpenAI:
    """Retourne une instance configurée du LLM OpenAI."""
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=temperature,
        max_retries=3,
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    reraise=True,
)
async def invoke_structured(
    prompt_template: str,
    variables: dict,
    output_schema: Type[T],
    temperature: float = 0.1,
) -> T:
    """
    Invoque le LLM avec un prompt structuré et parse la réponse en JSON
    via la fonctionnalité native with_structured_output d'OpenAI.
    """
    llm = get_llm(temperature=temperature)
    structured_llm = llm.with_structured_output(output_schema)
    
    from langchain_core.messages import SystemMessage, HumanMessage
    
    system_content = (
        "Tu es un assistant RH expert dans l'analyse de CVs et de fiches de poste. "
        "Réponds de manière précise et rigoureuse."
    )
    
    human_prompt = ChatPromptTemplate.from_template(prompt_template)
    formatted_human = human_prompt.format(**variables)

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=formatted_human),
    ]

    logger.debug(f"🤖 Appel LLM ({settings.openai_model}) | temp={temperature}")

    try:
        response = await structured_llm.ainvoke(messages)
        logger.debug("✅ Réponse LLM parsée avec succès via structured output OpenAI")
        return response
    except Exception as e:
        logger.error(f"❌ Erreur invoke_structured: {e}")
        raise


async def invoke_text(
    prompt_template: str,
    variables: dict,
    temperature: float = 0.3,
) -> str:
    """
    Invoque le LLM et retourne la réponse en texte brut.
    """
    llm = get_llm(temperature=temperature)

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Tu es un assistant RH expert en analyse de candidatures. "
            "Réponds en français, de manière professionnelle et concise."
        )),
        ("human", prompt_template),
    ])

    formatted_prompt = prompt.format_messages(**variables)
    response = await llm.ainvoke(formatted_prompt)
    return response.content.strip()

