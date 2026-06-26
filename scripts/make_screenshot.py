"""Erzeugt assets/example_report.svg — den README-Screenshot.

Bewusst eine kuratierte, deterministische Beispiel-Synthese (kein Live-Lauf), damit
das Bild sauber und reproduzierbar ist. Inhalt: das fiktive Demo „FokusZeit".

  python scripts/make_screenshot.py
"""
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rich.console import Console  # noqa: E402

from synthpanel.orchestrator.report import _render_rich  # noqa: E402
from synthpanel.orchestrator.synthesis import Cluster, Coverage, Synthesis  # noqa: E402


def _c(issue, severity, quote, suggestion, lens_names, has_barrier=False):
    return Cluster(
        issue=issue, severity=severity, quote=quote, suggestion=suggestion,
        lens_ids=[n.lower() for n in lens_names], lens_names=lens_names,
        has_barrier=has_barrier, count=len(lens_names),
    )


clusters = [
    _c("Was nach der Gratis-Phase kostet, bleibt unklar", "hoch",
       "Kostenlos starten", "Direkt sagen, was nach der Testzeit fällig wird",
       ["Preisbewusst", "Skeptiker", "Laie", "Mobil", "Datenschutz", "Rotes Team"]),
    _c("„Flow\" wird vorausgesetzt, nicht erklärt", "hoch",
       "bringt dich in den Flow", "Einfacher: „hilft dir, konzentriert zu bleiben\"",
       ["Einfache Sprache", "Laie", "Senior", "Mobil"], has_barrier=True),
    _c("Behauptung „Schluss mit Aufschieben\" ohne Beleg", "mittel",
       "Schluss mit Aufschieben", "Konkretes Ergebnis statt Versprechen zeigen",
       ["Skeptiker", "Rotes Team", "Early Adopter"]),
    _c("Statistik nur in Plus — wirkt wie Köder", "mittel",
       "FokusZeit Plus für 2,99 €/Monat", "Zeigen, welche Statistik gratis bleibt",
       ["Preisbewusst", "Konkurrenz-Kenner"]),
]
dissent = [
    _c("Nur Klänge als Signal — für Hörbehinderte unbrauchbar", "hoch",
       "Sanfte Klänge statt schriller Wecker", "Zusätzlich ein sichtbares Signal",
       ["Hörbehinderung"], has_barrier=True),
]
syn = Synthesis(
    clusters=clusters,
    dissent=dissent,
    coverage=Coverage(total=11, by_kind={"standard": 7, "barrier": 2, "red_team": 2},
                      by_provenance={"sampled": 11}, failed=[]),
    would_use_count=4,
    would_use_total=11,
    blocked_count=3,
)

console = Console(record=True, width=98)
_render_rich(syn, "FokusZeit — Landingpage", console=console)

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
os.makedirs(out_dir, exist_ok=True)
path = os.path.join(out_dir, "example_report.svg")
console.save_svg(path, title="synthpanel run landingpage.md")
print(f"Screenshot: {path}")
