"""Lens Library — Laden & Auswahl. Zweck: Coverage diverser Blickwinkel, NICHT
statistische Repräsentativität."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML fehlt: pip install pyyaml") from exc

_DEFAULT_LIBRARY = os.path.join(os.path.dirname(__file__), "library.yaml")


@dataclass
class Lens:
    id: str
    name: str
    persona: str
    kind: str = "standard"  # standard | barrier | red_team
    provenance: str = "sampled"  # sampled | modified | generated
    tags: list[str] = field(default_factory=list)


def load_library(path: str | None = None) -> list[Lens]:
    path = path or _DEFAULT_LIBRARY
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    lenses = [Lens(**entry) for entry in raw["lenses"]]
    if not lenses:
        raise ValueError(f"Keine Lenses in {path}")
    return lenses


def select(lenses: list[Lens], ids: str | None) -> list[Lens]:
    """ids: None/'all' = alle; sonst kommaseparierte Lens-IDs."""
    if not ids or ids == "all":
        return lenses
    wanted = {i.strip() for i in ids.split(",") if i.strip()}
    chosen = [lz for lz in lenses if lz.id in wanted]
    missing = wanted - {lz.id for lz in chosen}
    if missing:
        raise ValueError(f"Unbekannte Lens-IDs: {', '.join(sorted(missing))}")
    return chosen
