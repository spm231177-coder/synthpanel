"""Report-Rendering. Nutzt rich, wenn vorhanden, sonst Plain-Text-Fallback.

Der Output ist bewusst screenshot-tauglich (Shareability = Adoptions-Hebel).
"""
from __future__ import annotations

from .synthesis import Cluster, Synthesis

_SEV_ICON = {"hoch": "🔴", "mittel": "🟡", "niedrig": "⚪"}
_SEV_LABEL = {"hoch": "HOCH", "mittel": "MITTEL", "niedrig": "NIEDRIG"}


def _cluster_lines(c: Cluster, total: int) -> list[str]:
    icon = _SEV_ICON.get(c.severity, "🟡")
    lines = [f"{icon} [{_SEV_LABEL.get(c.severity, c.severity.upper())}] {c.issue}"]
    names = ", ".join(c.lens_names)
    lines.append(f"   ├─ getroffen von: {c.count}/{total} Lenses ({names})")
    if c.quote:
        lines.append(f"   ├─ Zitat: »{c.quote}«")
    if c.suggestion:
        lines.append(f"   ├─ Vorschlag: {c.suggestion}")
    lines.append(f"   └─ {'Barriere-Befund' if c.has_barrier else 'Reibung'}")
    return lines


def render_plain(syn: Synthesis, title: str) -> str:
    total = syn.coverage.total
    out: list[str] = []
    out.append("═" * 64)
    out.append(f"  SynthPanel — Reibungs-Report: {title}")
    out.append("═" * 64)
    out.append("")
    out.append(f"  {total} Lenses gelaufen · {len(syn.clusters)} Reibungs-Cluster gefunden")
    out.append(
        f"  Würden es nutzen: {syn.would_use_count}/{syn.would_use_total} "
        f"· {syn.blocked_count} mit hartem Blocker — Indiz, keine Hochrechnung"
    )
    out.append("")

    out.append("── RANGIERTE REIBUNG (wie viele stolperten × wie hart) " + "─" * 9)
    out.append("")
    if not syn.clusters:
        out.append("  (keine Reibung gefunden — verdächtig; Lenses/Backend prüfen)")
    for c in syn.clusters:
        out.extend("  " + ln for ln in _cluster_lines(c, total))
        out.append("")

    if syn.dissent:
        out.append("── DISSENS (Einzelstimme, aber wichtig — NICHT wegmitteln) " + "─" * 5)
        out.append("")
        for c in syn.dissent:
            out.extend("  " + ln for ln in _cluster_lines(c, total))
            out.append("")

    out.append("── COVERAGE (ehrlich über die eigenen Lücken) " + "─" * 18)
    kinds = ", ".join(f"{k}: {n}" for k, n in sorted(syn.coverage.by_kind.items()))
    prov = ", ".join(f"{k}: {n}" for k, n in sorted(syn.coverage.by_provenance.items()))
    out.append(f"  Lens-Arten: {kinds}")
    out.append(f"  Provenance: {prov}")
    if syn.coverage.failed:
        fails = ", ".join(lid for lid, _ in syn.coverage.failed)
        out.append(f"  ⚠ Ausgefallen (nicht abgedeckt): {fails}")
    out.append("")
    out.append("  Hinweis: SynthPanel findet Reibung — es misst keine Häufigkeiten.")
    out.append("  Kein Ersatz für echte Nutzer, sondern der First-Pass davor.")
    out.append("═" * 64)
    return "\n".join(out)


def render_markdown(syn: Synthesis, title: str) -> str:
    """Markdown-Report — für GitHub-PR-Kommentare (der CI-Wedge)."""
    total = syn.coverage.total
    md = [f"## 🔍 SynthPanel — Reibungs-Report: `{title}`", ""]
    md.append(
        f"**{total} Test-Personas** · **{len(syn.clusters)}** Reibungs-Cluster · "
        f"würden nutzen: {syn.would_use_count}/{syn.would_use_total} "
        f"({syn.blocked_count} mit hartem Blocker)"
    )
    md.append("")
    md.append("### Rangierte Reibung")
    for c in syn.clusters[:15]:
        icon = _SEV_ICON.get(c.severity, "🟡")
        a11y = " `A11y`" if c.has_barrier else ""
        md.append(f"- {icon} **{c.issue}** — {c.count}/{total} Personas{a11y}")
        if c.quote:
            md.append(f"  > {c.quote}")
        if c.suggestion:
            md.append(f"  → _{c.suggestion}_")
    if syn.dissent:
        md.append("")
        md.append("### ⚠️ Dissens (Einzelstimme, aber wichtig)")
        for c in syn.dissent[:6]:
            md.append(f"- {_SEV_ICON.get(c.severity,'')} **{c.issue}** _({', '.join(c.lens_names)})_")
    if syn.coverage.failed:
        md.append("")
        md.append(f"<sub>⚠ Nicht abgedeckt (Ausfall): {', '.join(l for l, _ in syn.coverage.failed)}</sub>")
    md.append("")
    md.append(
        "<sub>SynthPanel findet Reibung — es misst keine Häufigkeiten. "
        "Kein Ersatz für echte Nutzer, sondern der First-Pass davor. "
        "[Was ist das?](https://github.com/spm231177-coder/synthpanel)</sub>"
    )
    return "\n".join(md)


