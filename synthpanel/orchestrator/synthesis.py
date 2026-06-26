"""Synthese — verdichtet Lens-Urteile zu einer rangierten Reibungs-Liste.

Bewusst DETERMINISTISCH (kein zweiter LLM-Call): reproduzierbar, token-sparend,
nichts wird wegerfunden. Clustering über String-Ähnlichkeit (difflib).

Kein Score, keine Prozente, keine Hochrechnung — nur "wie viele Lenses stolperten"
als Indiz. Dissens (Einzel-Lens, aber wichtig) wird laut hervorgehoben.
"""
from __future__ import annotations

import difflib
import math
from dataclasses import dataclass, field

from .. import models
from ..schemas import LensVerdict

_SEV_WEIGHT = {"hoch": 3, "mittel": 2, "niedrig": 1}
_SIM_THRESHOLD = 0.55  # difflib-Fallback (String-Ähnlichkeit)
_EMBED_THRESHOLD = 0.68  # Cosine bei nomic-embed-text (semantisch; tiefer = mehr Merges)


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


@dataclass
class Cluster:
    issue: str
    severity: str
    quote: str
    suggestion: str
    lens_ids: list[str]
    lens_names: list[str]
    has_barrier: bool
    count: int

    @property
    def rank(self) -> int:
        return _SEV_WEIGHT[self.severity] * self.count


@dataclass
class Coverage:
    total: int
    by_kind: dict[str, int]
    by_provenance: dict[str, int]
    failed: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Synthesis:
    clusters: list[Cluster]
    dissent: list[Cluster]
    coverage: Coverage
    would_use_count: int
    would_use_total: int
    blocked_count: int = 0


def _build_similarity(items: list, use_embeddings: bool):
    """Liefert (sim_fn, method). sim_fn(i, j) -> bool: gehören Items i,j ins selbe Cluster?

    Bevorzugt semantische Embeddings (nomic-embed-text, lokal/gratis); fällt bei
    Nichtverfügbarkeit sauber auf String-Ähnlichkeit (difflib) zurück.
    """
    issues = [f.issue for f, _ in items]
    if use_embeddings:
        try:
            vecs = models.embed(issues)
            if len(vecs) == len(issues):
                return (lambda i, j: _cosine(vecs[i], vecs[j]) > _EMBED_THRESHOLD), "embeddings"
        except models.ModelError:
            pass
    norms = [_norm(s) for s in issues]
    return (
        lambda i, j: difflib.SequenceMatcher(None, norms[i], norms[j]).ratio() > _SIM_THRESHOLD,
        "difflib",
    )


def _cluster_frictions(verdicts: list[LensVerdict], use_embeddings: bool = True) -> list[Cluster]:
    items = [(f, v) for v in verdicts for f in v.frictions]
    similar, _method = _build_similarity(items, use_embeddings)

    raw: list[dict] = []  # offene Cluster im Aufbau; "seed" = Index des ersten Members
    for idx, (f, v) in enumerate(items):
        placed = False
        for c in raw:
            if similar(c["seed"], idx):
                c["members"].append((f, v))
                placed = True
                break
        if not placed:
            raw.append({"seed": idx, "issue": f.issue, "members": [(f, v)]})

    clusters: list[Cluster] = []
    for c in raw:
        members = c["members"]
        # Repräsentant = Member mit höchster Severity (für Zitat & Vorschlag)
        rep_friction, _ = max(members, key=lambda m: _SEV_WEIGHT[m[0].severity])
        max_sev = max(_SEV_WEIGHT[f.severity] for f, _ in members)
        sev_label = next(k for k, w in _SEV_WEIGHT.items() if w == max_sev)
        lens_ids = sorted({v.lens_id for _, v in members})
        clusters.append(
            Cluster(
                issue=rep_friction.issue,
                severity=sev_label,
                quote=rep_friction.quote,
                suggestion=rep_friction.suggestion,
                lens_ids=lens_ids,
                lens_names=sorted({v.lens_name for _, v in members}),
                has_barrier=any(v.kind == "barrier" for _, v in members),
                count=len(lens_ids),
            )
        )

    clusters.sort(key=lambda c: (c.rank, c.count), reverse=True)
    return clusters


def synthesize(
    verdicts: list[LensVerdict],
    failed: list[tuple[str, str]] | None = None,
    use_embeddings: bool = True,
) -> Synthesis:
    clusters = _cluster_frictions(verdicts, use_embeddings=use_embeddings)

    # Dissens: nur eine Lens, aber hohe Severity ODER Barriere-Befund.
    dissent = [c for c in clusters if c.count == 1 and (c.severity == "hoch" or c.has_barrier)]

    by_kind: dict[str, int] = {}
    by_prov: dict[str, int] = {}
    for v in verdicts:
        by_kind[v.kind] = by_kind.get(v.kind, 0) + 1
        by_prov[v.provenance] = by_prov.get(v.provenance, 0) + 1

    coverage = Coverage(
        total=len(verdicts),
        by_kind=by_kind,
        by_provenance=by_prov,
        failed=failed or [],
    )

    return Synthesis(
        clusters=clusters,
        dissent=dissent,
        coverage=coverage,
        would_use_count=sum(1 for v in verdicts if v.would_use),
        would_use_total=len(verdicts),
        blocked_count=sum(1 for v in verdicts if v.blocker),
    )
