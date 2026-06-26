# SynthPanel

**Lass viele verschiedene Test-Personas auf deinen Text schauen, bevor echte Menschen es tun.**

Du gibst eine Textdatei — einen Pitch, ein App-Konzept, einen Store-Text — und eine kurze Beschreibung, wen du erreichen willst. SynthPanel schickt eine Gruppe sehr unterschiedlicher Test-Personas durch deinen Text: den ungeduldigen Laien, den Skeptiker, den Preisbewussten, jemanden mit Screenreader, jemanden der einfache Sprache braucht, und ein „Rotes Team", das dein Produkt absichtlich auseinandernimmt. Jede sagt dir, woran sie hängenbleibt — mit dem wörtlichen Zitat der Stelle, die das ausgelöst hat.

**Für wen:** für Leute, die mit der Kommandozeile umgehen können — Entwickler, Maker, technische Gründer.

## So sieht das Ergebnis aus

Eine nach Schwere sortierte Liste, direkt im Terminal:

```
[HOCH] Der Preis steht nirgends — getroffen von 7 von 11 Personas
   Zitat: »Jetzt kostenlos starten«
   Vorschlag: Was es nach der Gratis-Phase kostet, gehört sichtbar nach oben.

[MITTEL] Unklar, für wen das gedacht ist — getroffen von 4 von 11 Personas
   Zitat: »die beste Lösung für alle«
   Vorschlag: Eine konkrete Zielgruppe nennen statt „für alle".
```

Dazu ein **Dissens-Teil** (wichtige Einzelstimmen, die nicht weggemittelt werden) und ein ehrlicher **Abdeckungs-Bericht**: welche Blickwinkel kamen vor — und welche nicht. Der Bericht läuft wahlweise farbig oder als reiner Text (für Screenreader geeignet).

## Was es ist — und was nicht
- **Es findet Probleme**, die du selbst übersiehst — blinde Flecken aus fremden Blickwinkeln.
- **Es misst nichts.** Keine Prozente, keine „73 % mochten es". Ein Sprachmodell ist gut darin, Probleme zu *finden*, und schwach darin, Häufigkeiten zu *schätzen* — SynthPanel nutzt nur die Stärke.
- **Es ersetzt keine echten Nutzer.** Es ist der kostenlose erste Durchgang davor — am stärksten, solange du noch keinen Prototyp hast.

## Schnellstart

```
pip install pyyaml rich pydantic
ollama pull qwen3.5:4b
python -m synthpanel run mein_text.md --audience "wen du erreichen willst"
```

`ollama pull` lädt ein Sprachmodell auf deinen Rechner. **Es läuft danach lokal — keine laufenden Kosten, keine Cloud.** Dein Text verlässt deinen Rechner nicht. Nur wenn du keine passende Hardware hast, kannst du mit `--backend anthropic` auf einen Cloud-Anbieter wechseln; dann geht der zu prüfende Text an diesen Anbieter, und es kostet pro Lauf (eine Warnung mit Kostenschätzung erscheint vorher).

**Das Modell bestimmt die Tiefe:** ein kleines Modell ist schnell, aber oberflächlich. Für ernste Analysen ein größeres lokales Modell oder einen starken Cloud-Anbieter. Welches Modell lief, steht immer im Bericht — nichts ist eine Black Box.

## Gegen Schönfärberei
Sprachmodelle neigen zum Schmeicheln. Drei Gegenmittel sind eingebaut: jede Bewertung wird einmal befürwortend und einmal kritisch abgefragt und dann zusammengeführt; das „Rote Team" ist immer dabei; und die eine wichtige Gegenstimme wird hervorgehoben statt weggerechnet.

## Eigene Test-Personas
Die Personas stehen in einer einfachen, versionierten Datei. Du kannst eigene ergänzen — lokale Zielgruppen oder zusätzliche Profile für Barrierefreiheit. Beiträge sind willkommen.

## Lizenz
MIT — frei nutzbar, auch kommerziell.
