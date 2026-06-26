"""SynthPanel CLI.

  synthpanel run <artefakt.md> [--audience "..."] [--backend ollama|anthropic]
  synthpanel lenses

Default-Backend ist Ollama (lokal, gratis). Anthropic löst eine Token-Killer-Warnung
mit Kostenschätzung aus, bevor irgendetwas kostet.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from dataclasses import asdict

# Windows-Konsolen sind oft cp1252 — Report nutzt Emoji/Unicode. UTF-8 erzwingen.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

from . import __version__
from .lenses import load_library, select
from .orchestrator import synthesize
from .orchestrator.report import render, render_detailed, render_diff, render_markdown
from .store import diff_clusters, load_snapshot, save_snapshot
from .swarm import run_swarm


def _export_json(path: str, title: str, verdicts, syn) -> None:
    data = {
        "title": title,
        "would_use": [syn.would_use_count, syn.would_use_total],
        "blocked": syn.blocked_count,
        "clusters": [asdict(c) for c in syn.clusters],
        "dissent": [asdict(c) for c in syn.dissent],
        "coverage": {
            "total": syn.coverage.total,
            "by_kind": syn.coverage.by_kind,
            "by_provenance": syn.coverage.by_provenance,
            "failed": syn.coverage.failed,
        },
        "lenses": [
            {
                "id": v.lens_id, "name": v.lens_name, "kind": v.kind,
                "balanced_score": v.balanced_score, "pro_score": v.pro_score,
                "con_score": v.con_score, "blocker": v.blocker,
                "would_use": v.would_use, "reason": v.would_use_reason,
                "frictions": [f.model_dump() for f in v.frictions],
                "positives": v.positives,
            }
            for v in verdicts
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _cmd_lenses(args) -> int:
    lenses = load_library(args.library)
    print(f"Lens Library — {len(lenses)} Blickwinkel:\n")
    for lz in lenses:
        flag = {"barrier": " [A11y]", "red_team": " [Rotes Team]"}.get(lz.kind, "")
        print(f"  {lz.id:<26} {lz.name}{flag}")
    return 0


def _confirm_anthropic_cost(n_lenses: int) -> bool:
    # grobe Schätzung: ~1.2k Input + ~0.6k Output je Lens
    est_in = n_lenses * 1200
    est_out = n_lenses * 600
    print("⚠  TOKEN-KILLER-WARNUNG (Backend: anthropic)", file=sys.stderr)
    print(
        f"   {n_lenses} Lenses × 1 Runde ≈ {est_in:,} Input- + {est_out:,} Output-Tokens.\n"
        "   Pro zusätzliche Runde fällt das erneut an. Drosseln: weniger Lenses\n"
        "   (--lenses id,id), oder gratis über Ollama (--backend ollama).",
        file=sys.stderr,
    )
    try:
        return input("   Fortfahren und Tokens ausgeben? [y/N] ").strip().lower() in ("y", "j", "yes", "ja")
    except EOFError:
        return False


def _cmd_run(args) -> int:
    try:
        with open(args.artifact, encoding="utf-8") as fh:
            artifact = fh.read()
    except OSError as exc:
        print(f"Artefakt nicht lesbar: {exc}", file=sys.stderr)
        return 2
    if not artifact.strip():
        print("Artefakt ist leer.", file=sys.stderr)
        return 2

    lenses = select(load_library(args.library), args.lenses)

    if args.backend == "anthropic" and not args.yes:
        if not _confirm_anthropic_cost(len(lenses)):
            print("Abgebrochen.", file=sys.stderr)
            return 1

    title = args.title or args.artifact

    def _progress(lens, err):
        mark = "✗" if err else "✓"
        print(f"  {mark} {lens.name}", file=sys.stderr)

    print(f"SynthPanel v{__version__} — {len(lenses)} Lenses, Backend={args.backend}\n", file=sys.stderr)
    verdicts = run_swarm(
        lenses,
        artifact,
        artifact_kind=args.kind,
        audience=args.audience,
        backend=args.backend,
        model=args.model,
        max_workers=args.max_workers,
        on_done=_progress,
    )
    failed = getattr(run_swarm, "last_errors", [])

    if not verdicts:
        print("\nKeine Lens hat geantwortet — Backend/Modell prüfen.", file=sys.stderr)
        for lid, msg in failed:
            print(f"  {lid}: {msg}", file=sys.stderr)
        return 3

    syn = synthesize(verdicts, failed=failed, use_embeddings=not args.no_embeddings)
    print("", file=sys.stderr)

    if args.detailed:
        render_detailed(verdicts, title)
    render(syn, title, use_rich=not args.no_rich)

    if args.json:
        _export_json(args.json, title, verdicts, syn)
        print(f"JSON-Export: {args.json}", file=sys.stderr)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(syn, title))
        print(f"Markdown-Export: {args.markdown}", file=sys.stderr)

    # Diff gegen alten Snapshot VOR dem Überschreiben (falls gleicher Name).
    if args.compare:
        try:
            old = load_snapshot(args.compare, args.snapshot_dir)
            d = diff_clusters(old["clusters"], syn, use_embeddings=not args.no_embeddings)
            render_diff(d, old, title)
        except FileNotFoundError:
            print(f"Kein Snapshot „{args.compare}\" in {args.snapshot_dir}/", file=sys.stderr)

    if args.save_snapshot:
        created = datetime.datetime.now().isoformat(timespec="seconds")
        path = save_snapshot(
            syn, name=args.save_snapshot, snapshot_dir=args.snapshot_dir,
            title=title, model=args.model or "(default)", created=created,
        )
        print(f"Snapshot gespeichert: {path}", file=sys.stderr)

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="synthpanel", description="Such-Werkzeug: findet Reibung aus diversen Blickwinkeln.")
    p.add_argument("--version", action="version", version=f"synthpanel {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Artefakt durch den Lens-Schwarm jagen")
    run.add_argument("artifact", help="Pfad zur Text-/Konzept-Datei")
    run.add_argument("--audience", default="", help="Zielgruppe (1-2 Sätze)")
    run.add_argument("--kind", default="Konzept", help="Artefakt-Typ-Label (z.B. Pitch, Store-Listing)")
    run.add_argument("--title", default="", help="Titel im Report")
    run.add_argument("--backend", choices=["ollama", "anthropic"], default="ollama")
    run.add_argument("--model", default=None, help="Modell-Override")
    run.add_argument("--lenses", default="all", help="'all' oder kommaseparierte Lens-IDs")
    run.add_argument("--library", default=None, help="Pfad zu eigener library.yaml")
    run.add_argument("--max-workers", type=int, default=4)
    run.add_argument("--no-rich", action="store_true", help="Plain-Text-Report erzwingen")
    run.add_argument("--no-embeddings", action="store_true",
                     help="Semantisches Clustering aus (nutzt String-Ähnlichkeit statt nomic-embed-text)")
    run.add_argument("--detailed", action="store_true",
                     help="Transparenz-Ansicht: jede Persona einzeln (Score, Blocker, Reibung, Begründung)")
    run.add_argument("--json", default=None, metavar="PATH",
                     help="Kompletten strukturierten Report als JSON exportieren")
    run.add_argument("--markdown", default=None, metavar="PATH",
                     help="Report als Markdown exportieren (z.B. für GitHub-PR-Kommentar)")
    run.add_argument("--save-snapshot", default=None, metavar="NAME",
                     help="Diesen Lauf als Snapshot für späteren Regressions-Vergleich speichern")
    run.add_argument("--compare", default=None, metavar="NAME",
                     help="Nach dem Lauf qualitativen Diff gegen einen früheren Snapshot zeigen")
    run.add_argument("--snapshot-dir", default="snapshots", help="Verzeichnis für Snapshots")
    run.add_argument("--yes", action="store_true", help="Kosten-Warnung überspringen")
    run.set_defaults(func=_cmd_run)

    ls = sub.add_parser("lenses", help="Lens Library anzeigen")
    ls.add_argument("--library", default=None)
    ls.set_defaults(func=_cmd_lenses)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
