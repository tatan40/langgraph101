"""Questions Jev pour l'analyse du tempérament. Une seule requête, questions en parallèle."""

from typing import Literal

from typesafe_sdk import Choice, Noul, Question, Score

from app.temperaments import ALL_CHOICES, TEMPERAMENTS, Temperament

Lang = Literal["fr", "en"]

_TEXT = {
    "fr": {
        "temperament": "Quel est le tempérament dominant de l'auteur du message `email` ?",
        "ton": "Le message `email` exprime-t-il, même de façon secondaire, ce tempérament : {desc}",
        "intensite": "Avec quelle intensité l'émotion de l'auteur s'exprime-t-elle dans `email` ?",
        "intensite_levels": [
            "Aucune émotion perceptible : message purement factuel.",
            "Émotion légère, perceptible à un ou deux mots près.",
            "Émotion nette, qui colore une bonne partie du message.",
            "Émotion qui domine tout le message (majuscules, exclamations, vocabulaire fort).",
        ],
        "attend_reponse": "L'auteur de `email` attend-il une réponse ou une action de la part du destinataire ?",
        "escalade": (
            "Le message `email` contient-il une menace, une mise en demeure, une intention d'action "
            "en justice ou un risque pour la sécurité d'une personne ?"
        ),
    },
    "en": {
        "temperament": "What is the dominant temperament of the author of the French message `email`?",
        "ton": "Does the French message `email` express, even secondarily, this temperament: {desc}",
        "intensite": "How intensely is the author's emotion expressed in the French message `email`?",
        "intensite_levels": [
            "No perceptible emotion: purely factual message.",
            "Mild emotion, noticeable in one or two words.",
            "Clear emotion that colors a good part of the message.",
            "Emotion dominates the whole message (capitals, exclamations, strong wording).",
        ],
        "attend_reponse": "Does the author of the French message `email` expect a reply or an action from the recipient?",
        "escalade": (
            "Does the French message `email` contain a threat, a formal notice, an intent to take "
            "legal action, or a risk to someone's safety?"
        ),
    },
}


def _desc(t: Temperament, lang: Lang):
    return t.fr if lang == "fr" else t.en


def analysis_questions(lang: Lang = "fr") -> dict[str, Question]:
    txt = _TEXT[lang]
    questions: dict[str, Question] = {
        "temperament": Choice(
            instructions=txt["temperament"],
            criteria={t.id: _desc(t, lang) for t in ALL_CHOICES},
        ),
        "intensite": Score(instructions=txt["intensite"], criteria=txt["intensite_levels"]),
        "attend_reponse": Noul(instructions=txt["attend_reponse"]),
        "escalade": Noul(instructions=txt["escalade"]),
    }
    for t in TEMPERAMENTS:
        desc = _desc(t, lang)
        desc_text = desc if isinstance(desc, str) else desc["description"]
        questions[f"ton_{t.id}"] = Noul(instructions=txt["ton"].format(desc=desc_text))
    return questions


def analysis_state(body: str, subject: str | None = None) -> dict:
    return {"email": {"subject": subject or "", "body": body}}
