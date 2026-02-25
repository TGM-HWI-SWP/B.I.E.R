# Test-Dokumentation

## Übersicht

Dieses Dokument beschreibt die Test-Strategie und Test-Struktur des B.I.E.R-Projekts.

**Test-Framework:** pytest 9+  
**Test-Ergebnis (Stand 2026-02-25):** 49 passed, 2 skipped (1.74 s)

---

## Test-Strategie

Das Projekt verwendet drei Teststufen:

| Stufe | Datei | Zweck |
|---|---|---|
| Unit | `tests/unit/test_domain.py` | Services isoliert, ohne Datenbankverbindung |
| Integration (Services) | `tests/integration/test_integration.py` | Mehrere Services zusammen |
| Integration (Flask) | `tests/integration/test_flask.py` | HTTP-Routen via Flask-Test-Client |
| Live (Docker) | `tests/integration/test_mongodb.py` | Echter Ping gegen MongoDB (auto-skip) |

Die MongoDB-Abhängigkeit wird in allen nicht-Live-Tests durch ein `MagicMock` ersetzt.

---

## Shared Fixtures (`tests/conftest.py`)

```python
mock_db           # MagicMock, mimics MongoDBAdapter
product_service   # ProductService(mock_db)
warehouse_service # WarehouseService(mock_db)
inventory_service # InventoryService(mock_db)
flask_client      # app.test_client() mit monkeypatched _db
```

Der `flask_client`-Fixture monkeypatcht `bierapp.frontend.flask.gui._db` auf das `mock_db`-Objekt, sodass keine echte MongoDB-Verbindung aufgebaut wird.

---

## Unit Tests – `tests/unit/test_domain.py`

### TestProductService (10 Tests)

| Test | Prüft |
|---|---|
| `test_create_product_returns_doc_with_id` | Gibt Dokument mit `_id` zurück, ruft `insert` auf |
| `test_create_product_strips_whitespace` | Trimmt führende/nachfolgende Leerzeichen |
| `test_create_product_empty_name_raises` | `ValueError` bei leerem Namen |
| `test_create_product_negative_weight_raises` | `ValueError` bei negativem Gewicht |
| `test_get_product_delegates_to_db` | Delegiert an `find_by_id` |
| `test_list_products_delegates_to_db` | Gibt `find_all`-Ergebnis zurück |
| `test_update_product_raises_for_missing` | `KeyError` bei fehlendem Dokument |
| `test_update_product_calls_db_update` | Ruft `db.update` auf |
| `test_delete_product_calls_db_delete` | Ruft `db.delete` auf |
| `test_delete_product_raises_for_missing` | `KeyError` bei fehlendem Dokument |

### TestWarehouseService (6 Tests)

| Test | Prüft |
|---|---|
| `test_create_warehouse_returns_doc` | Gibt Dokument zurück, persistiert |
| `test_create_warehouse_empty_name_raises` | `ValueError` bei leerem Lagernamen |
| `test_create_warehouse_zero_plaetze_raises` | `ValueError` bei `max_plaetze=0` |
| `test_create_warehouse_negative_plaetze_raises` | `ValueError` bei negativem Wert |
| `test_update_warehouse_raises_for_missing` | `KeyError` wenn Lager nicht gefunden |
| `test_delete_warehouse_raises_for_missing` | `KeyError` wenn Lager nicht gefunden |

### TestInventoryService (10 Tests)

| Test | Prüft |
|---|---|
| `test_add_product_inserts_new_entry` | Erstellt neuen Inventar-Eintrag |
| `test_add_product_merges_existing` | Addiert Menge zu vorhandenem Eintrag |
| `test_add_product_negative_menge_raises` | `ValueError` bei negativer Menge |
| `test_update_quantity_raises_for_missing_entry` | `KeyError` bei fehlendem Eintrag |
| `test_update_quantity_negative_raises` | `ValueError` bei negativer Menge |
| `test_remove_product_calls_delete` | Ruft `db.delete` auf |
| `test_remove_product_raises_for_missing` | `KeyError` bei fehlendem Eintrag |
| `test_list_inventory_raises_for_missing_lager` | `KeyError` wenn Lager nicht existiert |
| `test_list_inventory_enriches_entries` | Ergänzt Einträge mit Produktname |

