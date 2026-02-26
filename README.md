<p align="center">
  <img src="src/resources/pictures/BIER_LOGO_SCHWARZ_COMPRESSED.png" alt="B.I.E.R Logo" width="300"/>
</p>

# B.I.E.R - Büro-Inventar- und Einkaufs-Register

> **Important Note – AI-generated test branch**
>
> This is **not** the main / production branch of B.I.E.R. The code and documentation here were created **almost entirely with AI support** as an experiment and **must be treated as a test version only**. For authoritative source code, architecture and grading-relevant artifacts, always refer to the official main branch provided.

A warehouse management web application built with Python, Flask, MongoDB, and Docker.

---

## About

This project was developed as part of the Software Development and Project Management (SWP) course at TGM - Die Schule der Technik, Vienna, Austria (2026).

**Project Team:**

- Paul Hinterbauer
- Mateja Gvozdenac
- Dragoljub Mitrovic
- Emir Keser

---

## Features

- **Inventory Management** – Track and manage warehouse stock across multiple locations
- **Modern Flask Web UI** – 5 Seiten (Produkte, Produkt bearbeiten, Lager, Statistik, Historie) mit Dark-Theme
- **Multi-Lager-Unterstützung** – Pro Produkt unterschiedliche Bestände in mehreren Lagern pflegen
- **Event-Historie** – Alle Änderungen an Produkten, Lagern und Beständen werden in einer eigenen Historie erfasst
- **Reporting** – Zwei Reports (Bestandsreport und Statistikreport) erzeugen aus den gespeicherten Daten auswertbare Textdateien
- **MongoDB Backend** – Persistente Datenspeicherung inkl. Event-Historie
- **Port-Adapter Architecture** – Clean, testable, and maintainable codebase (Hexagonale Architektur)
- **Docker Support** – One-command deployment with Docker Compose

---

## Prerequisites

- **Python 3.10+**
- **Docker Desktop** - Required for containerized deployment

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd B.I.E.R
```

### 2. Run with Docker

Start all services (Flask app, MongoDB, Mongo Express) with a single command:

```bash
docker compose up --build
```

### 3. Run Locally (without Docker)

```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac

# Install dependencies (inkl. Dev-Tools)
pip install -e .[dev]

# Run tests
pytest
```

---

## Usage

Once running, the following services are available:

| Service       | URL                                         | Description         |
| ------------- | ------------------------------------------- | ------------------- |
| Flask App     | [http://localhost:5000](http://localhost:5000) | Main web interface  |
| Mongo Express | [http://localhost:8081](http://localhost:8081) | Database management |

---

## Reports & Exports

### Inventory & Statistics Reports (CLI)

Die beiden Reports sind als eigenständige Komponenten implementiert und können direkt über Python ausgeführt werden (innerhalb des aktivierten virtuellen Environments):

```bash
cd B.I.E.R
.venv\Scripts\activate  # oder entsprechendes Activate-Skript

# Statistikreport (globale KPIs)
python -m bierapp.reports.statistics_report

# Bestandsreport über alle Lager
python -m bierapp.reports.inventory_report

# Optional: nur ein bestimmtes Lager
python -m bierapp.reports.inventory_report <lager_id>
```

Die Report-Dateien werden im Ordner [src/bierapp/reports/output](src/bierapp/reports/output) abgelegt:

- Statistik: [src/bierapp/reports/output/statistics.txt](src/bierapp/reports/output/statistics.txt)
- Globaler Bestandsreport: [src/bierapp/reports/output/inventory_all.txt](src/bierapp/reports/output/inventory_all.txt)
- Lager-spezifische Reports: [src/bierapp/reports/output](src/bierapp/reports/output) (Dateiname `inventory_<lager_id>.txt`)

### Historie als TXT aus der UI exportieren

Auf **Page 5 – Historie** (`/ui/historie`) gibt es einen Button *„Historie als TXT exportieren“*.

- Ein Klick erzeugt on-the-fly eine Textdatei mit allen Historien-Einträgen.
- Der Browser bietet diese Datei direkt als Download (`history.txt`) an – es wird kein zusätzlicher Ordner im Projekt angelegt.

---

## Architecture

```
Frontend (Flask)
      |
  Backend (Logic)
      |
   DB (MongoDB)
```

- **Frontend** - Flask routes and Jinja2 templates (`src/bierapp/frontend/`)
- **Backend** - Business logic (`src/bierapp/backend/`)
- **DB** - MongoDB adapter (`src/bierapp/db/`)
- **Contracts** - Shared interfaces (`src/bierapp/contracts.py`)

---

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest --cov=src tests/
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
