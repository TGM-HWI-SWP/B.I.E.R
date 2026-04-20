# Style Guide

In general, we try to follow the [PEP8 Style Guide](https://peps.python.org/pep-0008/) with limited adaptations for ease-of-use.

---

## Doc-Strings

All doc strings are written in a slightly modified **Google Style**.

### Explanation

Write a short explanation of the function itself.

### Args

Display all defined arguments used in the function, as well as the use case of the argument.

**How to display:**

1. Name with datatype in round brackets
2. Explanation of the argument

**Example:**

```
message_id (int): The ID of the message to be translated.
```

### Returns

Display the return/returns of the function. Firstly, write the datatype, then a short explanation.

**How to display:**

1. Datatype
2. Explanation of the return

**Example:**

```
str: The translated message
```

---

## Imports

The imports are divided into two categories:

1. Python core/standard libraries
2. Custom files/libraries/scripts

These categories are separated by skipping a line.

### Python core/standard library

All imports from standard libraries must be on top of the code, using `from` imports to make sure they work properly.

### Python custom files/libraries/scripts

Write them after skipping a line under all the core libraries, also using `from` imports to make sure they work properly.

---

## Variable Naming

| Type     | Convention     | Example         |
| -------- | -------------- | --------------- |
| Variable | `snake_case` | `hello_world` |
| Class    | `CapWords`   | `MyClass`     |
| Constant | `ALL_CAPS`   | `MYCONSTANT`  |

---

## Comments

Docstrings are the **primary way** of communicating a function's purpose and details.

Comments should only be used to specify certain in-line details — for example, mathematical formulas in the middle of a code chunk.

---

## Security & Auth Conventions

- Never store plain text passwords in MongoDB; only `generate_password_hash(...)` output is persisted.
- Any manager-only route must be guarded via `_require_manager()`.
- User mutations must preserve a safe baseline:
	- no self-deactivation,
	- no demotion of own manager role to clerk,
	- at least one active manager remains.

---

## Audit Logging Conventions

- User administration changes must create an event in `events` with `entity_type = user_admin`.
- Required event fields for user-admin actions:
	- `timestamp`, `action`, `performed_by`, `summary`, `entity_id`, `details.target_username`, `details.changes`.
- Audit logging should not block the main mutation path; failures in logging should degrade gracefully.

---

## Documentation Maintenance Rule

When adding routes, pages, collections, or persistence behavior, update all markdown docs in the same change set:

- `README.md`
- `docs/architecture.md`
- `docs/contracts.md`
- `docs/tests.md`
- `docs/style_guide.md`

This keeps code and docs synchronized.

---

**Letzte Aktualisierung:** 2026-04-20
