"""Lancer le graphe en ligne de commande.

  uv run python -m app.cli "Texte de l'email"
  uv run python -m app.cli --id t25            # un email du jeu de test
  uv run python -m app.cli --mermaid           # affiche le graphe
  uv run python -m app.cli --id t28 --auto approve   # répond à la pause sans interaction
"""

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from langgraph.types import Command
from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy

from app.config import settings
from app.graph.build import build_graph
from app.jev.client import JevJudge
from app.llm.writer import OllamaWriter
from app.temperaments import ALL_CHOICES, BY_ID

DATASET = Path(__file__).resolve().parents[1] / "eval" / "dataset.jsonl"


### Construit l'email à traiter : depuis le jeu de test (--id) ou depuis le texte tapé.
def load_email(args) -> dict:
    if args.id:
        for line in DATASET.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            if item["id"] == args.id:
                return {"subject": item["subject"], "body": item["text"]}
        raise SystemExit(f"Id inconnu : {args.id}")
    return {"subject": args.subject or "", "body": args.text}


### Affiche dans le terminal ce qu'un node du graphe vient de produire (analyse, brouillon, contrôles…).
def show(node: str, patch: dict) -> None:
    print(f"\n● {node}")
    if a := patch.get("analysis"):
        top = sorted(a["probabilities"].items(), key=lambda kv: kv[1], reverse=True)[:3]
        print(f"  tempérament : {BY_ID[a['temperament']].label}  (confiance {a['confidence']:.2f})")
        print("  top 3       : " + ", ".join(f"{BY_ID[k].label} {v:.0%}" for k, v in top))
        tons = [BY_ID[t].label for t, p in a["tons"].items()
                if p >= settings.tons_display_threshold and t != a["temperament"]]
        print(f"  tons second.: {', '.join(tons) or '—'}")
        print(f"  intensité   : {a['intensite']:.1f}/3   attend une réponse : {a['attend_reponse']:.0%}"
              f"   escalade : {a['escalade']:.0%}")
    if d := patch.get("draft"):
        print(f"  brouillon n°{patch['attempts']} — {d['subject']}")
        print("  " + d["body"].replace("\n", "\n  "))
    if v := patch.get("verification"):
        print("  contrôles   : " + ", ".join(f"{k} {'✓' if p >= settings.verify_threshold else '✗'} {p:.0%}"
                                           for k, p in v["checks"].items()))
    if dec := patch.get("decision"):
        print(f"  → {dec['route']} : {dec['reason']}")
    if h := patch.get("human"):
        print(f"  décision humaine : {h}")
    if f := patch.get("final"):
        print(f"  statut final : {f['status']}")


### Pendant une pause du graphe, demande à l'humain d'approuver, corriger, rejeter ou éditer.
def ask_human(payload: dict, auto: str | None) -> dict:
    print(f"\n⏸  PAUSE — {payload['reason']}")
    if auto:
        print(f"  (réponse automatique : {auto})")
        return {"action": auto}
    has_draft = payload.get("draft") is not None
    choices = "[a]pprouver  [c]orriger la catégorie  [r]ejeter" + ("  [e]diter" if has_draft else "")
    while True:
        c = input(f"  {choices} > ").strip().lower()
        if c == "a":
            return {"action": "approve"}
        if c == "r":
            return {"action": "reject"}
        if c == "c":
            for i, t in enumerate(ALL_CHOICES):
                print(f"    {i:2} {t.label}")
            return {"action": "approve", "temperament": ALL_CHOICES[int(input("  n° > "))].id}
        if c == "e" and has_draft:
            body = input("  nouveau texte > ")
            return {"action": "edit", "reply": {"subject": payload["draft"]["subject"], "body": body}}


### Exécute le graphe sur l'email, gère les pauses humaines, puis affiche le résultat final.
async def run(email: dict, auto: str | None) -> None:
    key = settings.typesafe_api_key.get_secret_value() if settings.typesafe_api_key else None
    async with AsyncTypeSafeClient(api_key=key, retry=RetryPolicy(max_retries=3)) as client:
        graph = build_graph(JevJudge(client, settings), OllamaWriter(settings), settings)
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        payload: object = {"email": email}
        while True: 
            paused = None
            # stream_mode="updates" : un événement par node terminé, avec le patch qu'il a renvoyé.
            async for chunk in graph.astream(payload, config, stream_mode="updates"):
                for node, patch in chunk.items():
                    if node == "__interrupt__":
                        paused = patch[0].value
                    else:
                        show(node, patch)
            if paused is None:
                break
            payload = Command(resume=ask_human(paused, auto))

        final = (await graph.aget_state(config)).values["final"]
        print(f"\n=== Résultat : {final['status']} · {BY_ID[final['temperament']].label} ===")
        if final["reply"]:
            print(final["reply"]["body"])


### Point d'entrée : lit les options du terminal et lance le programme.
def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("text", nargs="?")
    p.add_argument("--subject")
    p.add_argument("--id", help="id d'un email de eval/dataset.jsonl")
    p.add_argument("--auto", choices=["approve", "reject"], help="réponse automatique aux pauses")
    p.add_argument("--mermaid", action="store_true")
    args = p.parse_args()

    if args.mermaid:
        print(build_graph(None, None, settings).get_graph().draw_mermaid())
        return
    if not (args.text or args.id):
        p.error("fournir un texte ou --id")
    asyncio.run(run(load_email(args), args.auto))


if __name__ == "__main__":
    main()
