"""Snapshots & Regressions-Diff — der Kern von Phase 2.

Ein Snapshot hält die Reibungs-Cluster eines Laufs fest. Beim nächsten Lauf
(nach einem Fix) vergleicht `diff_clusters` qualitativ: was ist WEG (gelöst),
was ist NEU, was BLEIBT. Bewusst qualitativ — keine Prozent-Deltas.

Matching der Cluster über Embeddings (semantisch, gratis via Ollama) mit
difflib-Fallback, damit „Preis unklar" und „Preisstruktur fehlt" als dieselbe
Reibung erkannt werden.
"""
from __future__ import annotations

import difflib
import json
import math
import os
from dataclasses import asdict

from . import models

_MATCH_EMBED = 0.70
_MATCH_DIFFLIB = 0.55


def _path(snapshot_dir: str, name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return os.path.join(snapshot_dir, f"{safe}.json")


def save_snapshot(syn, *, name: str, snapshot_dir: str, title: str, model: str,
                  created: str) -> str:
    os.makedirs(snapshot_dir, exist_ok=True)
    data = {
        "title": title,
        "created": created,
        "model": model,
        "would_use": [syn.would_use_count, syn.would_use_total],
        "blocked": syn.blocked_count,
        "clusters": [asdict(c) for c in syn.clusters],
    }
    path = _path(snapshot_dir, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return path


def load_snapshot(name: str, snapshot_dir: str) -> dict:
    with open(_path(snapshot_dir, name), encoding="utf-8") as fh:
        return json.load(fh)


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _matcher(old_issues: list[str], new_issues: list[str], use_embeddings: bool):
    """Liefert match(i_old, j_new) -> bool."""
    if use_embeddings and (old_issues or new_issues):
        try:
            vecs = models.embed(old_issues + new_issues)
            n = len(old_issues)
            ov, nv = vecs[:n], vecs[n:]
            return lambda i, j: _cosine(ov[i], nv[j]) > _MATCH_EMBED
        except models.ModelError:
            pass
    on = [" ".join(s.lower().split()) for s in old_issues]
    nn = [" ".join(s.lower().split()) for s in new_issues]
    return lambda i, j: difflib.SequenceMatcher(None, on[i], nn[j]).ratio() > _MATCH_DIFFLIB


def diff_clusters(old: list[dict], new_syn, use_embeddings: bool = True) -> dict:
    """Vergleicht alte Snapshot-Cluster (dicts) mit der neuen Synthese.

    Rückgabe: {"resolved":[...], "new":[...], "persisted":[(old,new),...]}.
    """
    new_clusters = [asdict(c) for c in new_syn.clusters]
    old_issues = [c["issue"] for c in old]
    new_issues = [c["issue"] for c in new_clusters]
    match = _matcher(old_issues, new_issues, use_embeddings)

    matched_old: set[int] = set()
    matched_new: set[int] = set()
    persisted: list[tuple[dict, dict]] = []

    for j, _nc in enumerate(new_clusters):
        for i, _oc in enumerate(old):
            if i in matched_old:
                continue
            if match(i, j):
                persisted.append((old[i], new_clusters[j]))
                matched_old.add(i)
                matched_new.add(j)
                break

    resolved = [c for i, c in enumerate(old) if i not in matched_old]
    fresh = [c for j, c in enumerate(new_clusters) if j not in matched_new]
    return {"resolved": resolved, "new": fresh, "persisted": persisted}
