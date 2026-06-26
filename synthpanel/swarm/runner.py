"""Schwarm-Runner — jede Lens urteilt strukturiert über das Artefakt.

Framing-Balance: die Attraktivität wird einmal pro- und einmal contra-geframt
abgefragt (pro_score/con_score), der Mischwert entzerrt die Zustimmungsverzerrung.
Reibung wird mit Pflicht-Zitat erhoben (Evidence-Grounding).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from .. import models
from ..lenses import Lens
from ..schemas import Friction, LensVerdict
from ..util import parse_json

_SYSTEM = (
    "Du bist eine Testperson in einem synthetischen Panel. Du urteilst ehrlich aus "
    "deiner ganz eigenen Lage — nicht gefällig, nicht neutral. Du erfindest nichts, "
    "was nicht im vorgelegten Text steht. Wenn dir etwas FEHLT, benennst du die "
    "Stelle, an der du es erwartet hättest."
)


def _build_prompt(lens: Lens, artifact: str, artifact_kind: str, audience: str) -> str:
    return f"""DEINE LAGE:
{lens.persona.strip()}

DU BEWERTEST DIESES {artifact_kind.upper()}:
\"\"\"
{artifact.strip()}
\"\"\"

ZIELGRUPPE laut Macher: {audience or "nicht angegeben"}

AUFGABE — strikt aus deiner Lage:
1. frictions: konkrete Reibungspunkte (was hakt, was ist unklar, wo steigst du aus,
   was fehlt). Für JEDEN Punkt:
   - issue: kurz, worum es geht
   - quote: WÖRTLICHES Zitat der auslösenden Stelle aus dem Text (Pflicht; wenn etwas
     fehlt, zitiere die Stelle, wo du es erwartet hättest)
   - severity: "hoch" | "mittel" | "niedrig"
   - suggestion: konkreter Verbesserungsvorschlag
2. positives: max 3 kurze Punkte, was gut wirkt
3. pro_score (0-10): Als BEFÜRWORTER — wie attraktiv ist das für DICH?
4. con_score (0-10): Als KRITIKER — wie stark schrecken dich die gefundenen Probleme ab?
   (0 = gar nicht, 10 = totaler Reinfall). Sei streng und ehrlich.
5. blocker (true/false): Hält dich mindestens eine der Reibungen in der JETZIGEN Form
   definitiv von der Nutzung ab? Im Zweifel true.
6. would_use_reason: ein ehrlicher Satz, ob du es nutzen würdest und warum

Antworte NUR als JSON in dieser Form:
{{"frictions":[{{"issue":"","quote":"","severity":"mittel","suggestion":""}}],
"positives":[""],"pro_score":5,"con_score":5,"blocker":false,"would_use_reason":""}}"""


_MAX_ATTEMPTS = 3


def _judge(lens: Lens, artifact: str, artifact_kind: str, audience: str,
           backend: str | None, model: str | None) -> LensVerdict:
    prompt = _build_prompt(lens, artifact, artifact_kind, audience)

    # Kleine Modelle liefern unter Parallellast gelegentlich leere/kaputte JSON-Antworten.
    # Mehrere Versuche, leicht steigende Temperatur, bevor die Lens als Ausfall zählt.
    data = None
    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            raw = models.call(
                prompt, system=_SYSTEM, backend=backend, model=model,
                json_mode=True, temperature=0.7 + 0.1 * attempt,
            )
            data = parse_json(raw)
            break
        except (models.ModelError, ValueError) as exc:
            last_exc = exc
    if data is None:
        raise RuntimeError(f"{_MAX_ATTEMPTS}x fehlgeschlagen: {last_exc}")

    frictions = []
    for f in data.get("frictions", []) or []:
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity", "mittel")).lower()
        if sev not in ("hoch", "mittel", "niedrig"):
            sev = "mittel"
        frictions.append(
            Friction(
                issue=str(f.get("issue", "")).strip(),
                quote=str(f.get("quote", "")).strip(),
                severity=sev,
                suggestion=str(f.get("suggestion", "")).strip(),
            )
        )

    def _score(key: str) -> float:
        try:
            return max(0.0, min(10.0, float(data.get(key, 5))))
        except (TypeError, ValueError):
            return 5.0

    return LensVerdict(
        lens_id=lens.id,
        lens_name=lens.name,
        kind=lens.kind,
        provenance=lens.provenance,
        frictions=[f for f in frictions if f.issue],
        positives=[str(p).strip() for p in (data.get("positives") or []) if str(p).strip()][:3],
        pro_score=_score("pro_score"),
        con_score=_score("con_score"),
        blocker=bool(data.get("blocker", False)),
        would_use_reason=str(data.get("would_use_reason", "")).strip(),
    )


def run_swarm(
    lenses: list[Lens],
    artifact: str,
    artifact_kind: str = "Konzept",
    audience: str = "",
    backend: str | None = None,
    model: str | None = None,
    max_workers: int = 4,
    on_done=None,
) -> list[LensVerdict]:
    """Lässt alle Lenses (gedrosselt parallel) urteilen. Einzelne Fehler killen
    nicht den Lauf — die betroffene Lens wird übersprungen und gemeldet."""
    verdicts: list[LensVerdict] = []
    errors: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_judge, lz, artifact, artifact_kind, audience, backend, model): lz
            for lz in lenses
        }
        for fut in as_completed(futures):
            lz = futures[fut]
            try:
                v = fut.result()
                verdicts.append(v)
                if on_done:
                    on_done(lz, None)
            except Exception as exc:  # noqa: BLE001 — eine kaputte Lens darf den Lauf nicht stoppen
                errors.append((lz.id, str(exc)))
                if on_done:
                    on_done(lz, exc)

    run_swarm.last_errors = errors  # type: ignore[attr-defined]
    return verdicts