---

## Service-Integrationstests – `tests/integration/test_integration.py`

| Test | Prüft |
|---|---|
| `test_create_product_then_add_to_warehouse` | Produkt erstellen + Lager erstellen + einbuchen (3x insert) |
| `test_add_product_merge_increases_total` | Zweites Einbuchen addiert Menge korrekt |
| `test_update_then_remove_lifecycle` | Menge ändern + ausbuchen (update + delete) |
| `test_list_inventory_includes_product_details` | Anreicherung mit Produktdaten |
| `test_update_preserves_unspecified_fields` | Update überschreibt alle Pflichtfelder |

---

## Flask-Integrationstests – `tests/integration/test_flask.py`

### TestStaticAndDashboard (2 Tests)
- `test_index_returns_200` – GET `/` gibt HTTP 200 zurück
- `test_index_contains_stat_cards` – Response enthält Schlüsselwort "Produkte"

### TestProdukte (6 Tests)
- `test_list_returns_200` – GET `/produkte` gibt 200 zurück
- `test_create_valid_redirects` – POST mit gültigen Daten → 302, `insert` wird aufgerufen
- `test_create_empty_name_redirects_with_flash` – Leerer Name → 302, kein `insert`
- `test_create_negative_weight_redirects_with_flash` – Negatives Gewicht → 302, kein `insert`
- `test_update_missing_redirects` – Update bei fehlendem Dokument → 302 (kein Crash)
- `test_delete_missing_redirects` – Löschen bei fehlendem Dokument → 302

### TestLager (4 Tests)
- `test_list_returns_200` – GET `/lager` gibt 200 zurück
- `test_create_valid_redirects` – Gültiges POST → 302, `insert` aufgerufen
- `test_create_empty_name_redirects_without_insert` – Leerer Name → kein `insert`
- `test_create_zero_plaetze_redirects_without_insert` – `max_plaetze=0` → kein `insert`

### TestInventar (7 Tests)
- `test_inventar_empty_lager_returns_200` – Keine Lager → Leer-Zustand 200
- `test_inventar_redirects_to_first_lager` – Lager vorhanden → Redirect zu erstem Lager
- `test_inventar_detail_returns_200` – GET `/inventar/<id>` gibt 200 zurück
- `test_inventar_detail_unknown_lager_redirects` – Unbekannte ID → 302
- `test_inventar_add_valid_redirects` – Einbuchen → 302
- `test_inventar_update_quantity_redirects` – Menge ändern → 302, `update` aufgerufen
- `test_inventar_remove_redirects` – Ausbuchen → 302, `delete` aufgerufen

---

## Live-Tests – `tests/integration/test_mongodb.py`

**Werden automatisch übersprungen**, wenn kein MongoDB-Server auf `localhost:27017` erreichbar ist.

```
pytest -m live   # Nur Live-Tests ausführen (nach docker compose up)
```

---

## Test-Ausführung

```bash
# Alle Tests
pytest tests/ -v

# Nur Unit-Tests
pytest tests/unit/ -v

# Nur Integrationstests (ohne Live)
pytest tests/integration/test_flask.py tests/integration/test_integration.py -v

# Mit Coverage-Report
pytest --cov=src tests/ --cov-report=html

# Einzelnen Test ausführen
pytest tests/unit/test_domain.py::TestProductService::test_create_product_returns_doc_with_id -v
```

---

## Test-Naming-Konvention

```
test_<component>_<action>_<expected_result>

Beispiele:
  test_create_product_empty_name_raises        ✓
  test_inventar_redirects_to_first_lager       ✓
  test_add_product_merge_increases_total       ✓
  test_list_inventory_enriches_entries         ✓
```

---

**Letzte Aktualisierung:** 2026-02-25
