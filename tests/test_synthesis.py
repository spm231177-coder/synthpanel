"""Offline-Tests für die deterministische Synthese — kein Modell nötig."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from synthpanel.orchestrator import synthesize  # noqa: E402
from synthpanel.schemas import Friction, LensVerdict  # noqa: E402


def _verdict(lens_id, kind, frictions, pro=5, con=5, blocker=False):
    return LensVerdict(
        lens_id=lens_id,
        lens_name=lens_id.title(),
        kind=kind,
        frictions=frictions,
        pro_score=pro,
        con_score=con,
        blocker=blocker,
    )


def test_clusters_merge_similar_issues():
    a = _verdict("l1", "standard", [Friction(issue="Preis ist unklar", quote="gratis", severity="hoch")])
    b = _verdict("l2", "standard", [Friction(issue="Preis unklar dargestellt", quote="gratis", severity="mittel")])
    syn = synthesize([a, b], use_embeddings=False)
    assert len(syn.clusters) == 1
    assert syn.clusters[0].count == 2
    assert syn.clusters[0].severity == "hoch"  # max severity gewinnt


def test_dissent_picks_single_high_severity():
    a = _verdict("l1", "standard", [Friction(issue="Tippfehler", severity="niedrig")])
    b = _verdict("l2", "barrier", [Friction(issue="CTA nur über Farbe erkennbar", severity="hoch")])
    syn = synthesize([a, b], use_embeddings=False)
    assert any("CTA" in c.issue for c in syn.dissent)
    assert not any("Tippfehler" in c.issue for c in syn.dissent)


def test_would_use_uses_balanced_score():
    # pro 8, Abschreckung 2 → (8 + 8)/2 = 8.0 → würde nutzen
    v = _verdict("l1", "standard", [], pro=8, con=2)
    assert v.balanced_score == 8.0
    assert v.would_use is True
    # pro 3, Abschreckung 8 → (3 + 2)/2 = 2.5 → würde nicht
    v2 = _verdict("l2", "standard", [], pro=3, con=8)
    assert v2.balanced_score == 2.5
    assert v2.would_use is False


def test_blocker_overrides_high_score():
    # Hoher Score, aber harter Blocker → trotzdem keine Nutzung
    v = _verdict("l1", "standard", [], pro=9, con=1, blocker=True)
    assert v.balanced_score >= 5.5
    assert v.would_use is False


def test_coverage_counts_kinds():
    syn = synthesize([
        _verdict("l1", "standard", []),
        _verdict("l2", "barrier", []),
        _verdict("l3", "red_team", []),
    ], use_embeddings=False)
    assert syn.coverage.total == 3
    assert syn.coverage.by_kind["barrier"] == 1
    assert syn.coverage.by_kind["red_team"] == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  [ok] {name}")
    print("Alle Tests gruen.")
