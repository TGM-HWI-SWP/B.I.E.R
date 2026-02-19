# Git-Workflow für dieses Projekt

## Branch-Struktur

```
main (stable)
  └─ develop (integration)
      ├─ feature/rolle1/... (Contract Owner)
      ├─ feature/rolle2/... (Businesslogik & Report A)
      ├─ feature/rolle3/... (Report B & Tests)
      └─ feature/rolle4/... (GUI)
```

## Commit-Nachricht Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type
- `feat`: Neue Funktion
- `fix`: Bug-Fix
- `docs`: Dokumentation
- `test`: Tests
- `refactor`: Code-Umstrukturierung
- `ci`: CI/CD-Konfiguration

### Scope (optional)
- `domain`
- `service`
- `ui`
- `tests`
- `docs`
- `repo`

### Beispiele

```bash
git commit -m "feat(domain): add Product.update_quantity method"
git commit -m "test(service): add test_warehouse_service_add_to_stock"
git commit -m "docs(architecture): update contracts documentation"
git commit -m "fix(ui): resolve table layout issue"
```

## Workflow pro Feature

```bash
# 1. Neuen Branch erstellen
git checkout develop
git pull origin develop
git checkout -b feature/rolle2/product-validation

# 2. Entwickeln & committen
# ... Code schreiben ...
git add .
git commit -m "feat(domain): add price validation to Product"

# 3. Regelmäßig pushen
git push origin feature/rolle2/product-validation

# 4. Pull Request erstellen (auf develop)
# → Code Review
# → Mergekonflikte lösen (falls nötig)
# → Merge

# 5. Zurück zu develop
git checkout develop
git pull origin develop
```

## Mergekonflikt-Handling

### Konflikt erkennen
```bash
git status
# Conflict: product.py
```

### Auflösen
```bash
# 1. Konflikt-Marker anschauen
<<<<<<< HEAD
    # Deine Version
=======
    # Ihre Version
>>>>>>> feature/...

# 2. Korrekt zusammenführen
# 3. Tests ausführen
pytest

# 4. Commiten
git add product.py
git commit -m "fix: resolve merge conflict in product.py"
git push
```

### Dokumentation
**In:** `docs/changelog_<name>.md`
```markdown
## Mergekonflikte
- [Datei]: [Kurzbeschreibung und Lösung]
```

## Versioning & Tags

```bash
# Version erstellen
git tag -a v0.1 -m "v0.1 - Projektstart und Grundarchitektur"
git push origin v0.1

# Changelog aktualisieren
# → docs/changelog_<name>.md mit Commits aktualisieren
```

## Best Practices

1. **Kleine, häufige Commits** statt wenige große
2. **Aussagekräftige Commit-Messages**
3. **Vor dem Push testen:** `pytest` ausführen
4. **Regelmäßig pullen** um mit develop synchron zu bleiben
5. **Code-Reviews** vor dem Merge
6. **Konflikt-Dokumentation** nicht vergessen

---

[Zurück zum README](../README.md)
