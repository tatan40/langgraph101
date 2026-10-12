"""Appels à Jev : analyse du tempérament et contrôle qualité d'un brouillon."""

from typesafe_sdk import AsyncTypeSafeClient

from app.config import Settings
from app.graph.state import Analysis, Email, Reply, Verification
from app.jev.questions import (
    analysis_questions,
    analysis_state,
    verification_questions,
    verification_state,
)
from app.temperaments import TEMPERAMENTS


class JevJudge:
    def __init__(self, client: AsyncTypeSafeClient, settings: Settings):
        self._client = client
        self._s = settings
        # Questions construites une fois : elles ne dépendent pas de l'email.
        self._analysis_q = analysis_questions(settings.jev_lang)
        self._verify_q = verification_questions(settings.jev_lang)

    async def analyze(self, email: Email) -> Analysis:
        r = await self._client.system_one(analysis_state(email["body"], email["subject"]), self._analysis_q)
        choice = r.choices["temperament"]
        return {
            "temperament": choice.choice,
            "confidence": choice.confidence,
            "probabilities": dict(choice.probabilities),
            "tons": {t.id: r.nouls[f"ton_{t.id}"].noul for t in TEMPERAMENTS},
            "intensite": r.scores["intensite"].score,
            "attend_reponse": r.nouls["attend_reponse"].noul,
            "escalade": r.nouls["escalade"].noul,
        }

    async def verify(self, email: Email, reply: Reply) -> Verification:
        r = await self._client.system_one(verification_state(email, reply), self._verify_q)
        checks = {k: r.nouls[k].noul for k in self._verify_q}
        failed = [k for k, p in checks.items() if p < self._s.verify_threshold]
        return {"checks": checks, "failed": failed, "passed": not failed}
