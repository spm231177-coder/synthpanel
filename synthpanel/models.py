"""Modell-Router: Ollama (Default, lokal/gratis) oder Anthropic (Cloud).

Bewusst dependency-arm: Ollama über die Standardbibliothek (urllib), damit der
0-€-Pfad ohne pip-Install läuft. Anthropic nur, wenn das Paket vorhanden ist.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("SYNTHPANEL_OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("SYNTHPANEL_OLLAMA_MODEL", "llama3.2:3b")
ANTHROPIC_MODEL = os.environ.get("SYNTHPANEL_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


class ModelError(RuntimeError):
    pass


def call(
    prompt: str,
    system: str = "",
    backend: str | None = None,
    model: str | None = None,
    json_mode: bool = True,
    temperature: float = 0.7,
) -> str:
    backend = backend or os.environ.get("SYNTHPANEL_BACKEND", "ollama")
    if backend == "ollama":
        return _ollama(prompt, system, model or OLLAMA_MODEL, json_mode, temperature)
    if backend == "anthropic":
        return _anthropic(prompt, system, model or ANTHROPIC_MODEL, json_mode, temperature)
    raise ModelError(f"Unbekanntes Backend: {backend!r} (erlaubt: ollama, anthropic)")


def _ollama(prompt, system, model, json_mode, temperature) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
        # Thinking-Modelle (qwen3*, ...) befüllen sonst nur das Reasoning und lassen
        # content leer, sobald format=json gesetzt ist. Reasoning hier abschalten.
        "think": False,
    }
    if json_mode:
        body["format"] = "json"

    def _post(payload: dict) -> str:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["message"]["content"]

    try:
        return _post(body)
    except urllib.error.HTTPError as exc:
        # Nicht-Thinking-Modelle lehnen das think-Feld ab → ohne wiederholen.
        if exc.code == 400:
            body.pop("think", None)
            try:
                return _post(body)
            except urllib.error.URLError as exc2:
                raise ModelError(f"Ollama-Call fehlgeschlagen ({model}): {exc2}") from exc2
        raise ModelError(f"Ollama HTTP {exc.code} ({model}): {exc}") from exc
    except urllib.error.URLError as exc:
        raise ModelError(
            f"Ollama nicht erreichbar ({model} @ {OLLAMA_URL}): {exc}. "
            f"Läuft Ollama? Modell gezogen? (ollama pull {model})"
        ) from exc
    except (KeyError, json.JSONDecodeError) as exc:
        raise ModelError(f"Unerwartete Ollama-Antwort: {exc}") from exc


def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Embeddings über Ollama (gratis, lokal) — für semantisches Clustering der
    Reibungspunkte. Wirft ModelError, wenn nicht verfügbar (Aufrufer fällt zurück)."""
    if not texts:
        return []
    model = model or os.environ.get("SYNTHPANEL_EMBED_MODEL", "nomic-embed-text")
    body = {"model": model, "input": texts}
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embed",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["embeddings"]
    except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        raise ModelError(f"Embeddings nicht verfügbar ({model} @ {OLLAMA_URL}): {exc}") from exc


def _anthropic(prompt, system, model, json_mode, temperature) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise ModelError("anthropic-Paket fehlt: pip install anthropic") from exc

    client = anthropic.Anthropic()  # liest ANTHROPIC_API_KEY aus der Umgebung
    sys = system
    if json_mode:
        sys = (sys + "\n\nAntworte AUSSCHLIESSLICH mit gültigem JSON, ohne Markdown.").strip()
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=2048,
            temperature=temperature,
            system=sys,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # anthropic.APIError u.a.
        raise ModelError(f"Anthropic-Call fehlgeschlagen ({model}): {exc}") from exc
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
