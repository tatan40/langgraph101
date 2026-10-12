"""Les nodes du graphe. Chacun lit l'état et renvoie un patch ; aucun ne choisit la suite.

Les dépendances (Jev, Ollama) sont injectées : les tests passent des doublures.
"""

from typing import Protocol

from langgraph.types import interrupt

from app.config import Settings
from app.graph.routing import decide_after_analysis, decide_after_verify
from app.graph.state import Analysis, Email, EmailState, Reply, Verification


class Judge(Protocol):
    async def analyze(self, email: Email) -> Analysis: ...
    async def verify(self, email: Email, reply: Reply) -> Verification: ...


class Writer(Protocol):
    async def write(self, email: Email, temperament: str, intensite: float,
                    feedback: list[str] | None = None) -> Reply: ...


def current_temperament(state: EmailState) -> str:
    """La catégorie corrigée par l'humain l'emporte sur celle de Jev."""
    human = state.get("human") or {}
    return human.get("temperament") or state["analysis"]["temperament"]


def make_nodes(judge: Judge, writer: Writer, s: Settings):
    async def analyze(state: EmailState) -> dict:
        analysis = await judge.analyze(state["email"])
        return {"analysis": analysis, "decision": decide_after_analysis(analysis, s), "attempts": 0}

    async def draft(state: EmailState) -> dict:
        previous = state.get("verification")
        feedback = previous["failed"] if previous and not previous["passed"] else None
        reply = await writer.write(state["email"], current_temperament(state),
                                   state["analysis"]["intensite"], feedback)
        return {"draft": reply, "drafts": [reply], "attempts": state.get("attempts", 0) + 1}

    async def verify(state: EmailState) -> dict:
        v = await judge.verify(state["email"], state["draft"])
        return {"verification": v, "decision": decide_after_verify(v, state["attempts"], s)}

    def human_review(state: EmailState) -> dict:
        # interrupt() met le graphe en pause et renvoie la valeur fournie à la reprise
        # via Command(resume=...). Au moment de la reprise, LangGraph RÉ-EXÉCUTE ce node
        # depuis le début : rien avant interrupt() ne doit avoir d'effet de bord.
        decision = interrupt({
            "reason": state["decision"]["reason"],
            "analysis": state["analysis"],
            "draft": state.get("draft"),
            "verification": state.get("verification"),
        })
        return {"human": decision}

    def finalize(state: EmailState) -> dict:
        human = state.get("human") or {}
        temperament = current_temperament(state)
        if human.get("action") == "reject":
            return {"final": {"status": "rejected", "reply": None, "temperament": temperament}}
        if human.get("action") == "edit":
            return {"final": {"status": "replied", "reply": human["reply"], "temperament": temperament}}
        if state.get("draft"):
            return {"final": {"status": "replied", "reply": state["draft"], "temperament": temperament}}
        return {"final": {"status": "no_reply", "reply": None, "temperament": temperament}}

    return {"analyze": analyze, "draft": draft, "verify": verify,
            "human_review": human_review, "finalize": finalize}
