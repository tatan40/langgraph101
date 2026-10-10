"""Étape 0 : Jev comprend-il le tempérament de textes en français ?

Compare deux variantes sur eval/dataset.jsonl :
  - fr : consignes et descriptions en français
  - en : consignes et descriptions en anglais, texte en français

Usage : uv run python -m eval.spike [--lang fr en] [--concurrency 5]
"""

import argparse
import asyncio
import json
import statistics
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy, TypeSafeAPIError

from app.jev.questions import analysis_questions, analysis_state
from app.temperaments import TEMPERAMENTS

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parents[1] / ".env")


def load_dataset() -> list[dict]:
    with open(ROOT / "dataset.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


async def analyze(client, sem, item, questions) -> dict:
    async with sem:
        t0 = time.perf_counter()
        resp = await client.system_one(analysis_state(item["text"], item["subject"]), questions)
        latency_ms = (time.perf_counter() - t0) * 1000
    choice = resp.choices["temperament"]
    ranked = sorted(choice.probabilities.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "id": item["id"],
        "expected": item["temperament"],
        "predicted": choice.choice,
        "confidence": round(choice.confidence, 3),
        "top3": [(k, round(v, 3)) for k, v in ranked[:3]],
        "tons": {t.id: round(resp.nouls[f"ton_{t.id}"].noul, 3) for t in TEMPERAMENTS},
        "expected_tons": item["tons"],
        "intensite": round(resp.scores["intensite"].score, 2),
        "attend_reponse": round(resp.nouls["attend_reponse"].noul, 3),
        "expected_attend_reponse": item["attend_reponse"],
        "escalade": round(resp.nouls["escalade"].noul, 3),
        "expected_escalade": item["escalade"],
        "latency_ms": round(latency_ms),
        "input_tokens": resp.usage.input_tokens,
    }


def metrics(rows: list[dict]) -> dict:
    n = len(rows)
    correct = [r for r in rows if r["predicted"] == r["expected"]]
    wrong = [r for r in rows if r["predicted"] != r["expected"]]
    top2 = [r for r in rows if r["expected"] in {k for k, _ in r["top3"][:2]}]
    confident = [r for r in rows if r["confidence"] >= 0.5]
    lat = sorted(r["latency_ms"] for r in rows)
    # Tons secondaires : rappel sur les tons annotés, et faux positifs hors catégorie principale.
    expected_tons = [(r, t) for r in rows for t in r["expected_tons"]]
    tons_found = [1 for r, t in expected_tons if r["tons"][t] >= 0.5]
    spurious = [
        1 for r in rows for t, p in r["tons"].items()
        if p >= 0.5 and t != r["expected"] and t not in r["expected_tons"]
    ]
    return {
        "n": n,
        "accuracy": round(len(correct) / n, 3),
        "top2_accuracy": round(len(top2) / n, 3),
        "coverage_conf_0.5": round(len(confident) / n, 3),
        "accuracy_when_conf_0.5": round(
            sum(r["predicted"] == r["expected"] for r in confident) / max(len(confident), 1), 3
        ),
        "mean_conf_correct": round(statistics.mean(r["confidence"] for r in correct), 3) if correct else None,
        "mean_conf_wrong": round(statistics.mean(r["confidence"] for r in wrong), 3) if wrong else None,
        "escalade_accuracy": round(sum((r["escalade"] >= 0.5) == r["expected_escalade"] for r in rows) / n, 3),
        "attend_reponse_accuracy": round(
            sum((r["attend_reponse"] >= 0.5) == r["expected_attend_reponse"] for r in rows) / n, 3
        ),
        "tons_recall": round(len(tons_found) / max(len(expected_tons), 1), 3),
        "tons_spurious_per_text": round(len(spurious) / n, 2),
        "latency_p50_ms": lat[n // 2],
        "latency_p95_ms": lat[min(n - 1, int(n * 0.95))],
        "mean_input_tokens": round(statistics.mean(r["input_tokens"] or 0 for r in rows)),
        "confusions": Counter(f"{r['expected']} → {r['predicted']}" for r in wrong).most_common(),
    }


def per_class(rows: list[dict]) -> dict[str, str]:
    out = {}
    for t in TEMPERAMENTS:
        rs = [r for r in rows if r["expected"] == t.id]
        out[t.id] = f"{sum(r['predicted'] == t.id for r in rs)}/{len(rs)}"
    return out


async def main(langs: list[str], concurrency: int) -> None:
    dataset = load_dataset()
    sem = asyncio.Semaphore(concurrency)
    report: dict = {}
    async with AsyncTypeSafeClient(retry=RetryPolicy(max_retries=3)) as client:
        for lang in langs:
            questions = analysis_questions(lang)
            try:
                rows = await asyncio.gather(*(analyze(client, sem, it, questions) for it in dataset))
            except TypeSafeAPIError as e:
                raise SystemExit(f"Erreur API TypeSafe ({lang}) : status={e.status} request_id={e.request_id}") from e
            report[lang] = {"metrics": metrics(rows), "per_class": per_class(rows), "rows": rows}

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"spike-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for lang, r in report.items():
        m = r["metrics"]
        print(f"\n=== Variante {lang} ===")
        for k, v in m.items():
            if k != "confusions":
                print(f"  {k:28} {v}")
        print("  par classe                  ", r["per_class"])
        for row in r["rows"]:
            if row["predicted"] != row["expected"]:
                print(f"    {row['id']}: attendu {row['expected']}, prédit {row['predicted']} "
                      f"(conf {row['confidence']}) top3={row['top3']}")
    print(f"\nDétail : {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--lang", nargs="+", default=["fr", "en"], choices=["fr", "en"])
    p.add_argument("--concurrency", type=int, default=5)
    args = p.parse_args()
    asyncio.run(main(args.lang, args.concurrency))
