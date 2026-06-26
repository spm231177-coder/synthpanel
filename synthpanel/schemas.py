"""Pydantic-Schemas — erzwungener strukturierter Output. Zitat ist Pflicht-Feld."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["hoch", "mittel", "niedrig"]


class Friction(BaseModel):
    """Ein einzelner Reibungspunkt aus Sicht einer Lens."""

    issue: str = Field(..., description="Was hakt, kurz")
    quote: str = Field("", description="Wörtliches Zitat der auslösenden Stelle (Pflicht)")
    severity: Severity = "mittel"
    suggestion: str = Field("", description="Konkreter Verbesserungsvorschlag")


class LensVerdict(BaseModel):
    """Das Urteil einer einzelnen Lens über das Artefakt."""

    lens_id: str
    lens_name: str
    kind: str = "standard"  # standard | barrier | red_team
    provenance: str = "sampled"  # sampled | modified | generated

    frictions: list[Friction] = Field(default_factory=list)
    positives: list[str] = Field(default_factory=list)

    # Framing-Balance gegen Zustimmungsverzerrung:
    #   pro_score = Anwalt DAFÜR (Attraktivität 0-10)
    #   con_score = Anwalt DAGEGEN (Abschreckung 0-10; 10 = totaler Reinfall)
    pro_score: float = 5.0
    con_score: float = 5.0
    blocker: bool = False  # hält mindestens eine Reibung definitiv von der Nutzung ab?
    would_use_reason: str = ""

    @property
    def balanced_score(self) -> float:
        """Mischwert: pro und (10 - Abschreckung) gemittelt. Beide Framings ziehen
        in dieselbe Richtung nur, wenn das Urteil wirklich konsistent ist."""
        return round((self.pro_score + (10 - self.con_score)) / 2, 1)

    @property
    def would_use(self) -> bool:
        # Ein harter Blocker schlägt jeden Score — Evidence vor Bauchgefühl.
        return self.balanced_score >= 5.5 and not self.blocker
