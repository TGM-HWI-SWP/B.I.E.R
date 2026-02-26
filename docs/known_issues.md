# Known Issues

## Aktuelle Probleme

### Kritisch
- Keine kritischen Issues bekannt.

### Hoch
- **MongoDB offline → Flask-Absturz**: Wenn beim Start der Flask-App keine MongoDB-Verbindung hergestellt werden kann, wirft `MongoDBAdapter.connect()` einen `ConnectionError`. Es gibt derzeit keine Retry-Logik oder Fallback-Seite.
  - *Workaround:* Docker Stack zuerst starten (`docker compose up mongodb`), dann die App.

### Mittel
- **Keine Pagination**: `find_all()` lädt uneingeschränkt alle Dokumente einer Collection. Bei sehr großen Datenmengen kann die UI träge werden.
- **Kein CSRF-Schutz**: POST-Formulare sind nicht durch CSRF-Token geschützt (kein Flask-WTF eingebunden).
- **Keine Authentifizierung**: Alle Routen sind ohne Login erreichbar.

### Niedrig
- **Favicon 404 im Test**: Der Favicon-Endpunkt (`/favicon.ico`) sucht `BIER_ICON_COMPRESSED.png` im `pictures/`-Ordner. Wenn die Datei fehlt (z. B. in CI), gibt Flask eine 404-Antwort.
- **Flash-Messages nach Redirect**: In seltenen Fällen (mehrere schnelle Submits) können Flash-Messages einer älteren Session angezeigt werden.

---

## Gelöste Issues

### v1.0
- ✅ `pyproject.toml`: Paketpfad falsch (`src.bierapp` statt `bierapp`) → behoben durch `package-dir = {"" = "src"}`
- ✅ `import os` in mehreren Dateien → ersetzt durch `from os import environ, path` (Style-Guide)
- ✅ `_db: MongoDBAdapter | None` → `Optional[MongoDBAdapter]` (Python 3.10-Kompatibilität + Style-Guide)
- ✅ Inline-Import innerhalb Routen-Funktion → an Modul-Top verschoben

### v0.2
- ✅ `test_mongodb.py` hing beim CI ohne MongoDB → jetzt mit `skipif`-Decorator

---

## Bekannte Limitationen

| Bereich | Limitation |
|---|---|
| Authentifizierung | Nicht implementiert (außerhalb Projektumfang) |
| Pagination | Nicht implementiert |
| CSRF | Nicht implementiert |
| Mehrsprachigkeit | Nur Deutsch |
| Bilder/Datei-Upload | Nicht implementiert |
| Benutzerrollen | Nicht implementiert |

---

**Letzte Aktualisierung:** 2026-02-26
