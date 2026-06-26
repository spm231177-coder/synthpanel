# Beitragen zu SynthPanel

Danke, dass du SynthPanel besser machen willst. Der wertvollste Beitrag ist meist
**eine neue Test-Persona (Lens)** — denn die Vielfalt der Blickwinkel ist der Kern.

## Eine Lens beitragen

Lenses leben in [`synthpanel/lenses/library.yaml`](synthpanel/lenses/library.yaml).
Eine neue Persona ist ein Eintrag:

```yaml
  - id: senior_skeptisch
    name: "Senior:in, 70+, skeptisch gegenüber Technik"
    kind: standard          # standard | barrier | red_team
    provenance: sampled
    tags: [alter, technik-skepsis]
    persona: >
      Du bist über 70, nutzt ein Smartphone nur für das Nötigste und bist bei
      allem Neuen vorsichtig. Fachbegriffe verunsichern dich. Du fragst dich bei
      jedem Schritt: Mache ich gerade etwas kaputt? Kostet mich das heimlich Geld?
```

**Worauf wir achten:**
- **Eine klare *Lage*, nicht nur Demografie.** Eine Lens hat eine Haltung, einen
  Kontext, ein Vorwissen — nicht nur Alter und Einkommen.
- **`kind: barrier`** für Barriere-Profile (Screenreader, einfache Sprache, Motorik,
  kognitive Last, Farbfehlsichtigkeit, Hörbehinderung). Diese werden **besonders
  sorgfältig** reviewt — ein unrealistisches Barriere-Profil ist schlimmer als keins.
  Orientiere dich an realen Assistenz-Szenarien und WCAG-Personas, nicht an Klischees.
- **`kind: red_team`** für Personas, die das Produkt absichtlich zerlegen.
- **Keine Beleidigungen, keine echten Personen.** Archetypen, keine Karikaturen.

**Lokale/sprachliche Sets** (z.B. eine US-, AT-, CH-Population) sind willkommen — gern
als eigene `library_<region>.yaml`, die per `--library` geladen wird.

## Code-Beiträge

- `python tests/test_synthesis.py` muss grün bleiben (Offline-Tests, kein Modell nötig).
- Halte den Kern **dependency-arm** — der 0-€-Pfad (Ollama via Standardbibliothek) darf
  keine neuen Pflicht-Abhängigkeiten bekommen.
- Stil: klar, kommentiert wo es nicht offensichtlich ist.

## Leitlinie

SynthPanel ist ein **Such-Werkzeug**, kein Mess-Werkzeug. Beiträge, die Prozente,
Repräsentativitäts-Versprechen oder „Scores als Wahrheit" einführen, passen nicht zur
Philosophie — wir behaupten nie eine Zahl, die wir nicht haben.
