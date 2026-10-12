"""Appels à Jev : analyse du tempérament et contrôle qualité d'un brouillon."""

from langfuse import observe
from typesafe_sdk import AsyncTypeSafeClient

from app.config import Settings
from app.graph.state import Analysis, Email, Reply, Verification
from app.jev.questions import (
    analysis_questions,
    analysis_state,
    verification_questions,
    verification_state,
)
from app.observability import record_jev_call
from app.temperaments import TEMPERAMENTS


class JevJudge:
    def __init__(self, client: AsyncTypeSafeClient, settings: Settings):
        self._client = client
        self._s = settings
        # Questions construites une fois : elles ne dépendent pas de l'email.
        self._analysis_q = analysis_questions(settings.jev_lang)
        self._verify_q = verification_questions(settings.jev_lang)

    # @observe crée une observation Langfuse de type « generation » autour de l'appel.
    # capture_input=False : on enregistre l'état envoyé à Jev plutôt que les arguments Python.
    @observe(name="jev.analyze", as_type="generation", capture_input=False, capture_output=False)
    async def analyze(self, email: Email) -> Analysis:
        state = analysis_state(email["body"], email["subject"])
        r = await self._client.system_one(state, self._analysis_q)
        choice = r.choices["temperament"]
        analysis: Analysis = {
            "temperament": choice.choice,
            "confidence": choice.confidence,
            "probabilities": dict(choice.probabilities),
            "tons": {t.id: r.nouls[f"ton_{t.id}"].noul for t in TEMPERAMENTS},
            "intensite": r.scores["intensite"].score,
            "attend_reponse": r.nouls["attend_reponse"].noul,
            "escalade": r.nouls["escalade"].noul,
            "demande_humain": r.nouls["demande_humain"].noul,
        }
        record_jev_call(state, r.model, r.usage.input_tokens, analysis)
        return analysis

    def _threshold(self, check: str) -> float:
        s = self._s
        return s.verify_threshold_strict if check in s.strict_checks else s.verify_threshold

    @observe(name="jev.verify", as_type="generation", capture_input=False, capture_output=False)
    async def verify(self, email: Email, reply: Reply) -> Verification:
        state = verification_state(email, reply)
        r = await self._client.system_one(state, self._verify_q)
        checks = {k: r.nouls[k].noul for k in self._verify_q}
        failed = [k for k, p in checks.items() if p < self._threshold(k)]
        verification: Verification = {"checks": checks, "failed": failed, "passed": not failed}
        record_jev_call(state, r.model, r.usage.input_tokens, verification)
        return verification
