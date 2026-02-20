# Projekt-Template Index

## 🎯 START HIER

1. **Zum Verstehen der Vorlage:** [TEMPLATE_INFO.md](TEMPLATE_INFO.md)
2. **Projektübersicht:** [README.md](README.md)
3. **Git-Workflow:** [GIT_WORKFLOW.md](GIT_WORKFLOW.md)

---

## 📁 Datei-Struktur

### 🔧 Konfiguration
```
pyproject.toml          Python-Projektconfig & Dependencies
.gitignore              Git-Ignore-Regeln
.pylintrc               Linting-Konfiguration
.flake8                 Code-Style-Konfiguration
```

### 📚 Dokumentation
```
README.md               Komplette Projekt-Übersicht
TEMPLATE_INFO.md        Info über diese Vorlage
GIT_WORKFLOW.md        Git Best Practices & Workflow

docs/
  ├── architecture.md    Architektur-Dokumentation
  ├── contracts.md       Schnittstellen-Dokumentation (Rolle 1)
  ├── tests.md           Test-Strategie
  ├── projektmanagement.md  PM-Dokumente (PSP, Gantt, etc.)
  ├── retrospective.md   Retrospektive-Vorlage
  ├── changelog_template.md  Persönliche Changelog-Vorlage
  └── known_issues.md    Known Issues & Limitations
```

### 💻 Quellcode
```
src/
  ├── domain/           Geschäftslogik (Product, Warehouse)
  │   ├── product.py    Produktklasse
  │   └── warehouse.py  Lagerverwaltung
  ├── ports/            Schnittstellen-Definitionen
  ├── adapters/         Konkrete Implementierungen
  │   ├── repository.py  In-Memory, SQLite, JSON
  │   └── report.py     Report-Generierung
  ├── services/         Business Logic Service
  ├── ui/               PyQt6 Benutzeroberfläche
  └── reports/          Report-Module
```

### 🧪 Tests
```
tests/
  ├── unit/            Unit-Tests
  ├── integration/      Integration-Tests
  └── conftest.py      Pytest-Konfiguration
```

### 📦 Daten
```
data/                   Speicherort für Daten (SQLite, JSON, etc.)
```

---

## 🚀 Quick Start (5 Minuten)

```bash
# 1. Setup
pip install -e .
pip install -e ".[dev]"

# 2. Verifikation
pytest tests/ -v

# 3. GUI Starten (optional)
python -m src.ui

# 4. Git initialisieren
git init
git add .
git commit -m "Initial: Projektvorlage v0.1"
```

---

## 📖 Dokumentations-Guide

### Schüler/innen sollten lesen:
1. **[TEMPLATE_INFO.md](TEMPLATE_INFO.md)** - Was ist enthalten?
2. **[README.md](README.md)** - Projektübersicht
3. **[docs/architecture.md](docs/architecture.md)** - Wie funktioniert's?
4. **[GIT_WORKFLOW.md](GIT_WORKFLOW.md)** - Git Best Practices
5. **[docs/contracts.md](docs/contracts.md)** - Schnittstellen verstehen

### Während der Entwicklung:
- **[docs/tests.md](docs/tests.md)** - Wie teste ich?
- **[docs/known_issues.md](docs/known_issues.md)** - Was ist bekannt kaputt?
- **[docs/changelog_template.md](docs/changelog_template.md)** - Persönliche Dokumentation

### Lehrpersonen:
- **[LEHRERINFO.md](LEHRERINFO.md)** - Alles für die Lehrperson
- **[docs/projektmanagement.md](docs/projektmanagement.md)** - PSP, Gantt, Rollen

---

## 🎓 Was ist bereits vorbereitet?

### ✅ Code
- [x] Domain-Modelle (Product, Warehouse, Movement)
- [x] Port-Adapter-Architektur
- [x] Service-Layer (WarehouseService)
- [x] In-Memory Repository
- [x] Report-Adapter (Console)
- [x] PyQt6 GUI-Skeleton
- [x] Unit & Integration Tests

### ✅ Dokumentation
- [x] Architektur-Dokumentation
- [x] Schnittstellen-Dokumentation
- [x] Test-Strategie
- [x] Projektmanagement-Vorlage
- [x] Retrospektive-Vorlage
- [x] Changelog-Vorlage
- [x] Known Issues Template

### ✅ Konfiguration
- [x] pyproject.toml mit Dependencies
- [x] pytest-Konfiguration
- [x] Code-Style-Einstellungen
- [x] .gitignore

