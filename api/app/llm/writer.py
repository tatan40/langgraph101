"""Rédaction de la réponse par le modèle local (Ollama). Aucune décision n'est prise ici."""

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.config import Settings
from app.graph.state import Email, Reply
from app.temperaments import BY_ID

# Stratégie de réponse par tempérament : c'est ce qui rend la réponse « adaptée ».
STRATEGIES: dict[str, str] = {
    "joyeux": "Partage l'enthousiasme avec sobriété, réponds à la question éventuelle.",
    "reconnaissant": "Remercie en retour, brièvement et chaleureusement.",
    "neutre": "Réponds de façon factuelle et concise, accuse réception si besoin.",
    "inquiet": "Rassure avec des faits, explique les prochaines étapes, ne minimise pas la crainte.",
    "triste": "Fais preuve d'empathie sincère, sans formules toutes faites ni excès.",
    "frustre": "Reconnais l'attente et la gêne, excuse-toi, indique une action concrète pour avancer.",
    "enerve": "Reste calme, reconnais le problème sans te justifier longuement, excuse-toi, "
              "propose une action concrète. Ne réponds jamais au ton par le ton.",
    "moqueur": "Ignore l'ironie, ne la relève pas, traite le problème de fond avec sérieux.",
    "passif_agressif": "Réponds au fond, factuellement et cordialement. Ne relève pas la pique, "
                       "ne te justifie pas sur les relances.",
    "hostile": "Reste factuel et ferme, sans aucune provocation. N'admets aucune faute juridique, "
               "propose un échange avec un responsable.",
    "autre": "Accuse réception poliment et demande des précisions si nécessaire.",
}

# Traduction des contrôles Jev échoués en consignes de réécriture pour le 7B.
FEEDBACK_HINTS = {
    "polie": "sois plus poli et professionnel",
    "reconnait_emotion": "tiens compte de l'état d'esprit de l'auteur",
    "sans_engagement_invente": "retire toute promesse précise (date, montant, remboursement)",
    "sans_sarcasme": "supprime toute ironie ou tout reproche",
    "traite_la_demande": "réponds précisément à la demande de l'auteur",
    "en_francais": "rédige entièrement en français",
}

SYSTEM = """Tu rédiges des réponses à des emails, en français, pour un service client.
Le tempérament de l'auteur a été analysé : {label} (intensité {intensite:.1f} sur 3).
Stratégie à suivre : {strategy}

Règles :
- Réponds uniquement en français, en 60 à 150 mots, ton professionnel.
- Ne promets rien de précis (date, montant, remboursement, geste commercial) : propose plutôt de vérifier.
- Pas d'ironie, pas de reproche envers l'auteur.
- Signe « Le service client ».
Renvoie un objet JSON avec les champs "subject" et "body"."""


class _ReplySchema(BaseModel):
    subject: str = Field(description="Objet de la réponse, commençant par « Re : »")
    body: str = Field(description="Corps de la réponse")


class OllamaWriter:
    def __init__(self, settings: Settings):
        llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
            num_predict=600,
        )
        self._llm = llm.with_structured_output(_ReplySchema, method="json_schema")

    async def write(self, email: Email, temperament: str, intensite: float,
                    feedback: list[str] | None = None) -> Reply:
        system = SYSTEM.format(label=BY_ID[temperament].label, intensite=intensite,
                               strategy=STRATEGIES[temperament])
        user = f"Objet : {email['subject']}\n\n{email['body']}"
        if feedback:
            user += ("\n\nUn premier brouillon a été refusé. Corrige ces points : "
                     + ", ".join(FEEDBACK_HINTS.get(f, f) for f in feedback))
        out: _ReplySchema = await self._llm.ainvoke([("system", system), ("user", user)])
        return {"subject": out.subject, "body": out.body}
