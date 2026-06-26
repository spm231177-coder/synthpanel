"""Kleine Helfer — v.a. robustes JSON-Parsing aus LLM-Antworten."""
from __future__ import annotations

import json
import re


def parse_json(text: str) -> dict:
    """Extrahiert das erste JSON-Objekt aus einer LLM-Antwort.

    Toleriert Markdown-Codefences und Geschwätz drumherum. Wirft ValueError,
    wenn nichts Brauchbares gefunden wird.
    """
    if not text or not text.strip():
        raise ValueError("Leere Modell-Antwort")

    cleaned = text.strip()
    # Codefences entfernen (```json ... ``` oder ``` ... ```)
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()

    # Erstes '{' bis letztes '}' herausschneiden
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Kein JSON-Objekt in Antwort gefunden: {text[:200]!r}")

    snippet = cleaned[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError as exc:
        # Häufiger Fehler: trailing commas — simpel reparieren
        repaired = re.sub(r",\s*([}\]])", r"\1", snippet)
        return json.loads(repaired)  # wirft erneut, wenn immer noch kaputt