---

## 📅 Vorgesehene Meilestones

| Version | Woche | Fokus |
|---------|-------|-------|
| **v0.1** | 1-2 | Projektstart, Rollen, erste Contracts |
| **v0.2** | 2-3 | Architektur & Walking Skeleton |
| **v0.3** | 3 | Kernlogik & GUI-Minimum |
| **v0.4** | 4-6 | Reports implementieren |
| **v0.5** | 7 | Tests & Stabilisierung |
| **v1.0** | 8 | Fertig, stabil, präsentierbar |

---

## 🔧 Was Schüler/innen erweitern müssen

### Phase 1: Verstehen (Woche 1-2)
- [ ] Code lesen und verstehen
- [ ] Architecture.md durcharbeiten
- [ ] Erstes Mergekonflikt als Lernchance

### Phase 2: Erweitern (Woche 2-6)
- [ ] Datenbank-Adapter implementieren
- [ ] Report B (Grafiken)
- [ ] GUI
- [ ] Test-Coverage erhöhen

### Phase 3: Stabilisieren (Woche 7-8)
- [ ] Bugs fixen
- [ ] Documentation vollständig
- [ ] Tests 90%+ Coverage
- [ ] Präsentation vorbereiten

---

## 🎯 Erfolgs-Indikatoren

**v0.1:**
- Tests laufen grün ✓
- Rollen klar verteilt ✓
- Erstes Git-Repo initialisiert ✓

**v0.5:**
- 80%+ Test-Coverage ✓
- Alle Reports funktionieren ✓
- Mergekonflikte dokumentiert gelöst ✓

**v1.0:**
- 90%+ Test-Coverage ✓
- Alle Dokumentationen fertig ✓
- Präsentation funktioniert ✓
- Keine kritischen Bugs ✓

---

## 📞 Häufig gefragt

**F: Wo finde ich Beispiel-Tests?**
→ [tests/unit/test_domain.py](tests/unit/test_domain.py)

**F: Wie starte ich die GUI?**
→ `python -m src.ui` (siehe [README.md](README.md))

**F: Was ist ein Mergekonflikt?**
→ [GIT_WORKFLOW.md](GIT_WORKFLOW.md#mergekonflikt-handling)

**F: Wie dokumentiere ich meine Arbeit?**
→ Persönliche `docs/changelog_<name>.md` führen

**F: Wer bin ich in dieser Vorlage?**
→ Siehe [docs/projektmanagement.md](docs/projektmanagement.md#rollenverteilung)

---

## 🔗 Wichtigste Links

| Ziel | Link |
|------|------|
| **Projekt verstehen** | [TEMPLATE_INFO.md](TEMPLATE_INFO.md) |
| **Architektur lernen** | [docs/architecture.md](docs/architecture.md) |
| **Schnittstellen verstehen** | [docs/contracts.md](docs/contracts.md) |
| **Tests schreiben** | [docs/tests.md](docs/tests.md) |
| **Git Workflow** | [GIT_WORKFLOW.md](GIT_WORKFLOW.md) |
| **PM-Struktur** | [docs/projektmanagement.md](docs/projektmanagement.md) |
| **Lehrperson-Info** | [LEHRERINFO.md](LEHRERINFO.md) |

---

## 📊 Dateigröße & Umfang

- **Python-Code:** ~1500 Zeilen
- **Tests:** ~250 Zeilen
- **Dokumentation:** ~3000 Zeilen Markdown (gerne auch KI-erstellt!)
- **Gesamtumfang:** Perfekt für 8-Wochen Projekt

---

## ✨ Highlights dieser Vorlage

1. **Port-Adapter-Architektur** - Professionelle Struktur lehren
2. **Komplette Tests** - Unit + Integration Tests vorbereitet
3. **Umfassende Dokumentation** - Alles erklärt
4. **Realistische Workflows** - Git, Mergekonflikte, Versionierung
5. **Schüler/innen-freundlich** - Starter-Code, aber viel zu tun
6. **Erweiterbar** - Einfach neue Features hinzufügen
7. **Prüfbar** - Klare Erfolgskriterien, Test-Coverage

---

**Version:** 0.1  
**Erstellt:** 2025-01-29 
**Für:** 5. Jahrgang Softwareentwicklung & Projektmanagement  
**Bearbeitungszeit:** 7-8 Wochen | 2 UE pro Woche
