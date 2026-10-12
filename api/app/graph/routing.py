"""Politique de routage : du code pur, sans appel réseau. Jev juge, ce code décide."""

from app.config import Settings
from app.graph.state import Analysis, Decision, EmailState, Route, Verification
from app.temperaments import BY_ID


def decide_after_analysis(a: Analysis, s: Settings) -> Decision:
    label = BY_ID[a["temperament"]].label
    if a["escalade"] > s.escalade_threshold or a["temperament"] == "hostile":
        return {"route": "human_review",
                "reason": f"Revue humaine obligatoire : {label}, risque d'escalade {a['escalade']:.0%}."}
    if a["confidence"] < s.min_confidence:
        first, second = sorted(a["probabilities"], key=a["probabilities"].get, reverse=True)[:2]
        return {"route": "human_review",
                "reason": f"Confiance faible ({a['confidence']:.2f}) : hésitation entre "
                          f"{BY_ID[first].label} et {BY_ID[second].label}."}
    if a["attend_reponse"] < s.reply_expected_min:
        return {"route": "finalize",
                "reason": f"{label} : aucune réponse attendue ({a['attend_reponse']:.0%})."}
    return {"route": "draft",
            "reason": f"{label} (confiance {a['confidence']:.2f}) : rédaction automatique."}


def decide_after_verify(v: Verification, attempts: int, s: Settings) -> Decision:
    if v["passed"]:
        return {"route": "finalize", "reason": "Brouillon validé par le contrôle qualité."}
    if attempts < s.max_attempts:
        return {"route": "draft",
                "reason": f"Contrôle qualité échoué ({', '.join(v['failed'])}) : réécriture."}
    return {"route": "human_review",
            "reason": f"Toujours en échec après {attempts} brouillons ({', '.join(v['failed'])})."}


def decide_after_human(state: EmailState) -> Route:
    h = state["human"]
    if h["action"] == "approve" and not state.get("draft"):
        return "draft"      # l'humain valide (ou corrige) la catégorie : on rédige
    return "finalize"       # approve d'un brouillon existant, edit, ou reject


# Fonction passée à add_conditional_edges : elle lit la décision déjà écrite dans l'état.
def route_from_decision(state: EmailState) -> Route:
    return state["decision"]["route"]
