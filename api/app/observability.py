"""Traçage Langfuse. Désactivé proprement si aucune clé n'est configurée.

Ce qui est tracé :
  - le graphe LangGraph et chaque node, via le CallbackHandler LangChain ;
  - les appels Ollama (ChatOllama), automatiquement par le même handler ;
  - les appels Jev, via @observe dans app/jev/client.py.
Un run = une session Langfuse (session_id = thread_id) : la pause humaine et la reprise
apparaissent comme des traces successives de la même session.
"""

from contextlib import contextmanager

from langfuse import Langfuse, get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

from app.config import Settings

_enabled = False


def init_tracing(s: Settings) -> bool:
    """Initialise le client Langfuse global. Renvoie False si le traçage est désactivé."""
    global _enabled
    _enabled = bool(s.langfuse_public_key and s.langfuse_secret_key)
    # Langfuse() enregistre un client global, réutilisé par get_client(), @observe et le handler.
    Langfuse(
        public_key=s.langfuse_public_key,
        secret_key=s.langfuse_secret_key.get_secret_value() if s.langfuse_secret_key else None,
        base_url=s.langfuse_base_url,
        tracing_enabled=_enabled,
    )
    return _enabled


def callbacks() -> list:
    """Callbacks à passer dans la config du graphe : config={"callbacks": callbacks()}."""
    return [CallbackHandler()] if _enabled else []


@contextmanager
def trace_run(thread_id: str, email: dict):
    """Ouvre une observation racine pour tout le run (reprises après pause comprises).

    Sans elle, le handler LangChain et @observe n'ont pas de parent commun : les appels Jev
    partiraient dans des traces séparées, et chaque reprise créerait une nouvelle trace.
    Renvoie l'observation racine (ou None si le traçage est désactivé) pour y écrire la sortie.
    """
    if not _enabled:
        yield None
        return
    with get_client().start_as_current_observation(name="temperament-agent", input=email) as root:
        with propagate_attributes(session_id=thread_id, trace_name="temperament-agent"):
            yield root


def record_jev_call(state: dict, model: str, input_tokens: int | None, output: dict) -> None:
    """Complète l'observation Jev en cours (créée par @observe) : entrée, modèle, usage, sortie."""
    if _enabled:
        get_client().update_current_generation(
            input=state,
            model=model,
            usage_details={"input": input_tokens or 0},
            output=output,
        )


def session_url(s: Settings, thread_id: str) -> str | None:
    if not _enabled:
        return None
    return f"{s.langfuse_base_url}/project/{s.langfuse_project_id}/sessions/{thread_id}"


def flush() -> None:
    if _enabled:
        get_client().flush()
