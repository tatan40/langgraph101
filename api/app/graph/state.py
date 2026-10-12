"""État partagé du graphe. Chaque node lit l'état et renvoie un patch (un dict partiel)."""

import operator
from typing import Annotated, Literal, TypedDict


class Email(TypedDict):
    subject: str
    body: str


class Reply(TypedDict):
    subject: str
    body: str


class Analysis(TypedDict):
    temperament: str
    confidence: float
    probabilities: dict[str, float]
    tons: dict[str, float]          # probabilité de chaque ton secondaire
    intensite: float                # 0 (aucune émotion) à 3 (émotion dominante)
    attend_reponse: float
    escalade: float


Route = Literal["draft", "human_review", "finalize"]


class Decision(TypedDict):
    route: Route
    reason: str                     # explication lisible, affichée dans l'UI


class Verification(TypedDict):
    checks: dict[str, float]        # probabilité que chaque critère soit respecté
    failed: list[str]
    passed: bool


class HumanDecision(TypedDict, total=False):
    action: Literal["approve", "edit", "reject"]
    temperament: str                # catégorie corrigée par l'humain
    reply: Reply                    # réponse réécrite par l'humain (action "edit")


class Final(TypedDict):
    status: Literal["replied", "no_reply", "rejected"]
    reply: Reply | None
    temperament: str


class EmailState(TypedDict, total=False):
    email: Email
    analysis: Analysis
    decision: Decision
    draft: Reply | None
    # Reducer `operator.add` : chaque patch {"drafts": [x]} est AJOUTÉ à la liste
    # au lieu de la remplacer. On garde ainsi tous les brouillons successifs.
    drafts: Annotated[list[Reply], operator.add]
    verification: Verification | None
    attempts: int
    human: HumanDecision | None
    final: Final
