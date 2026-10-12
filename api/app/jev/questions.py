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
        "demande_humain": (
            "L'auteur de `email` demande-t-il explicitement à parler à une personne, à être rappelé "
            "ou à joindre un responsable ou un conseiller ?"
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
        "demande_humain": (
            "Does the author of the French message `email` explicitly ask to speak to a person, to be "
            "called back, or to reach a manager or an advisor?"
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
        "demande_humain": Noul(instructions=txt["demande_humain"]),
    }
    for t in TEMPERAMENTS:
        desc = _desc(t, lang)
        desc_text = desc if isinstance(desc, str) else desc["description"]
        questions[f"ton_{t.id}"] = Noul(instructions=txt["ton"].format(desc=desc_text))
    return questions


def analysis_state(body: str, subject: str | None = None) -> dict:
    return {"email": {"subject": subject or "", "body": body}}


# Contrôle qualité du brouillon : chaque Noul est formulé pour que « oui » = critère respecté.
VERIFICATION_QUESTIONS: dict[str, dict[str, str]] = {
    "polie": {
        "fr": "La réponse `reply` est-elle polie et professionnelle ?",
        "en": "Is the reply `reply` polite and professional?",
    },
    "reconnait_emotion": {
        "fr": "La réponse `reply` tient-elle compte de l'état d'esprit de l'auteur de `email` "
              "(sans le nier ni en rajouter) ?",
        "en": "Does the reply `reply` take into account the state of mind of the author of `email` "
              "(without dismissing or exaggerating it)?",
    },
    "sans_engagement_invente": {
        "fr": "La réponse `reply` évite-t-elle toute promesse précise (date, montant, remboursement, "
              "geste commercial) que rien dans `email` ne justifie ?",
        "en": "Does the reply `reply` avoid any specific promise (date, amount, refund, compensation) "
              "that nothing in `email` justifies?",
    },
    "sans_sarcasme": {
        "fr": "La réponse `reply` est-elle exempte d'ironie, de sarcasme ou de reproche envers l'auteur ?",
        "en": "Is the reply `reply` free of irony, sarcasm, or reproach toward the author?",
    },
    "traite_la_demande": {
        "fr": "La réponse `reply` répond-elle explicitement à chacune des demandes formulées dans `email` "
              "(et pas seulement à son sujet général) ?",
        "en": "Does the reply `reply` explicitly address each request made in `email` "
              "(not just its general topic)?",
    },
    "sans_fait_invente": {
        "fr": "La réponse `reply` s'abstient-elle d'affirmer des faits ou des actions en cours "
              "(vérification, traitement, solution) que rien dans `email` ne permet de connaître ?",
        "en": "Does the reply `reply` refrain from asserting facts or ongoing actions (checking, "
              "processing, a solution) that nothing in `email` makes it possible to know?",
    },
    "en_francais": {
        "fr": "La réponse `reply` est-elle entièrement rédigée en français ?",
        "en": "Is the reply `reply` written entirely in French?",
    },
}


def verification_questions(lang: Lang = "fr") -> dict[str, Question]:
    return {k: Noul(instructions=v[lang]) for k, v in VERIFICATION_QUESTIONS.items()}


def verification_state(email: dict, reply: dict) -> dict:
    return {"email": email, "reply": reply}
