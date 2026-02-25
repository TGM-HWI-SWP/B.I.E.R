# Retrospektive – B.I.E.R

## Projektübersicht

**Projekttitel:** B.I.E.R – Büro-Inventar- und Einkaufs-Register  
**Zeitraum:** Februar 2026  
**Schule:** TGM Wien – Die Schule der Technik (SWP 4BHWII)  
**Gruppenmitglieder:** Paul Hinterbauer, Mateja Gvozdenac, Dragoljub Mitrovic, Emir Keser

---

## Versionsmilestones

### v0.1 – Projektstart & Grundarchitektur
**Abschluss:** 2026-02-20

#### Was lief gut?
- Hexagonale Architektur von Beginn an klar definiert
- `contracts.py` als Single Source of Truth für alle Schnittstellen etabliert
- Docker Compose Stack auf Anhieb funktionsfähig
- Git-Workflow und Branching-Strategie früh festgelegt

#### Was konnte verbessert werden?
- `pyproject.toml` hatte falschen Package-Pfad (`src.bierapp` statt `bierapp`) → fiel erst bei Tests auf
- Anfangs keine klare Aufgabenteilung für Templates

#### Learnings
- Architektur-Entscheidungen (Ports & Adapters) zahlen sich spät aus – Testen wird deutlich einfacher
- `package-dir` in `pyproject.toml` korrekt setzen, bevor Code geschrieben wird

---

### v0.2 – MongoDB-Adapter & DB-Initialisierung
**Abschluss:** 2026-02-21

#### Was lief gut?
- `MongoDBAdapter` sauber als `DatabasePort`-Implementierung strukturiert
- Idempotentes Setup-Script (`db/init/setup.py`) funktioniert zuverlässig
- Unique Indexes auf Collections frühzeitig gesetzt

#### Was konnte verbessert werden?
- Kein Retry-Mechanismus bei fehlender Datenbankverbindung
- `import os` anstatt `from os import environ` – Style-Guide-Konflikt erst später bemerkt

#### Learnings
- Umgebungsvariablen konsequent über `from os import environ` beziehen
- BSON `ObjectId` muss immer zu `str` serialisiert werden bevor JSON-Ausgabe

---

### v0.3 – Flask-GUI & Business-Logik
**Abschluss:** 2026-02-22

#### Was lief gut?
- Bootstrap 5 + Bootstrap Icons ermöglichten schnelles, ansprechendes UI
- Lazy-Singleton-Pattern für DB und Services hält `gui.py` übersichtlich
- Alle CRUD-Workflows in einem Sprint implementiert
- Flash-Messages geben dem Nutzer direktes Feedback

#### Was konnte verbessert werden?
- Inline-Import innerhalb einer Route-Funktion → Style-Guide-Verstoß, später korrigiert
- Kein CSRF-Schutz in POST-Formularen

#### Learnings
- Flash-Messages + Redirect-After-Post-Pattern konsequent verwenden
- Templates von Beginn an mit einer `layout.html`-Basis aufbauen

---

### v1.0 – Tests, Style & Dokumentation
**Abschluss:** 2026-02-25

#### Was lief gut?
- 49 Tests in unter 2 Sekunden, vollständig ohne Datenbankverbindung
- `MagicMock` für `MongoDBAdapter` deckt alle Use-Cases ab
- `monkeypatch` für Flask-Test-Client funktioniert elegant ohne Umstrukturierung
- Style-Guide konsequent auf alle Python-Dateien angewendet

#### Was konnte verbessert werden?
- Tests hätten früher geschrieben werden sollen (Test-First hätte Bugs verhindert)
- `test_mongodb.py` hätte von Anfang an das `skipif`-Pattern verwenden sollen

#### Learnings
- Fixture-Design in `conftest.py` ist der Schlüssel zu wartbaren Tests
- `replace_string_in_file` bei Unicode-Zeichen in `oldString` sorgfältig prüfen

---

## Überblick: Stärken & Schwächen

### Team-Stärken
- Klare Architektur-Entscheidung am Anfang, konsequent durchgezogen
- Hexagonale Architektur ermöglichte paralleles Entwickeln (DB / Services / GUI)
- Code-Qualität durch Style-Guide und Docstrings einheitlich hoch

### Verbesserungspotenzial
- Tests früher im Entwicklungszyklus schreiben (TDD)
- CSRF-Schutz und Authentifizierung einplanen
- CI/CD-Pipeline für automatisches Testen bei jedem Push

---

## Technische Erkenntnisse

### Was funktioniert gut?
- **Port-Adapter-Architektur:** Services ohne DB testbar. `MagicMock` reicht für 49 Tests.
- **Docker Compose:** Ein Befehl startet gesamten Stack (MongoDB + Mongo Express + Flask)
- **Bootstrap 5 CDN:** Kein Build-Tool nötig, trotzdem professionelles UI

### Technische Schulden
- Keine Pagination für große Collections
- Kein Authentifizierungs-Layer
- Kein CSRF-Schutz auf POST-Routen
- Keine Benutzerrollen

### Empfehlungen für Folge-Projekte
1. `pyproject.toml` mit `package-dir` korrekt konfigurieren, bevor der erste Import geschrieben wird
2. `conftest.py` gleich am Projektbeginn mit Mock-Fixtures anlegen
3. Style-Guide von Anfang an als Linter-Regel einbinden (`flake8` / `pylint` in pre-commit)

---

## Abschließende Bewertung

| Kriterium | Bewertung (1–10) |
|---|---|
| Code-Qualität | 8 |
| Dokumentation | 9 |
| Tests | 8 |
| Architektur | 9 |
| **Durchschnitt** | **8.5** |

---

**Retrospektive erstellt:** 2026-02-25  
**Geschrieben von:** Paul Hinterbauer