def render_detailed(verdicts, title: str) -> None:
    """Transparenz-Ansicht: jede Persona einzeln — Score, Blocker, Reibung, Begründung."""
    out = ["", "═" * 64, f"  DETAIL-AUSWERTUNG: jede Persona einzeln — {title}", "═" * 64]
    for v in sorted(verdicts, key=lambda x: x.balanced_score):
        kind = {"barrier": " [A11y]", "red_team": " [Rotes Team]"}.get(v.kind, "")
        verdict = "würde nutzen" if v.would_use else "würde NICHT nutzen"
        block = "  ⛔ BLOCKER" if v.blocker else ""
        out.append("")
        out.append(f"▸ {v.lens_name}{kind}")
        out.append(
            f"   Mischwert {v.balanced_score}/10 (pro {v.pro_score:g} · Abschreckung "
            f"{v.con_score:g}) → {verdict}{block}"
        )
        if v.would_use_reason:
            out.append(f"   Fazit: {v.would_use_reason}")
        for f in v.frictions:
            out.append(f"   · [{f.severity}] {f.issue}")
            if f.quote:
                out.append(f"       »{f.quote}«")
            if f.suggestion:
                out.append(f"       → {f.suggestion}")
        if v.positives:
            out.append(f"   + gut: {'; '.join(v.positives)}")
    out.append("═" * 64)
    print("\n".join(out))


def render_diff(diff: dict, old_meta: dict, title: str) -> None:
    """Regressions-Diff gegen einen früheren Snapshot — qualitativ."""
    out = ["", "═" * 64, f"  REGRESSIONS-DIFF vs. Snapshot „{old_meta.get('title', '?')}\"", "═" * 64]
    created = old_meta.get("created", "?")
    out.append(f"  Vergleich gegen Lauf vom {created}")
    out.append("")

    resolved, fresh, persisted = diff["resolved"], diff["new"], diff["persisted"]
    out.append(f"  ✅ GELÖST: {len(resolved)}   🆕 NEU: {len(fresh)}   ➖ UNVERÄNDERT: {len(persisted)}")
    out.append("")

    if resolved:
        out.append("── ✅ GELÖSTE REIBUNG (war da, jetzt weg) " + "─" * 22)
        for c in resolved:
            out.append(f"  ✅ [{c['severity']}] {c['issue']}  ({c['count']} Lenses)")
        out.append("")
    if fresh:
        out.append("── 🆕 NEU AUFGETAUCHT (Nebenwirkung des Fixes?) " + "─" * 16)
        for c in fresh:
            out.append(f"  🆕 [{c['severity']}] {c['issue']}  ({c['count']} Lenses)")
        out.append("")
    if persisted:
        out.append("── ➖ UNVERÄNDERT (besteht weiter) " + "─" * 30)
        for old_c, new_c in persisted:
            note = ""
            if old_c["count"] != new_c["count"]:
                note = f"  (Lenses {old_c['count']}→{new_c['count']})"
            sev = ""
            if old_c["severity"] != new_c["severity"]:
                sev = f"  (Schwere {old_c['severity']}→{new_c['severity']})"
            out.append(f"  ➖ [{new_c['severity']}] {new_c['issue']}{note}{sev}")
        out.append("")
    out.append("═" * 64)
    print("\n".join(out))


def render(syn: Synthesis, title: str, use_rich: bool = True) -> None:
    if use_rich:
        try:
            _render_rich(syn, title)
            return
        except ImportError:
            pass
    print(render_plain(syn, title))


def _render_rich(syn: Synthesis, title: str) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    total = syn.coverage.total

    console.print(
        Panel.fit(
            f"[bold]SynthPanel[/bold] — Reibungs-Report\n[dim]{title}[/dim]",
            border_style="cyan",
        )
    )
    console.print(
        f"[bold]{total}[/bold] Lenses · [bold]{len(syn.clusters)}[/bold] Reibungs-Cluster · "
        f"würden nutzen: [bold]{syn.would_use_count}/{syn.would_use_total}[/bold] "
        f"· [bold]{syn.blocked_count}[/bold] Blocker "
        "[dim](Indiz, keine Hochrechnung)[/dim]\n"
    )

    style = {"hoch": "red", "mittel": "yellow", "niedrig": "white"}
    table = Table(title="Rangierte Reibung", show_lines=True, expand=True)
    table.add_column("Sev", width=8)
    table.add_column("Reibung")
    table.add_column("Lenses", width=10, justify="center")
    table.add_column("Zitat / Vorschlag")
    for c in syn.clusters:
        detail = ""
        if c.quote:
            detail += f"[dim]»{c.quote}«[/dim]\n"
        if c.suggestion:
            detail += f"→ {c.suggestion}"
        table.add_row(
            f"[{style.get(c.severity,'white')}]{_SEV_ICON.get(c.severity,'')} {c.severity}[/]",
            c.issue + ("  [magenta](A11y)[/magenta]" if c.has_barrier else ""),
            f"{c.count}/{total}",
            detail or "[dim]—[/dim]",
        )
    console.print(table)

    if syn.dissent:
        body = "\n".join(
            f"• [bold]{c.issue}[/bold] [dim]({', '.join(c.lens_names)})[/dim]"
            + (f"\n   »{c.quote}«" if c.quote else "")
            for c in syn.dissent
        )
        console.print(Panel(body, title="Dissens — Einzelstimme, aber wichtig", border_style="magenta"))

    kinds = ", ".join(f"{k}: {n}" for k, n in sorted(syn.coverage.by_kind.items()))
    prov = ", ".join(f"{k}: {n}" for k, n in sorted(syn.coverage.by_provenance.items()))
    cov = f"Lens-Arten: {kinds}\nProvenance: {prov}"
    if syn.coverage.failed:
        cov += "\n⚠ Ausgefallen: " + ", ".join(lid for lid, _ in syn.coverage.failed)
    cov += "\n\n[dim]Findet Reibung, misst keine Häufigkeiten. First-Pass vor echten Nutzern.[/dim]"
    console.print(Panel(cov, title="Coverage — ehrlich über Lücken", border_style="cyan"))
