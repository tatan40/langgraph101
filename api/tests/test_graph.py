"""Tests du graphe sans réseau : Jev et Ollama sont remplacés par des doublures."""

import uuid

from langgraph.types import Command

from app.config import Settings
from app.graph.build import build_graph

S = Settings(_env_file=None)


def analysis(temperament="neutre", confidence=0.95, attend=0.9, escalade=0.0, humain=0.0):
    return {"temperament": temperament, "confidence": confidence,
            "probabilities": {temperament: confidence, "frustre": 1 - confidence},
            "tons": {}, "intensite": 1.0, "attend_reponse": attend, "escalade": escalade,
            "demande_humain": humain}


class FakeJudge:
    def __init__(self, analysis, verdicts):
        self._analysis = analysis
        self._verdicts = list(verdicts)   # un booléen par appel à verify

    async def analyze(self, email):
        return self._analysis

    async def verify(self, email, reply):
        ok = self._verdicts.pop(0)
        return {"checks": {"polie": 0.9 if ok else 0.1}, "failed": [] if ok else ["polie"], "passed": ok}


class FakeWriter:
    def __init__(self):
        self.calls = []

    async def write(self, email, temperament, intensite, feedback=None):
        self.calls.append({"temperament": temperament, "feedback": feedback})
        return {"subject": "Re", "body": f"brouillon {len(self.calls)}"}


async def run(judge, writer, *resumes):
    """Lance le graphe, puis reprend après chaque pause avec les valeurs fournies."""
    graph = build_graph(judge, writer, S)
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    payload = {"email": {"subject": "s", "body": "b"}}
    pauses = []
    for resume in (None, *resumes):
        if resume is not None:
            payload = Command(resume=resume)
        await graph.ainvoke(payload, config)
        state = await graph.aget_state(config)
        if state.interrupts:
            pauses.append(state.interrupts[0].value)
    return state.values, pauses


async def test_chemin_nominal():
    judge, writer = FakeJudge(analysis(), [True]), FakeWriter()
    values, pauses = await run(judge, writer)
    assert values["final"]["status"] == "replied"
    assert values["attempts"] == 1 and not pauses


async def test_reecriture_puis_validation_avec_feedback():
    judge, writer = FakeJudge(analysis(), [False, True]), FakeWriter()
    values, _ = await run(judge, writer)
    assert values["attempts"] == 2
    assert writer.calls[1]["feedback"] == ["polie"]
    assert [d["body"] for d in values["drafts"]] == ["brouillon 1", "brouillon 2"]   # reducer


async def test_boucle_bornee_puis_revue_humaine():
    judge, writer = FakeJudge(analysis(), [False, False]), FakeWriter()
    values, pauses = await run(judge, writer, {"action": "approve"})
    assert len(writer.calls) == S.max_attempts
    assert "Toujours en échec" in pauses[0]["reason"]
    assert values["final"] == {"status": "replied", "reply": values["drafts"][-1], "temperament": "neutre"}


async def test_hostile_pause_avant_redaction_puis_rejet():
    judge, writer = FakeJudge(analysis("hostile", escalade=0.9), []), FakeWriter()
    values, pauses = await run(judge, writer, {"action": "reject"})
    assert pauses[0]["draft"] is None
    assert values["final"]["status"] == "rejected" and writer.calls == []


async def test_demande_a_parler_a_un_humain_pause_avant_redaction():
    judge, writer = FakeJudge(analysis("frustre", humain=0.9), [True]), FakeWriter()
    values, pauses = await run(judge, writer, {"action": "approve"})
    assert "parler à une personne" in pauses[0]["reason"] and pauses[0]["draft"] is None
    assert values["final"]["status"] == "replied"


async def test_confiance_faible_categorie_corrigee_par_humain():
    judge, writer = FakeJudge(analysis("moqueur", confidence=0.3), [True]), FakeWriter()
    values, pauses = await run(judge, writer, {"action": "approve", "temperament": "passif_agressif"})
    assert "Confiance faible" in pauses[0]["reason"]
    assert writer.calls[0]["temperament"] == "passif_agressif"
    assert values["final"]["temperament"] == "passif_agressif"


async def test_pas_de_reponse_attendue():
    judge, writer = FakeJudge(analysis("reconnaissant", attend=0.1), []), FakeWriter()
    values, _ = await run(judge, writer)
    assert values["final"]["status"] == "no_reply" and writer.calls == []


async def test_edition_humaine_du_brouillon():
    judge, writer = FakeJudge(analysis(), [False, False]), FakeWriter()
    edited = {"subject": "Re", "body": "texte humain"}
    values, _ = await run(judge, writer, {"action": "edit", "reply": edited})
    assert values["final"]["reply"] == edited


def test_structure_du_graphe():
    g = build_graph(None, None, S).get_graph()
    assert set(g.nodes) >= {"analyze", "draft", "verify", "human_review", "finalize"}
