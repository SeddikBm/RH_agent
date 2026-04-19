"""
Service LLM — Wrapper autour de GroqCloud via LangChain.
Fournit des appels structurés (Pydantic output) avec retry.
"""
import json
from typing import Optional, Type, TypeVar

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from loguru import logger
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings

settings = get_settings()

T = TypeVar("T", bound=BaseModel)


def get_llm(temperature: float = 0.1) -> ChatGroq:
    """Retourne une instance configurée du LLM GroqCloud."""
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=temperature,
        max_retries=3,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def invoke_structured(
    prompt_template: str,
    variables: dict,
    output_schema: Type[T],
    temperature: float = 0.1,
) -> T:
    """
    Invoque le LLM avec un prompt structuré et parse la réponse
    selon le schéma Pydantic fourni.
    """
    llm = get_llm(temperature=temperature)

    # Injecter le schéma directement (évite le conflit de variables {schema_json})
    schema_json = json.dumps(output_schema.model_json_schema(), indent=2, ensure_ascii=False)
    system_content = (
        "Tu es un assistant RH expert dans l'analyse de CVs et de fiches de poste. "
        "Tu réponds UNIQUEMENT en JSON valide, strictement conforme au schéma fourni. "
        "Ne génère aucun texte en dehors du JSON.\n\n"
        "Schéma de réponse attendu :\n" + schema_json
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_content),
        ("human", prompt_template),
    ])

    # Formater et invoquer
    formatted_prompt = prompt.format_messages(**variables)
    logger.debug(f"🤖 Appel LLM ({settings.groq_model}) | temp={temperature}")

    response = await llm.ainvoke(formatted_prompt)

    # Parser la réponse JSON
    raw_text = response.content.strip()

    # Nettoyer les balises markdown si présentes
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Trouver le début et la fin du bloc JSON
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        raw_text = "\n".join(lines[start:end]).strip()

    # Extraire uniquement le JSON valide (du premier { au dernier })
    first_brace = raw_text.find("{")
    last_brace = raw_text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        raw_text = raw_text[first_brace:last_brace + 1]

    try:
        parsed_data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur JSON parsing: {e}\nRaw text: {raw_text[:500]}")
        raise

    result = output_schema(**parsed_data)
    logger.debug(f"✅ Réponse LLM parsée avec succès")
    return result


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
