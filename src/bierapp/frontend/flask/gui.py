"""UI layer – Flask web interface for B.I.E.R.

This module wires together the Flask application, the database singleton,
and all route handlers. Route handlers are kept short by delegating complex
data computation to the helper functions in helpers.py.
"""

import json
from datetime import datetime, timedelta
from os import environ, path
from typing import Optional

from flask import (
    Flask,
    Response,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from bierapp.backend.inventory_service import InventoryService
from bierapp.backend.product_service import ProductService
from bierapp.backend.warehouse_service import WarehouseService
from bierapp.contracts import (
    DatabasePort,
    HttpResponsePort,
    InventoryServicePort,
    ProductServicePort,
    WarehouseServicePort,
)
from bierapp.db.mongodb import (
    COLLECTION_ABTEILUNGEN,
    COLLECTION_APP_SETTINGS,
    COLLECTION_BESTELLUNGEN,
    COLLECTION_EVENTS,
    COLLECTION_INVENTAR,
    COLLECTION_LAGER,
    COLLECTION_LIEFERANTEN,
    COLLECTION_PICKLISTEN,
    COLLECTION_PRODUKTE,
    COLLECTION_USERS,
    COLLECTION_USER_SETTINGS,
    MongoDBAdapter,
)
from bierapp.frontend.flask.helpers import (
    compute_category_counts,
    compute_top10_products,
    compute_utilisation,
    compute_warehouse_aggregates,
    compute_warehouse_stats,
    compute_warehouse_top_products,
    compute_warehouse_values,
    enrich_warehouses,
)
from bierapp.frontend.flask.http_adapter import FlaskHttpAdapter
from bierapp.reports.pdf_report import build_history_pdf, build_inventory_pdf, build_statistics_pdf

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

_HERE = path.dirname(__file__)
_DEFAULT_RESOURCES = path.abspath(path.join(_HERE, "..", "..", "..", "resources"))
_RESOURCES_BASE = environ.get("RESOURCES_DIR", _DEFAULT_RESOURCES)
RESOURCES_DIR = path.join(_RESOURCES_BASE, "pictures")
TEMPLATES_DIR = path.join(_RESOURCES_BASE, "templates")

app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = environ.get("FLASK_SECRET", "bier-dev-secret")
app.config["AUTH_REQUIRED"] = environ.get("AUTH_REQUIRED", "1") == "1"


def _build_default_users() -> dict:
    """Build the default in-memory user store.

    Returns:
        Mapping username -> user settings with role and password hash.
    """
    return {
        "admin": {
            "password_hash": generate_password_hash("admin"),
            "role": "manager",
            "display_name": "Administrator",
        },
        "lager": {
            "password_hash": generate_password_hash("lager"),
            "role": "clerk",
            "display_name": "Lager Team",
        },
    }


def _load_users() -> dict:
    """Load users from environment or fall back to local defaults.

    Environment format (JSON):
        {
            "admin": {"password": "secret", "role": "manager", "display_name": "Admin"}
        }

    Returns:
        Mapping username -> user settings with role and password hash.
    """
    configured = environ.get("BIER_USERS", "").strip()
    users = _build_default_users()
    if not configured:
        return users

    try:
        payload = json.loads(configured)
    except Exception:
        return users

    mapped = {}
    for username, values in payload.items():
        username_clean = str(username).strip()
        if not username_clean or not isinstance(values, dict):
            continue

        password = str(values.get("password", "")).strip()
        password_hash = str(values.get("password_hash", "")).strip()
        role = str(values.get("role", "clerk")).strip() or "clerk"
        display_name = str(values.get("display_name", username_clean)).strip() or username_clean

        if not password_hash and password:
            password_hash = generate_password_hash(password)

        if not password_hash:
            continue

        mapped[username_clean] = {
            "password_hash": password_hash,
            "role": role,
            "display_name": display_name,
        }

    return mapped or users


APP_USERS = _load_users()
UI_DEFAULT_SETTINGS = {
    "themeId": "bier-dark",
    "density": "comfortable",
    "motion": "full",
    "tableStripes": True,
    "glassCards": False,
    "fontScale": "normal",
    "startPage": "/ui/produkte",
    "compactSidebar": False,
    "flashDurationMs": 4000,
}
_ALLOWED_SETTING_KEYS = set(UI_DEFAULT_SETTINGS.keys())
_ROLE_POLICY_DEFAULT = {
    "clerk_defaults": dict(UI_DEFAULT_SETTINGS),
    "clerk_locked_keys": [],
}


def _sanitize_settings(values: dict) -> dict:
    """Filter incoming UI settings to allowed keys only.

    Args:
        values: Candidate settings dictionary.

    Returns:
        Sanitized settings dictionary.
    """
    if not isinstance(values, dict):
        return {}

    sanitized = {}
    for key, value in values.items():
        if key in _ALLOWED_SETTING_KEYS:
            sanitized[key] = value
    return sanitized


def _find_user_by_username(username: str) -> Optional[dict]:
    """Find a user document by username in MongoDB.

    Args:
        username: Login username.

    Returns:
        User document or None.
    """
    db = get_db()
    username_clean = (username or "").strip()
    if not username_clean:
        return None

    for user in db.find_all(COLLECTION_USERS):
        if str(user.get("username", "")).strip() == username_clean:
            return user

    return None


def _ensure_default_users_in_db() -> None:
    """Ensure built-in users exist in DB for initial login usage."""
    db = get_db()
    existing_users = db.find_all(COLLECTION_USERS)
    existing_usernames = {str(u.get("username", "")).strip() for u in existing_users}

    for username, cfg in APP_USERS.items():
        if username in existing_usernames:
            continue

        db.insert(
            COLLECTION_USERS,
            {
                "username": username,
                "password_hash": cfg.get("password_hash", ""),
                "role": cfg.get("role", "clerk"),
                "display_name": cfg.get("display_name", username),
                "active": True,
                "created_at": _now_utc_iso(),
            },
        )


def _normalize_user_role(role_raw: str) -> str:
    """Normalize a role string to supported values.

    Args:
        role_raw: Role value from request payload.

    Returns:
        Normalized role name.
    """
    role = str(role_raw or "").strip().lower()
    return role if role in ("manager", "clerk") else "clerk"


def _list_users_for_admin() -> list:
    """Return sanitized users for the admin user management page.

    Returns:
        Sorted list of user records.
    """
    _ensure_default_users_in_db()
    db = get_db()
    users = []
    for user in db.find_all(COLLECTION_USERS):
        username = str(user.get("username", "")).strip()
        if not username:
            continue

        role = _normalize_user_role(user.get("role", "clerk"))
        display_name = str(user.get("display_name", username)).strip() or username
        users.append(
            {
                "_id": user.get("_id", ""),
                "username": username,
                "display_name": display_name,
                "role": role,
                "active": bool(user.get("active", True)),
                "updated_at": user.get("updated_at", ""),
                "created_at": user.get("created_at", ""),
            }
        )

    users.sort(key=lambda row: (0 if row.get("role") == "manager" else 1, row.get("username", "").lower()))
    return users


def _find_user_by_id(user_id: str) -> Optional[dict]:
    """Resolve a user document by document id.

    Args:
        user_id: Mongo document id.

    Returns:
        User document or None.
    """
    return get_db().find_by_id(COLLECTION_USERS, user_id)


def _manager_count(users: list) -> int:
    """Count active manager users from a user list.

    Args:
        users: User record list.

    Returns:
        Number of active managers.
    """
    return sum(1 for user in users if user.get("role") == "manager" and user.get("active", True))


def _record_user_admin_event(
    action: str,
    target_username: str,
    summary: str,
    *,
    target_user_id: str = "",
    changes: Optional[dict] = None,
) -> None:
    """Persist an audit event for manager-driven user changes.

    Args:
        action: Action key such as create/update_role/update_status/reset_password.
        target_username: Username that was changed.
        summary: Human-readable summary for history views.
        target_user_id: Optional user document id.
        changes: Optional structured change set.
    """
    details = {
        "target_username": str(target_username or "").strip(),
        "changes": changes or {},
    }

    try:
        get_db().insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_utc_iso(),
                "entity_type": "user_admin",
                "entity_id": target_user_id,
                "action": action,
                "summary": summary,
                "performed_by": _current_username(),
                "details": details,
            },
        )
    except Exception:
        # Audit logging must never block core user-management actions.
        return


def _list_user_admin_audit_events(limit: int = 40) -> list:
    """Return latest user-admin audit events for the admin page.

    Args:
        limit: Maximum number of records.

    Returns:
        Sorted list of enriched audit events.
    """
    all_events = get_db().find_all(COLLECTION_EVENTS)
    rows = []
    for event in all_events:
        if event.get("entity_type") != "user_admin":
            continue

        details = event.get("details", {})
        if not isinstance(details, dict):
            details = {}

        timestamp = event.get("timestamp", "")
        rows.append(
            {
                "timestamp": timestamp,
                "display_time": _format_timestamp_for_display(timestamp),
                "action": event.get("action", "-"),
                "summary": event.get("summary", ""),
                "performed_by": event.get("performed_by", "system"),
                "target_username": details.get("target_username", ""),
                "changes": details.get("changes", {}),
            }
        )

    rows.sort(key=lambda row: row.get("timestamp", ""), reverse=True)
    return rows[: max(1, int(limit))]


def _get_role_policy() -> dict:
    """Load manager-defined role policy for clerk settings.

    Returns:
        Role policy dictionary with defaults and locked keys.
    """
    db = get_db()
    for setting in db.find_all(COLLECTION_APP_SETTINGS):
        if setting.get("key") == "role_policy":
            payload = setting.get("value", {})
            if isinstance(payload, dict):
                defaults = _sanitize_settings(payload.get("clerk_defaults", {}))
                locked = payload.get("clerk_locked_keys", [])
                if not isinstance(locked, list):
                    locked = []
                locked = [key for key in locked if key in _ALLOWED_SETTING_KEYS]
                return {
                    "clerk_defaults": {**UI_DEFAULT_SETTINGS, **defaults},
                    "clerk_locked_keys": locked,
                }

    return dict(_ROLE_POLICY_DEFAULT)


def _save_role_policy(policy: dict) -> dict:
    """Persist role policy for clerk settings defaults/locks.

    Args:
        policy: Policy payload.

    Returns:
        Persisted normalized policy.
    """
    db = get_db()
    normalized = {
        "clerk_defaults": {**UI_DEFAULT_SETTINGS, **_sanitize_settings(policy.get("clerk_defaults", {}))},
        "clerk_locked_keys": [
            key
            for key in policy.get("clerk_locked_keys", [])
            if key in _ALLOWED_SETTING_KEYS
        ],
    }

    existing = None
    for setting in db.find_all(COLLECTION_APP_SETTINGS):
        if setting.get("key") == "role_policy":
            existing = setting
            break

    payload = {
        "key": "role_policy",
        "value": normalized,
        "updated_at": _now_utc_iso(),
    }
    if existing:
        db.update(COLLECTION_APP_SETTINGS, existing.get("_id", ""), payload)
    else:
        db.insert(COLLECTION_APP_SETTINGS, payload)

    return normalized


def _get_user_profile_settings(username: str, profile_role: str) -> dict:
    """Read persisted UI profile settings from DB.

    Args:
        username: Owner username.
        profile_role: Target role profile (manager/clerk).

    Returns:
        Effective settings dictionary.
    """
    db = get_db()
    role_policy = _get_role_policy()
    role_name = profile_role if profile_role in ("manager", "clerk") else "clerk"

    settings_doc = None
    for row in db.find_all(COLLECTION_USER_SETTINGS):
        if row.get("owner_username") == username and row.get("profile_role") == role_name:
            settings_doc = row
            break

    persisted = _sanitize_settings(settings_doc.get("settings", {}) if settings_doc else {})
    merged = {**UI_DEFAULT_SETTINGS, **persisted}

    if role_name == "clerk":
        merged = {**role_policy.get("clerk_defaults", {}), **merged}

    if _current_role_name() == "clerk" and role_name == "clerk":
        for key in role_policy.get("clerk_locked_keys", []):
            merged[key] = role_policy.get("clerk_defaults", {}).get(key, UI_DEFAULT_SETTINGS.get(key))

    return merged


def _upsert_user_profile_settings(username: str, profile_role: str, settings: dict) -> dict:
    """Persist UI profile settings for one user and role profile.

    Args:
        username: Owner username.
        profile_role: Profile role to persist.
        settings: Settings payload.

    Returns:
        Persisted effective settings.
    """
    db = get_db()
    role_name = profile_role if profile_role in ("manager", "clerk") else "clerk"
    sanitized = _sanitize_settings(settings)

    if _current_role_name() == "clerk" and role_name == "clerk":
        role_policy = _get_role_policy()
        for key in role_policy.get("clerk_locked_keys", []):
            sanitized[key] = role_policy.get("clerk_defaults", {}).get(key, UI_DEFAULT_SETTINGS.get(key))

    existing = None
    for row in db.find_all(COLLECTION_USER_SETTINGS):
        if row.get("owner_username") == username and row.get("profile_role") == role_name:
            existing = row
            break

    payload = {
        "owner_username": username,
        "profile_role": role_name,
        "settings": sanitized,
        "updated_at": _now_utc_iso(),
    }
    if existing:
        db.update(COLLECTION_USER_SETTINGS, existing.get("_id", ""), payload)
    else:
        db.insert(COLLECTION_USER_SETTINGS, payload)

    return _get_user_profile_settings(username, role_name)


def _current_role_name() -> str:
    """Return current role from session with sane fallback.

    Returns:
        Active role name.
    """
    role = str(session.get("user_role", "")).strip().lower()
    if role in ("manager", "clerk"):
        return role
    return "clerk"


def _auth_enabled() -> bool:
    """Return whether authentication is active for this request context.

    Returns:
        True when login is required, otherwise False.
    """
    return bool(app.config.get("AUTH_REQUIRED", True))


def _current_username() -> str:
    """Return the active username from session.

    Returns:
        Username string, or "system" if nobody is logged in.
    """
    return str(session.get("user_name", "system"))


def _is_manager() -> bool:
    """Check whether the active user has manager permissions.

    Returns:
        True when current role equals "manager".
    """
    return str(session.get("user_role", "")) == "manager"


def _require_manager() -> Optional[Response]:
    """Guard manager-only routes.

    Returns:
        Redirect response when the current user is not allowed, else None.
    """
    if not _auth_enabled():
        return None

    if _is_manager():
        return None

    flash("Für diese Aktion sind Manager-Rechte erforderlich.", "danger")
    return redirect(url_for("page1_products"))


@app.before_request
def _enforce_login() -> Optional[Response]:
    """Redirect unauthenticated users to the login screen.

    Returns:
        Redirect response when access should be blocked, else None.
    """
    if not _auth_enabled():
        return None

    public_endpoints = {
        "login_page",
        "login_submit",
        "logo",
        "favicon",
        "static",
    }

    endpoint = request.endpoint or ""
    if endpoint in public_endpoints:
        return None

    if session.get("user_name"):
        g.current_user = session.get("display_name", session.get("user_name", ""))
        g.current_role = session.get("user_role", "")
        return None

    return redirect(url_for("login_page", next=request.path))


@app.context_processor
def _inject_user_context() -> dict:
    """Expose login/session state to all templates.

    Returns:
        Template context dictionary for authentication UI data.
    """
    return {
        "current_username": session.get("user_name", ""),
        "current_user": session.get("display_name", ""),
        "current_role": session.get("user_role", ""),
        "is_manager": _is_manager(),
        "auth_enabled": _auth_enabled(),
    }

# ---------------------------------------------------------------------------
# Database singleton and service factories
# ---------------------------------------------------------------------------

_db: Optional[MongoDBAdapter] = None

def get_db() -> MongoDBAdapter:
    """Return the shared MongoDBAdapter, creating and connecting it on first call.

    Returns:
        A connected MongoDBAdapter instance.
    """
    global _db
    if _db is None:
        _db = MongoDBAdapter()
        _db.connect()
    return _db

def get_product_service() -> ProductServicePort:
    """Create a ProductService bound to the shared database adapter.

    Returns:
        A ready-to-use ProductService instance.
    """
    return ProductService(get_db())

def get_warehouse_service() -> WarehouseServicePort:
    """Create a WarehouseService bound to the shared database adapter.

    Returns:
        A ready-to-use WarehouseService instance.
    """
    return WarehouseService(get_db())

def get_inventory_service() -> InventoryServicePort:
    """Create an InventoryService bound to the shared database adapter.

    Returns:
        A ready-to-use InventoryService instance.
    """
    return InventoryService(get_db())

# ---------------------------------------------------------------------------
# Static file routes
# ---------------------------------------------------------------------------

@app.route("/favicon.ico")
def favicon():
    """Serve the application favicon."""
    return send_from_directory(RESOURCES_DIR, "BIER_ICON_COMPRESSED.png", mimetype="image/png")

@app.route("/logo")
def logo():
    """Serve the B.I.E.R logo image."""
    return send_from_directory(RESOURCES_DIR, "BIER_LOGO_NOBG.png", mimetype="image/png")

# ---------------------------------------------------------------------------
# Authentication routes
# ---------------------------------------------------------------------------


@app.route("/login")
def login_page():
    """Render the login page.

    Returns:
        Login page response or redirect to dashboard when already authenticated.
    """
    if not _auth_enabled() or session.get("user_name"):
        return redirect(url_for("page1_products"))

    next_path = request.args.get("next", "").strip() or url_for("page1_products")
    return render_template("login.html", next_path=next_path, active_page=0)


@app.route("/login", methods=["POST"])
def login_submit():
    """Authenticate a user and create a session.

    Returns:
        Redirect to requested page on success, otherwise back to login page.
    """
    if not _auth_enabled():
        return redirect(url_for("page1_products"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    next_path = request.form.get("next", "").strip() or url_for("page1_products")

    _ensure_default_users_in_db()
    user = _find_user_by_username(username)
    if not user:
        flash("Ungültige Anmeldedaten.", "danger")
        return redirect(url_for("login_page", next=next_path))

    if not bool(user.get("active", True)):
        flash("Benutzer ist deaktiviert.", "danger")
        return redirect(url_for("login_page", next=next_path))

    password_hash = user.get("password_hash", "")
    if not check_password_hash(password_hash, password):
        flash("Ungültige Anmeldedaten.", "danger")
        return redirect(url_for("login_page", next=next_path))

    session["user_name"] = username
    session["display_name"] = user.get("display_name", username)
    session["user_role"] = user.get("role", "clerk")
    flash(f"Willkommen, {session['display_name']}.", "success")
    return redirect(next_path)


@app.route("/api/ui-settings/bootstrap")
def api_ui_settings_bootstrap():
    """Return persisted DB-backed UI settings bootstrap for current user."""
    username = str(session.get("user_name", "")).strip()
    role = _current_role_name()

    if _auth_enabled() and not username:
        return jsonify({"ok": False, "error": "not_authenticated"}), 401

    role_policy = _get_role_policy()
    profiles = {
        "manager": _get_user_profile_settings(username, "manager") if role == "manager" else None,
        "clerk": _get_user_profile_settings(username, "clerk"),
    }

    editable_roles = ["manager", "clerk"] if role == "manager" else [role]
    return jsonify(
        {
            "ok": True,
            "current_role": role,
            "active_profile_role": role,
            "editable_roles": editable_roles,
            "profiles": profiles,
            "role_policy": role_policy,
        }
    )


@app.route("/api/ui-settings/profile/<profile_role>", methods=["PUT", "DELETE"])
def api_ui_settings_profile(profile_role: str):
    """Update/reset persisted UI profile settings for current user."""
    username = str(session.get("user_name", "")).strip()
    role = _current_role_name()

    if _auth_enabled() and not username:
        return jsonify({"ok": False, "error": "not_authenticated"}), 401

    profile_role_clean = profile_role.strip().lower()
    if profile_role_clean not in ("manager", "clerk"):
        return jsonify({"ok": False, "error": "invalid_profile_role"}), 400

    if role != "manager" and profile_role_clean != role:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    if request.method == "DELETE":
        persisted = _upsert_user_profile_settings(username, profile_role_clean, UI_DEFAULT_SETTINGS)
        return jsonify({"ok": True, "settings": persisted})

    payload = request.get_json(silent=True) or {}
    settings = payload.get("settings", {})
    persisted = _upsert_user_profile_settings(username, profile_role_clean, settings)
    return jsonify({"ok": True, "settings": persisted})


@app.route("/api/ui-settings/role-policy", methods=["GET", "PUT"])
def api_ui_settings_role_policy():
    """Get or update role policy defaults and clerk locks (manager only for write)."""
    role = _current_role_name()

    if request.method == "GET":
        if _auth_enabled() and not session.get("user_name"):
            return jsonify({"ok": False, "error": "not_authenticated"}), 401
        return jsonify({"ok": True, "role_policy": _get_role_policy()})

    manager_guard = _require_manager()
    if manager_guard is not None:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    policy = {
        "clerk_defaults": _sanitize_settings(payload.get("clerk_defaults", {})),
        "clerk_locked_keys": payload.get("clerk_locked_keys", []),
    }
    saved = _save_role_policy(policy)

    # If manager changed policy, also enforce locked defaults for clerk profile owner.
    if role == "clerk":
        _upsert_user_profile_settings(_current_username(), "clerk", _get_user_profile_settings(_current_username(), "clerk"))

    return jsonify({"ok": True, "role_policy": saved})


@app.route("/logout", methods=["POST"])
def logout_submit():
    """Log out the current user and clear session state.

    Returns:
        Redirect to login page.
    """
    session.clear()
    flash("Erfolgreich abgemeldet.", "info")
    return redirect(url_for("login_page"))


# ---------------------------------------------------------------------------
# Dashboard / index
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Render the main dashboard page (product overview)."""
    if _auth_enabled() and not session.get("user_name"):
        return redirect(url_for("login_page"))
    return page1_products()

# ---------------------------------------------------------------------------
# Inventory routes
# ---------------------------------------------------------------------------

@app.route("/inventar")
def inventar_select():
    """Redirect to the first warehouse''s inventory, or show the statistics page when empty."""
    db = get_db()
    warehouses_list = db.find_all(COLLECTION_LAGER)

    if not warehouses_list:
        # No warehouses exist – show an empty state via the statistics page
        return page4_statistics()

    first_warehouse = warehouses_list[0]
    return redirect(url_for("inventar_detail", lager_id=first_warehouse["_id"]))

@app.route("/inventar/<lager_id>")
def inventar_detail(lager_id: str):
    """Show the detail view for a single warehouse inventory.

    Args:
        lager_id: Unique warehouse identifier from the URL.
    """
    db = get_db()
    lager = db.find_by_id(COLLECTION_LAGER, lager_id)

    if lager is None:
        return redirect(url_for("inventar_select"))

    return page4_statistics()

@app.route("/inventar/<lager_id>/hinzufuegen", methods=["POST"])
def inventar_add(lager_id: str):
    """Add a product to a warehouse inventory.

    Args:
        lager_id: Unique warehouse identifier from the URL.
    """
    svc = get_inventory_service()
    product_id = request.form.get("produkt_id", "")
    quantity_raw = request.form.get("menge", "1")

    try:
        quantity = int(quantity_raw)
        svc.add_product(
            warehouse_id=lager_id,
            product_id=product_id,
            quantity=quantity,
            performed_by=_current_username(),
        )
        flash("Produkt dem Lager hinzugefügt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("inventar_detail", lager_id=lager_id))

@app.route("/inventar/<lager_id>/<produkt_id>/aktualisieren", methods=["POST"])
def inventar_update(lager_id: str, produkt_id: str):
    """Update the quantity of a specific product in a warehouse.

    Args:
        lager_id: Unique warehouse identifier from the URL.
        produkt_id: Unique product identifier from the URL.
    """
    svc = get_inventory_service()
    quantity_raw = request.form.get("menge", "0")

    try:
        quantity = int(quantity_raw)
        svc.update_quantity(
            warehouse_id=lager_id,
            product_id=produkt_id,
            quantity=quantity,
            performed_by=_current_username(),
        )
        flash("Menge aktualisiert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("inventar_detail", lager_id=lager_id))

@app.route("/inventar/<lager_id>/<produkt_id>/entfernen", methods=["POST"])
def inventar_remove(lager_id: str, produkt_id: str):
    """Remove a product from a warehouse inventory.

    Args:
        lager_id: Unique warehouse identifier from the URL.
        produkt_id: Unique product identifier from the URL.
    """
    svc = get_inventory_service()
    try:
        svc.remove_product(
            warehouse_id=lager_id,
            product_id=produkt_id,
            performed_by=_current_username(),
        )
        flash("Produkt aus Lager entfernt.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("inventar_detail", lager_id=lager_id))


@app.route("/ui/produkt/<produkt_id>/zubuchen", methods=["POST"])
def page1_stock_in(produkt_id: str):
    """Book stock-in for a product in the selected warehouse.

    Args:
        produkt_id: Product identifier.
    """
    svc_inv = get_inventory_service()
    warehouse_id = request.form.get("lager_id", "").strip()
    quantity_raw = request.form.get("menge", "0").strip()

    try:
        quantity = int(quantity_raw)
        if quantity <= 0:
            raise ValueError("Menge muss größer als 0 sein.")

        svc_inv.add_product(
            warehouse_id=warehouse_id,
            product_id=produkt_id,
            quantity=quantity,
            performed_by=_current_username(),
        )
        flash("Bestand erfolgreich zugebucht.", "success")
    except (KeyError, ValueError) as exc:
        flash(f"Fehler beim Zubuchen: {exc}", "danger")

    return redirect(url_for("page1_products"))


@app.route("/ui/produkt/<produkt_id>/abbuchen", methods=["POST"])
def page1_stock_out(produkt_id: str):
    """Book stock-out for a product in the selected warehouse.

    Args:
        produkt_id: Product identifier.
    """
    svc_inv = get_inventory_service()
    warehouse_id = request.form.get("lager_id", "").strip()
    quantity_raw = request.form.get("menge", "0").strip()

    try:
        quantity = int(quantity_raw)
        if quantity <= 0:
            raise ValueError("Menge muss größer als 0 sein.")

        svc_inv.remove_stock(
            warehouse_id=warehouse_id,
            product_id=produkt_id,
            quantity=quantity,
            performed_by=_current_username(),
        )
        flash("Bestand erfolgreich abgebucht.", "success")
    except (KeyError, ValueError) as exc:
        flash(f"Fehler beim Abbuchen: {exc}", "danger")

    return redirect(url_for("page1_products"))

# ---------------------------------------------------------------------------
# Page 1 – Product overview
# ---------------------------------------------------------------------------

@app.route("/ui/produkte")
def page1_products():
    """Render Page 1: product management overview.

    Supports an optional ?lager_id= query parameter to filter products
    by warehouse. When no filter is active, the total quantity across
    all warehouses is shown for each product.
    """
    svc_p = get_product_service()
    svc_w = get_warehouse_service()
    db = get_db()

    warehouse_filter_id = request.args.get("lager_id", "").strip()
    all_products = svc_p.list_products()
    all_inventory = db.find_all(COLLECTION_INVENTAR)

    # Build a lookup: product_id → {warehouse_id → quantity}
    inventory_by_product: dict = {}
    for entry in all_inventory:
        product_id = entry.get("produkt_id", "")
        warehouse_id = entry.get("lager_id", "")

        if not product_id or not warehouse_id:
            continue

        if product_id not in inventory_by_product:
            inventory_by_product[product_id] = {}

        existing_qty = inventory_by_product[product_id].get(warehouse_id, 0)
        new_qty = existing_qty + entry.get("menge", 0)
        inventory_by_product[product_id][warehouse_id] = new_qty

    enriched_products = []
    low_stock_count = 0
    for product in all_products:
        product_id = product.get("_id")
        warehouse_map = inventory_by_product.get(product_id, {})
        product_copy = dict(product)

        if warehouse_filter_id:
            # Only include products that are stocked in the selected warehouse
            if warehouse_filter_id in warehouse_map:
                product_copy["lager_id"] = warehouse_filter_id
                product_copy["menge"] = warehouse_map.get(warehouse_filter_id, 0)
            else:
                continue
        else:
            # Show total quantity across all warehouses
            product_copy["lager_id"] = ""
            total_quantity = sum(warehouse_map.values()) if warehouse_map else 0
            product_copy["menge"] = total_quantity

        min_stock = int(product_copy.get("mindestbestand", 0) or 0)
        product_copy["mindestbestand"] = min_stock
        product_copy["is_low_stock"] = bool(min_stock > 0 and int(product_copy.get("menge", 0)) <= min_stock)
        if product_copy["is_low_stock"]:
            low_stock_count += 1

        enriched_products.append(product_copy)

    all_warehouses = svc_w.list_warehouses()

    # Find the active warehouse filter object (if any)
    active_filter = None
    for warehouse in all_warehouses:
        if warehouse["_id"] == warehouse_filter_id:
            active_filter = warehouse
            break

    return render_template(
        "page1_products.html",
        produkte=enriched_products,
        lager=all_warehouses,
        active_page=1,
        active_lager_filter=active_filter,
        low_stock_count=low_stock_count,
    )


@app.route("/ui/produkte/export-pdf", methods=["POST"])
def export_inventory_pdf():
    """Export the currently filtered product inventory as a PDF file."""
    svc_p = get_product_service()
    db = get_db()

    warehouse_filter_id = request.form.get("lager_id", "").strip()
    products = svc_p.list_products()
    inventory = db.find_all(COLLECTION_INVENTAR)
    warehouses = db.find_all(COLLECTION_LAGER)

    qty_by_pair = {}
    for entry in inventory:
        key = (entry.get("produkt_id", ""), entry.get("lager_id", ""))
        qty_by_pair[key] = qty_by_pair.get(key, 0) + int(entry.get("menge", 0))

    warehouse_name = "Alle Lager"
    if warehouse_filter_id:
        for warehouse in warehouses:
            if warehouse.get("_id") == warehouse_filter_id:
                warehouse_name = warehouse.get("lagername", "Alle Lager")
                break

    rows = []
    for product in products:
        product_id = product.get("_id", "")
        if warehouse_filter_id:
            quantity = qty_by_pair.get((product_id, warehouse_filter_id), 0)
            if quantity <= 0:
                continue
        else:
            quantity = 0
            for (entry_product_id, _warehouse_id), entry_qty in qty_by_pair.items():
                if entry_product_id == product_id:
                    quantity += entry_qty

        row = dict(product)
        row["menge"] = quantity
        rows.append(row)

    pdf_bytes = build_inventory_pdf(rows, warehouse_name)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=inventar_report.pdf"},
    )

# ---------------------------------------------------------------------------
# Page 2 – Product detail / create / edit
# ---------------------------------------------------------------------------

@app.route("/ui/produkt/neu")
def page2_product_edit():
    """Render Page 2 in create-mode (no existing product pre-loaded)."""
    warehouses = get_warehouse_service().list_warehouses()
    return render_template(
        "page2_product_edit.html",
        produkt=None,
        lager=warehouses,
        inventar_entries=[],
        produkt_menge_by_lager={},
        active_page=2,
    )

@app.route("/ui/produkt/<produkt_id>/bearbeiten")
def page2_product_edit_existing(produkt_id: str):
    """Render Page 2 in edit-mode for an existing product.

    Args:
        produkt_id: Unique product identifier from the URL.
    """
    svc_p = get_product_service()
    svc_w = get_warehouse_service()
    db = get_db()

    product = svc_p.get_product(produkt_id)
    if not product:
        flash("Produkt nicht gefunden.", "danger")
        return redirect(url_for("page1_products"))

    all_warehouses = svc_w.list_warehouses()
    warehouse_by_id = {}
    for warehouse in all_warehouses:
        warehouse_by_id[warehouse["_id"]] = warehouse

    # Collect inventory entries for this specific product
    inventory_entries = []
    all_inventory = db.find_all(COLLECTION_INVENTAR)
    for entry in all_inventory:
        if entry.get("produkt_id") != produkt_id:
            continue

        warehouse_id = entry.get("lager_id", "")
        warehouse_doc = warehouse_by_id.get(warehouse_id)

        if warehouse_doc:
            warehouse_name = warehouse_doc.get("lagername", warehouse_id)
        else:
            warehouse_name = warehouse_id

        inventory_entries.append({
            "lager_id": warehouse_id,
            "lagername": warehouse_name,
            "menge": entry.get("menge", 0),
        })

    # Build a quick lookup: warehouse_id → quantity
    stock_by_warehouse = {}
    for entry in inventory_entries:
        if entry.get("lager_id"):
            stock_by_warehouse[entry["lager_id"]] = int(entry.get("menge", 0))

    # Collect any non-standard product fields for display
    standard_fields = {
        "_id",
        "name",
        "beschreibung",
        "gewicht",
        "preis",
        "waehrung",
        "lieferant",
        "sku",
        "kategorie",
        "mindestbestand",
        "bestellmenge",
    }
    extra_attrs = {}
    for key, value in product.items():
        if key not in standard_fields:
            extra_attrs[key] = value
    product["extra_attrs"] = extra_attrs

    return render_template(
        "page2_product_edit.html",
        produkt=product,
        lager=all_warehouses,
        inventar_entries=inventory_entries,
        produkt_menge_by_lager=stock_by_warehouse,
        active_page=2,
    )

@app.route("/ui/produkt/neu", methods=["POST"])
def page2_create_product():
    """Handle product creation from the Page 2 create form."""
    svc_p = get_product_service()
    svc_inv = get_inventory_service()

    name = request.form.get("name", "").strip()
    price_raw = request.form.get("preis", "").strip()
    weight_raw = request.form.get("gewicht", "").strip()

    if not name or not price_raw or not weight_raw:
        flash("Bitte alle Pflichtfelder (Name, Preis und Gewicht) ausfüllen.", "danger")
        return redirect(url_for("page2_product_edit"))

    try:
        product_doc = svc_p.create_product(
            name=name,
            description=request.form.get("beschreibung", ""),
            weight=float(weight_raw),
            price=float(price_raw),
            performed_by=_current_username(),
        )
        product_id = product_doc["_id"]

        # Collect standard optional fields
        extra_data = {}
        for field in ("preis", "waehrung", "lieferant", "sku", "kategorie"):
            field_value = request.form.get(field, "").strip()
            if field_value:
                extra_data[field] = field_value

        min_stock_raw = request.form.get("mindestbestand", "").strip()
        reorder_qty_raw = request.form.get("bestellmenge", "").strip()
        if min_stock_raw:
            extra_data["mindestbestand"] = int(min_stock_raw)
        if reorder_qty_raw:
            extra_data["bestellmenge"] = int(reorder_qty_raw)

        # Collect any custom key-value attributes from the form
        custom_keys = request.form.getlist("extra_key[]")
        custom_vals = request.form.getlist("extra_val[]")
        for key, value in zip(custom_keys, custom_vals):
            key = key.strip()
            if key:
                extra_data[key] = value.strip()

        if extra_data:
            svc_p.update_product(product_id, extra_data, performed_by=_current_username())

        # Collect warehouse/quantity pairs (supports multi-warehouse form)
        stock_entries = _parse_stock_entries_from_form()
        for warehouse_id, quantity in stock_entries:
            try:
                svc_inv.add_product(
                    warehouse_id=warehouse_id,
                    product_id=product_id,
                    quantity=quantity,
                    performed_by=_current_username(),
                )
            except (KeyError, ValueError):
                pass  # Skip invalid entries silently

        flash("Produkt erfolgreich angelegt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page1_products"))

@app.route("/ui/produkt/<produkt_id>/speichern", methods=["POST"])
def page2_save_product(produkt_id: str):
    """Handle product update from the Page 2 edit form.

    Args:
        produkt_id: Unique product identifier from the URL.
    """
    svc_p = get_product_service()
    svc_inv = get_inventory_service()
    db = get_db()

    name = request.form.get("name", "").strip()
    price_raw = request.form.get("preis", "").strip()
    weight_raw = request.form.get("gewicht", "").strip()

    if not name or not price_raw or not weight_raw:
        flash("Bitte alle Pflichtfelder (Name, Preis und Gewicht) ausfüllen.", "danger")
        return redirect(url_for("page2_product_edit_existing", produkt_id=produkt_id))

    try:
        # Build the core update payload
        update_data = {
            "name": name,
            "beschreibung": request.form.get("beschreibung", "").strip(),
            "gewicht": float(weight_raw or 0),
        }

        # Include standard optional fields
        for field in ("preis", "waehrung", "lieferant"):
            update_data[field] = request.form.get(field, "").strip()

        update_data["sku"] = request.form.get("sku", "").strip()
        update_data["kategorie"] = request.form.get("kategorie", "").strip()
        min_stock_raw = request.form.get("mindestbestand", "").strip()
        reorder_qty_raw = request.form.get("bestellmenge", "").strip()
        update_data["mindestbestand"] = int(min_stock_raw or 0)
        update_data["bestellmenge"] = int(reorder_qty_raw or 0)

        # Include custom attributes
        custom_keys = request.form.getlist("extra_key[]")
        custom_vals = request.form.getlist("extra_val[]")
        for key, value in zip(custom_keys, custom_vals):
            key = key.strip()
            if key:
                update_data[key] = value.strip()

        svc_p.update_product(produkt_id, update_data, performed_by=_current_username())

        # Sync warehouse stock entries for this product
        desired_stock = _parse_stock_entries_from_form()

        # Aggregate desired quantities per warehouse (handles duplicate warehouse IDs)
        desired_by_warehouse = {}
        for warehouse_id, quantity in desired_stock:
            previous = desired_by_warehouse.get(warehouse_id, 0)
            desired_by_warehouse[warehouse_id] = previous + quantity

        # Find existing inventory entries for this product
        existing_entries = []
        for entry in db.find_all(COLLECTION_INVENTAR):
            if entry.get("produkt_id") == produkt_id:
                existing_entries.append(entry)

        existing_by_warehouse = {}
        for entry in existing_entries:
            warehouse_id = entry.get("lager_id", "")
            if warehouse_id:
                existing_by_warehouse[warehouse_id] = entry

        # Apply desired quantities: update or create entries
        for warehouse_id, quantity in desired_by_warehouse.items():
            try:
                if warehouse_id in existing_by_warehouse:
                    svc_inv.update_quantity(
                        warehouse_id=warehouse_id,
                        product_id=produkt_id,
                        quantity=quantity,
                        performed_by=_current_username(),
                    )
                else:
                    svc_inv.add_product(
                        warehouse_id=warehouse_id,
                        product_id=produkt_id,
                        quantity=quantity,
                        performed_by=_current_username(),
                    )
            except (KeyError, ValueError) as exc:
                flash(f"Fehler beim Aktualisieren des Bestands für Lager {warehouse_id}: {exc}", "danger")

        # Remove warehouse assignments that are no longer desired
        for warehouse_id in list(existing_by_warehouse.keys()):
            if warehouse_id not in desired_by_warehouse:
                try:
                    svc_inv.remove_product(
                        warehouse_id=warehouse_id,
                        product_id=produkt_id,
                        performed_by=_current_username(),
                    )
                except KeyError:
                    pass

        flash("Produkt gespeichert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page1_products"))

@app.route("/ui/produkt/<produkt_id>/verschieben", methods=["POST"])
def page2_move_product(produkt_id: str):
    """Move a quantity of a product from its current warehouse to another.

    Args:
        produkt_id: Unique product identifier from the URL.
    """
    svc_inv = get_inventory_service()
    db = get_db()

    target_warehouse_id = request.form.get("target_lager_id", "").strip()
    source_warehouse_override = request.form.get("source_lager_id", "").strip()
    quantity_raw = request.form.get("menge", "0").strip()

    try:
        quantity = int(quantity_raw or 0)
    except ValueError:
        flash("Menge muss eine ganze Zahl sein.", "danger")
        return redirect(url_for("page1_products"))

    # Determine source warehouse: prefer the explicit form value, fall back to the first entry
    source_entry = None
    if source_warehouse_override:
        source_entry = db.find_inventory_entry(source_warehouse_override, produkt_id)

    if not source_entry:
        # Look for any inventory entry for this product
        all_inventory = db.find_all(COLLECTION_INVENTAR)
        for entry in all_inventory:
            if entry.get("produkt_id") == produkt_id:
                source_entry = entry
                break

    if not source_entry:
        flash("Für dieses Produkt ist kein Lagerbestand vorhanden.", "danger")
        return redirect(url_for("page1_products"))

    source_warehouse_id = source_entry.get("lager_id", "")

    if not target_warehouse_id or target_warehouse_id == source_warehouse_id:
        flash("Bitte ein anderes Ziellager auswählen.", "danger")
        return redirect(url_for("page1_products"))

    try:
        svc_inv.move_product(
            source_warehouse_id,
            target_warehouse_id,
            produkt_id,
            quantity,
            performed_by=_current_username(),
        )
        flash("Produktbestand wurde verschoben.", "success")
    except (KeyError, ValueError) as exc:
        flash(f"Fehler beim Verschieben: {exc}", "danger")

    return redirect(url_for("page1_products"))

@app.route("/ui/produkt/<produkt_id>/loeschen", methods=["POST"])
def page2_delete_product(produkt_id: str):
    """Delete a product and remove all associated inventory entries.

    Args:
        produkt_id: Unique product identifier from the URL.
    """
    svc_p = get_product_service()
    svc_inv = get_inventory_service()
    db = get_db()

    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    try:
        # Remove all inventory entries for this product first
        all_inventory = db.find_all(COLLECTION_INVENTAR)
        for entry in all_inventory:
            if entry.get("produkt_id") != produkt_id:
                continue
            entry_warehouse_id = entry.get("lager_id", "")
            try:
                svc_inv.remove_product(
                    warehouse_id=entry_warehouse_id,
                    product_id=produkt_id,
                    performed_by=_current_username(),
                )
            except KeyError:
                pass  # Entry may have been removed already

        # Delete the product itself
        svc_p.delete_product(produkt_id, performed_by=_current_username())
        flash("Produkt und zugehöriger Bestand gelöscht.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page1_products"))

# ---------------------------------------------------------------------------
# Page 3 – Warehouse list
# ---------------------------------------------------------------------------

@app.route("/ui/lager")
def page3_warehouse_list():
    """Render Page 3: warehouse list with aggregated stock statistics."""
    raw_warehouses = get_warehouse_service().list_warehouses()
    all_inventory = get_db().find_all(COLLECTION_INVENTAR)
    enriched = enrich_warehouses(raw_warehouses, all_inventory)
    return render_template("page3_warehouse_list.html", lager=enriched, active_page=3)

@app.route("/ui/lager/neu", methods=["POST"])
def page3_create_warehouse():
    """Handle warehouse creation from Page 3."""
    svc = get_warehouse_service()
    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    warehouse_name = request.form.get("lagername", "")
    address = request.form.get("adresse", "")
    max_slots_raw = request.form.get("max_plaetze", "1")

    try:
        max_slots = int(max_slots_raw)
        svc.create_warehouse(
            warehouse_name=warehouse_name,
            address=address,
            max_slots=max_slots,
            performed_by=_current_username(),
        )
        flash("Lager erfolgreich angelegt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page3_warehouse_list"))

@app.route("/ui/lager/<lager_id>/bearbeiten", methods=["POST"])
def page3_update_warehouse(lager_id: str):
    """Handle warehouse update from Page 3.

    Args:
        lager_id: Unique warehouse identifier from the URL.
    """
    svc = get_warehouse_service()
    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    warehouse_name = request.form.get("lagername", "")
    address = request.form.get("adresse", "")
    max_slots_raw = request.form.get("max_plaetze", "1")

    try:
        max_slots = int(max_slots_raw)
        update_data = {
            "lagername": warehouse_name,
            "adresse": address,
            "max_plaetze": max_slots,
        }
        svc.update_warehouse(lager_id, update_data, performed_by=_current_username())
        flash("Lager aktualisiert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page3_warehouse_list"))

@app.route("/ui/lager/<lager_id>/loeschen", methods=["POST"])
def page3_delete_warehouse(lager_id: str):
    """Handle warehouse deletion from Page 3.

    All inventory entries belonging to this warehouse are removed first.

    Args:
        lager_id: Unique warehouse identifier from the URL.
    """
    svc_w = get_warehouse_service()
    svc_inv = get_inventory_service()
    db = get_db()

    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    try:
        # Remove all inventory entries for this warehouse before deleting the warehouse
        all_inventory = db.find_all(COLLECTION_INVENTAR)
        for entry in all_inventory:
            if entry.get("lager_id") != lager_id:
                continue
            entry_product_id = entry.get("produkt_id", "")
            try:
                svc_inv.remove_product(
                    warehouse_id=lager_id,
                    product_id=entry_product_id,
                    performed_by=_current_username(),
                )
            except KeyError:
                pass  # Entry may have been removed already

        svc_w.delete_warehouse(lager_id, performed_by=_current_username())
        flash("Lager und alle enthaltenen Bestände gelöscht.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page3_warehouse_list"))

# ---------------------------------------------------------------------------
# Page 4 – Statistics dashboard
# ---------------------------------------------------------------------------

@app.route("/ui/statistik")
def page4_statistics():
    """Render Page 4: statistics dashboard with charts and KPI cards."""
    db = get_db()
    products = db.find_all(COLLECTION_PRODUKTE)
    warehouses = db.find_all(COLLECTION_LAGER)
    inventory = db.find_all(COLLECTION_INVENTAR)

    # Use helper functions from helpers.py to perform all the complex computations
    (
        quantity_per_warehouse,
        products_per_warehouse,
        warehouse_labels,
        warehouse_quantities,
    ) = compute_warehouse_aggregates(warehouses, inventory)

    warehouse_stats = compute_warehouse_stats(
        warehouses, quantity_per_warehouse, products_per_warehouse
    )
    utilisation_labels, utilisation_pct = compute_utilisation(warehouse_stats)
    category_labels, category_counts = compute_category_counts(products)
    top10_labels, top10_values = compute_top10_products(products, inventory)
    warehouse_top_labels, warehouse_top_values = compute_warehouse_top_products(
        warehouses, products, inventory
    )
    warehouse_values, total_value = compute_warehouse_values(warehouses, products, inventory)

    total_quantity = sum(quantity_per_warehouse.values())
    low_stock_count = 0
    quantity_by_product = {}
    for entry in inventory:
        product_id = entry.get("produkt_id", "")
        quantity_by_product[product_id] = quantity_by_product.get(product_id, 0) + int(entry.get("menge", 0))

    for product in products:
        min_stock = int(product.get("mindestbestand", 0) or 0)
        current_qty = int(quantity_by_product.get(product.get("_id", ""), 0))
        if min_stock > 0 and current_qty <= min_stock:
            low_stock_count += 1

    return render_template(
        "page4_statistics.html",
        active_page=4,
        num_produkte=len(products),
        num_lager=len(warehouses),
        total_menge=total_quantity,
        total_value=total_value,
        low_stock_count=low_stock_count,
        num_inventar=len(inventory),
        lager_stats=warehouse_stats,
        lager_labels=warehouse_labels,
        lager_werte=warehouse_values,
        lager_mengen=warehouse_quantities,
        kat_labels=category_labels,
        kat_counts=category_counts,
        top10_labels=top10_labels,
        top10_values=top10_values,
        lager_top_labels=warehouse_top_labels,
        lager_top_values=warehouse_top_values,
        aus_labels=utilisation_labels,
        aus_pct=utilisation_pct,
    )


@app.route("/ui/statistik/export-pdf", methods=["POST"])
def export_statistics_pdf():
    """Export the current statistics dashboard data as a PDF file."""
    db = get_db()
    products = db.find_all(COLLECTION_PRODUKTE)
    warehouses = db.find_all(COLLECTION_LAGER)
    inventory = db.find_all(COLLECTION_INVENTAR)

    (
        quantity_per_warehouse,
        products_per_warehouse,
        _warehouse_labels,
        _warehouse_quantities,
    ) = compute_warehouse_aggregates(warehouses, inventory)
    warehouse_stats = compute_warehouse_stats(
        warehouses, quantity_per_warehouse, products_per_warehouse
    )
    _warehouse_values, total_value = compute_warehouse_values(warehouses, products, inventory)

    total_quantity = sum(quantity_per_warehouse.values())
    quantity_by_product = {}
    for entry in inventory:
        product_id = entry.get("produkt_id", "")
        quantity_by_product[product_id] = quantity_by_product.get(product_id, 0) + int(entry.get("menge", 0))

    low_stock_count = 0
    for product in products:
        min_stock = int(product.get("mindestbestand", 0) or 0)
        current_qty = int(quantity_by_product.get(product.get("_id", ""), 0))
        if min_stock > 0 and current_qty <= min_stock:
            low_stock_count += 1

    data = {
        "num_produkte": len(products),
        "num_lager": len(warehouses),
        "total_menge": total_quantity,
        "num_inventar": len(inventory),
        "total_value": total_value,
        "low_stock_count": low_stock_count,
        "lager_stats": warehouse_stats,
    }

    pdf_bytes = build_statistics_pdf(data)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=statistik_report.pdf"},
    )


# ---------------------------------------------------------------------------
# Page 6 – Procurement / reorder suggestions
# ---------------------------------------------------------------------------


def _now_utc_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format with trailing Z.

    Returns:
        Current UTC timestamp string.
    """
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _parse_iso_utc(value: str) -> Optional[datetime]:
    """Parse an ISO timestamp string into a datetime object.

    Args:
        value: ISO timestamp string.

    Returns:
        Parsed datetime or None when parsing fails.
    """
    clean = (value or "").strip().rstrip("Z")
    if not clean:
        return None
    try:
        return datetime.fromisoformat(clean)
    except ValueError:
        return None


def _to_float(value: str, default: float = 0.0) -> float:
    """Safely parse a float from string input.

    Args:
        value: Raw input value.
        default: Fallback value on parse errors.

    Returns:
        Parsed float or default.
    """
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _build_lookup(items: list) -> dict:
    """Build an id-based lookup map for document lists.

    Args:
        items: List of documents with optional _id fields.

    Returns:
        Dictionary mapping _id to document.
    """
    lookup = {}
    for item in items:
        doc_id = item.get("_id", "")
        if doc_id:
            lookup[doc_id] = item
    return lookup


def _enrich_orders(orders: list, suppliers: list, products: list, warehouses: list, departments: list) -> list:
    """Enrich order rows with display labels.

    Args:
        orders: Raw order documents.
        suppliers: Supplier documents.
        products: Product documents.
        warehouses: Warehouse documents.
        departments: Department documents.

    Returns:
        Enriched order list sorted by creation timestamp descending.
    """
    supplier_by_id = _build_lookup(suppliers)
    product_by_id = _build_lookup(products)
    warehouse_by_id = _build_lookup(warehouses)
    department_by_id = _build_lookup(departments)

    rows = []
    for order in orders:
        supplier = supplier_by_id.get(order.get("lieferant_id", ""), {})
        product = product_by_id.get(order.get("produkt_id", ""), {})
        warehouse = warehouse_by_id.get(order.get("lager_id", ""), {})
        department = department_by_id.get(order.get("abteilung_id", ""), {})

        ordered_qty = int(order.get("bestellmenge", 0) or 0)
        received_qty = int(order.get("geliefert", 0) or 0)
        backorder_qty = max(ordered_qty - received_qty, 0)
        unit_price = _to_float(order.get("einzelpreis", 0.0), 0.0)

        row = dict(order)
        row["lieferant_name"] = supplier.get("name", "-")
        row["produkt_name"] = product.get("name", "-")
        row["lager_name"] = warehouse.get("lagername", "-")
        row["abteilung_name"] = department.get("name", "-")
        row["kostenstelle"] = department.get("kostenstelle", "-")
        row["bestellmenge"] = ordered_qty
        row["geliefert"] = received_qty
        row["rueckstand"] = backorder_qty
        row["einzelpreis"] = unit_price
        row["gesamtpreis"] = ordered_qty * unit_price

        supplier_rating = _to_float(supplier.get("bewertung", 0.0), 0.0)
        supplier_sla_days = int(supplier.get("sla_tage", 0) or 0)
        row["lieferant_bewertung"] = supplier_rating
        row["sla_tage"] = supplier_sla_days

        created_at = _parse_iso_utc(order.get("erstellt_am", ""))
        expected_delivery = None
        sla_breach = False
        if created_at and supplier_sla_days > 0:
            expected_dt = created_at + timedelta(days=supplier_sla_days)
            expected_delivery = expected_dt.strftime("%d.%m.%Y")
            if order.get("status", "") not in ("abgeschlossen", "storniert", "abgelehnt"):
                sla_breach = datetime.utcnow() > expected_dt

        row["expected_delivery"] = expected_delivery or "-"
        row["sla_breach"] = sla_breach
        rows.append(row)

    rows.sort(key=lambda item: item.get("erstellt_am", ""), reverse=True)
    return rows


def _build_budget_view(departments: list) -> list:
    """Build budget overview rows for departments.

    Args:
        departments: Department documents.

    Returns:
        Department rows with budget usage values.
    """
    rows = []
    for department in departments:
        budget_limit = _to_float(department.get("budget_limit", 0.0), 0.0)
        budget_used = _to_float(department.get("budget_used", 0.0), 0.0)
        budget_remaining = budget_limit - budget_used
        usage_pct = 0.0
        if budget_limit > 0:
            usage_pct = max(min((budget_used / budget_limit) * 100, 999.0), 0.0)

        row = dict(department)
        row["budget_limit"] = budget_limit
        row["budget_used"] = budget_used
        row["budget_remaining"] = budget_remaining
        row["budget_pct"] = usage_pct
        rows.append(row)

    rows.sort(key=lambda item: item.get("name", ""))
    return rows


def _build_reorder_recommendations(
    products: list,
    warehouses: list,
    inventory: list,
    warehouse_filter_id: str = "",
) -> list:
    """Build reorder suggestions from min-stock and current inventory.

    Args:
        products: All product documents.
        warehouses: All warehouse documents.
        inventory: All inventory documents.
        warehouse_filter_id: Optional warehouse filter.

    Returns:
        A list of suggestion rows sorted by deficit descending.
    """
    quantity_by_pair = {}
    for entry in inventory:
        product_id = entry.get("produkt_id", "")
        warehouse_id = entry.get("lager_id", "")
        key = (product_id, warehouse_id)
        quantity_by_pair[key] = quantity_by_pair.get(key, 0) + int(entry.get("menge", 0))

    rows = []
    for product in products:
        product_id = product.get("_id", "")
        min_stock = int(product.get("mindestbestand", 0) or 0)
        reorder_qty = int(product.get("bestellmenge", 0) or 0)

        if min_stock <= 0:
            continue

        target_warehouses = warehouses
        if warehouse_filter_id:
            target_warehouses = [w for w in warehouses if w.get("_id") == warehouse_filter_id]

        for warehouse in target_warehouses:
            warehouse_id = warehouse.get("_id", "")
            current_qty = int(quantity_by_pair.get((product_id, warehouse_id), 0))
            if current_qty > min_stock:
                continue

            deficit = min_stock - current_qty
            suggested_qty = reorder_qty if reorder_qty > 0 else max(deficit, 1)

            rows.append({
                "produkt_id": product_id,
                "produkt_name": product.get("name", "-"),
                "sku": product.get("sku", ""),
                "kategorie": product.get("kategorie", ""),
                "lieferant": product.get("lieferant", ""),
                "lager_id": warehouse_id,
                "lagername": warehouse.get("lagername", "-"),
                "bestand": current_qty,
                "mindestbestand": min_stock,
                "defizit": deficit,
                "vorschlag": suggested_qty,
            })

    rows.sort(key=lambda r: (r.get("defizit", 0), r.get("produkt_name", "")), reverse=True)
    return rows


@app.route("/ui/bestellungen")
def page6_procurement():
    """Render reorder suggestions, orders, suppliers, and budget views."""
    db = get_db()
    products = db.find_all(COLLECTION_PRODUKTE)
    warehouses = db.find_all(COLLECTION_LAGER)
    inventory = db.find_all(COLLECTION_INVENTAR)
    suppliers = db.find_all(COLLECTION_LIEFERANTEN)
    departments = db.find_all(COLLECTION_ABTEILUNGEN)
    orders = db.find_all(COLLECTION_BESTELLUNGEN)

    warehouse_filter_id = request.args.get("lager_id", "").strip()
    suggestions = _build_reorder_recommendations(
        products,
        warehouses,
        inventory,
        warehouse_filter_id=warehouse_filter_id,
    )

    active_filter = None
    for warehouse in warehouses:
        if warehouse.get("_id") == warehouse_filter_id:
            active_filter = warehouse
            break

    total_deficit = 0
    total_suggested = 0
    for row in suggestions:
        total_deficit += int(row.get("defizit", 0))
        total_suggested += int(row.get("vorschlag", 0))

    budget_rows = _build_budget_view(departments)
    enriched_orders = _enrich_orders(orders, suppliers, products, warehouses, departments)

    product_with_supplier = []
    for product in products:
        if product.get("lieferant", ""):
            product_with_supplier.append(product)

    supplier_by_name = {s.get("name", ""): s for s in suppliers if s.get("name", "")}
    for product in product_with_supplier:
        supplier_name = product.get("lieferant", "")
        supplier = supplier_by_name.get(supplier_name)
        if supplier:
            product["lieferant_id"] = supplier.get("_id", "")
        else:
            product["lieferant_id"] = ""

    total_open_backorder = 0
    for order in enriched_orders:
        if order.get("status", "") in ("bestellt", "teilgeliefert"):
            total_open_backorder += int(order.get("rueckstand", 0))

    return render_template(
        "page6_procurement.html",
        active_page=6,
        lager=warehouses,
        active_lager_filter=active_filter,
        suggestions=suggestions,
        total_deficit=total_deficit,
        total_suggested=total_suggested,
        suppliers=suppliers,
        departments=budget_rows,
        products=products,
        products_for_orders=product_with_supplier,
        orders=enriched_orders,
        total_open_backorder=total_open_backorder,
    )


@app.route("/ui/bestellungen/<produkt_id>/ausfuehren", methods=["POST"])
def page6_execute_reorder(produkt_id: str):
    """Execute a reorder suggestion by booking stock in.

    Args:
        produkt_id: Product identifier.
    """
    svc_inv = get_inventory_service()
    warehouse_id = request.form.get("lager_id", "").strip()
    quantity_raw = request.form.get("menge", "0").strip()

    try:
        quantity = int(quantity_raw)
        if quantity <= 0:
            raise ValueError("Menge muss größer als 0 sein.")

        svc_inv.add_product(
            warehouse_id=warehouse_id,
            product_id=produkt_id,
            quantity=quantity,
            performed_by=_current_username(),
        )
        flash("Bestellvorschlag erfolgreich ausgeführt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler beim Ausführen des Bestellvorschlags: {exc}", "danger")

    return redirect(url_for("page6_procurement", lager_id=warehouse_id))


@app.route("/ui/lieferanten/neu", methods=["POST"])
def page6_create_supplier():
    """Create a supplier master record."""
    db = get_db()
    name = request.form.get("name", "").strip()
    contact_name = request.form.get("ansprechpartner", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("telefon", "").strip()
    payment_terms = request.form.get("zahlungsziel", "").strip()
    rating_raw = request.form.get("bewertung", "0").strip()
    min_order_raw = request.form.get("mindestbestellwert", "0").strip()
    sla_raw = request.form.get("sla_tage", "0").strip()

    if not name:
        flash("Lieferant konnte nicht angelegt werden: Name fehlt.", "danger")
        return redirect(url_for("page6_procurement"))

    rating = _to_float(rating_raw, 0.0)
    min_order = _to_float(min_order_raw, 0.0)
    try:
        sla_days = int(sla_raw)
    except ValueError:
        sla_days = 0

    if rating < 0 or rating > 5:
        flash("Bewertung muss zwischen 0 und 5 liegen.", "danger")
        return redirect(url_for("page6_procurement"))

    if min_order < 0:
        flash("Mindestbestellwert darf nicht negativ sein.", "danger")
        return redirect(url_for("page6_procurement"))

    if sla_days < 0:
        flash("Lieferzeit-SLA darf nicht negativ sein.", "danger")
        return redirect(url_for("page6_procurement"))

    supplier_doc = {
        "name": name,
        "ansprechpartner": contact_name,
        "email": email,
        "telefon": phone,
        "zahlungsziel": payment_terms,
        "bewertung": rating,
        "mindestbestellwert": min_order,
        "sla_tage": sla_days,
        "angelegt_am": _now_utc_iso(),
    }

    db.insert(COLLECTION_LIEFERANTEN, supplier_doc)
    flash("Lieferant erfolgreich angelegt.", "success")
    return redirect(url_for("page6_procurement"))


@app.route("/ui/abteilungen/neu", methods=["POST"])
def page6_create_department():
    """Create a department with cost center and budget settings."""
    db = get_db()
    name = request.form.get("name", "").strip()
    cost_center = request.form.get("kostenstelle", "").strip()
    budget_limit_raw = request.form.get("budget_limit", "0").strip()

    if not name:
        flash("Abteilung konnte nicht angelegt werden: Name fehlt.", "danger")
        return redirect(url_for("page6_procurement"))

    budget_limit = _to_float(budget_limit_raw, 0.0)
    if budget_limit < 0:
        flash("Budgetlimit darf nicht negativ sein.", "danger")
        return redirect(url_for("page6_procurement"))

    department_doc = {
        "name": name,
        "kostenstelle": cost_center,
        "budget_limit": budget_limit,
        "budget_used": 0.0,
        "angelegt_am": _now_utc_iso(),
    }

    db.insert(COLLECTION_ABTEILUNGEN, department_doc)
    flash("Abteilung erfolgreich angelegt.", "success")
    return redirect(url_for("page6_procurement"))


@app.route("/ui/bestellungen/neu", methods=["POST"])
def page6_create_order():
    """Create a real purchase order with status and budget allocation."""
    db = get_db()

    product_id = request.form.get("produkt_id", "").strip()
    supplier_id = request.form.get("lieferant_id", "").strip()
    warehouse_id = request.form.get("lager_id", "").strip()
    department_id = request.form.get("abteilung_id", "").strip()

    quantity_raw = request.form.get("bestellmenge", "0").strip()
    unit_price_raw = request.form.get("einzelpreis", "0").strip()

    try:
        quantity = int(quantity_raw)
    except ValueError:
        quantity = 0

    unit_price = _to_float(unit_price_raw, 0.0)
    order_total = quantity * unit_price

    if not product_id or not supplier_id or not warehouse_id or not department_id:
        flash("Bestellung unvollständig: Produkt, Lieferant, Lager und Abteilung sind Pflicht.", "danger")
        return redirect(url_for("page6_procurement"))

    if quantity <= 0:
        flash("Bestellmenge muss größer als 0 sein.", "danger")
        return redirect(url_for("page6_procurement"))

    if unit_price < 0:
        flash("Einzelpreis darf nicht negativ sein.", "danger")
        return redirect(url_for("page6_procurement"))

    supplier = db.find_by_id(COLLECTION_LIEFERANTEN, supplier_id)
    if not supplier:
        flash("Lieferant nicht gefunden.", "danger")
        return redirect(url_for("page6_procurement"))

    min_order_value = _to_float(supplier.get("mindestbestellwert", 0.0), 0.0)
    if min_order_value > 0 and order_total < min_order_value:
        flash(
            f"Mindestbestellwert des Lieferanten ({min_order_value:.2f} EUR) nicht erreicht.",
            "danger",
        )
        return redirect(url_for("page6_procurement"))

    department = db.find_by_id(COLLECTION_ABTEILUNGEN, department_id)
    if not department:
        flash("Abteilung nicht gefunden.", "danger")
        return redirect(url_for("page6_procurement"))

    budget_limit = _to_float(department.get("budget_limit", 0.0), 0.0)
    budget_used = _to_float(department.get("budget_used", 0.0), 0.0)
    if budget_limit > 0 and _is_manager() and (budget_used + order_total) > budget_limit:
        flash("Budget überschritten: Bestellung kann nicht freigegeben werden.", "danger")
        return redirect(url_for("page6_procurement"))

    initial_status = "bestellt" if _is_manager() else "warte_freigabe"
    budget_booked = _is_manager()

    order_doc = {
        "produkt_id": product_id,
        "lieferant_id": supplier_id,
        "lager_id": warehouse_id,
        "abteilung_id": department_id,
        "bestellmenge": quantity,
        "geliefert": 0,
        "einzelpreis": unit_price,
        "status": initial_status,
        "budget_verbucht": budget_booked,
        "erstellt_am": _now_utc_iso(),
        "erstellt_von": _current_username(),
    }

    db.insert(COLLECTION_BESTELLUNGEN, order_doc)
    if budget_booked:
        db.update(COLLECTION_ABTEILUNGEN, department_id, {"budget_used": budget_used + order_total})
        flash("Bestellung erfolgreich angelegt und freigegeben.", "success")
    else:
        flash("Bestellung erstellt und zur Freigabe vorgelegt.", "info")
    return redirect(url_for("page6_procurement"))


@app.route("/ui/bestellungen/<bestellung_id>/freigeben", methods=["POST"])
def page6_approve_order(bestellung_id: str):
    """Approve an order and allocate budget.

    Args:
        bestellung_id: Order identifier.
    """
    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    db = get_db()
    order = db.find_by_id(COLLECTION_BESTELLUNGEN, bestellung_id)
    if not order:
        flash("Bestellung nicht gefunden.", "danger")
        return redirect(url_for("page6_procurement"))

    if order.get("status", "") != "warte_freigabe":
        flash("Bestellung ist nicht im Freigabestatus.", "danger")
        return redirect(url_for("page6_procurement"))

    department_id = order.get("abteilung_id", "")
    department = db.find_by_id(COLLECTION_ABTEILUNGEN, department_id)
    if not department:
        flash("Abteilung nicht gefunden.", "danger")
        return redirect(url_for("page6_procurement"))

    order_total = int(order.get("bestellmenge", 0) or 0) * _to_float(order.get("einzelpreis", 0.0), 0.0)
    budget_limit = _to_float(department.get("budget_limit", 0.0), 0.0)
    budget_used = _to_float(department.get("budget_used", 0.0), 0.0)

    if budget_limit > 0 and (budget_used + order_total) > budget_limit:
        flash("Freigabe nicht möglich: Budgetlimit würde überschritten.", "danger")
        return redirect(url_for("page6_procurement"))

    db.update(
        COLLECTION_BESTELLUNGEN,
        bestellung_id,
        {
            "status": "bestellt",
            "budget_verbucht": True,
            "freigegeben_von": _current_username(),
            "freigegeben_am": _now_utc_iso(),
        },
    )
    db.update(COLLECTION_ABTEILUNGEN, department_id, {"budget_used": budget_used + order_total})
    flash("Bestellung freigegeben.", "success")
    return redirect(url_for("page6_procurement"))


@app.route("/ui/bestellungen/<bestellung_id>/ablehnen", methods=["POST"])
def page6_reject_order(bestellung_id: str):
    """Reject an order awaiting approval.

    Args:
        bestellung_id: Order identifier.
    """
    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    db = get_db()
    order = db.find_by_id(COLLECTION_BESTELLUNGEN, bestellung_id)
    if not order:
        flash("Bestellung nicht gefunden.", "danger")
        return redirect(url_for("page6_procurement"))

    if order.get("status", "") != "warte_freigabe":
        flash("Bestellung ist nicht im Freigabestatus.", "danger")
        return redirect(url_for("page6_procurement"))

    db.update(
        COLLECTION_BESTELLUNGEN,
        bestellung_id,
        {
            "status": "abgelehnt",
            "abgelehnt_von": _current_username(),
            "abgelehnt_am": _now_utc_iso(),
        },
    )
    flash("Bestellung wurde abgelehnt.", "info")
    return redirect(url_for("page6_procurement"))


@app.route("/ui/bestellungen/<bestellung_id>/status", methods=["POST"])
def page6_update_order_status(bestellung_id: str):
    """Update status of an existing purchase order.

    Args:
        bestellung_id: Order identifier.
    """
    db = get_db()
    order = db.find_by_id(COLLECTION_BESTELLUNGEN, bestellung_id)
    if not order:
        flash("Bestellung nicht gefunden.", "danger")
        return redirect(url_for("page6_procurement"))

    new_status = request.form.get("status", "").strip()
    allowed = {"entwurf", "bestellt", "teilgeliefert", "abgeschlossen", "storniert"}
    if new_status not in allowed:
        flash("Ungültiger Bestellstatus.", "danger")
        return redirect(url_for("page6_procurement"))

    db.update(COLLECTION_BESTELLUNGEN, bestellung_id, {"status": new_status})
    flash("Bestellstatus aktualisiert.", "success")
    return redirect(url_for("page6_procurement"))


@app.route("/ui/bestellungen/<bestellung_id>/wareneingang", methods=["POST"])
def page6_goods_receipt(bestellung_id: str):
    """Book goods receipt including partial deliveries and backorders.

    Args:
        bestellung_id: Order identifier.
    """
    db = get_db()
    svc_inv = get_inventory_service()

    order = db.find_by_id(COLLECTION_BESTELLUNGEN, bestellung_id)
    if not order:
        flash("Bestellung nicht gefunden.", "danger")
        return redirect(url_for("page6_procurement"))

    if order.get("status", "") in ("storniert", "abgeschlossen", "warte_freigabe", "abgelehnt"):
        flash("Wareneingang für diese Bestellung nicht mehr möglich.", "danger")
        return redirect(url_for("page6_procurement"))

    quantity_raw = request.form.get("menge", "0").strip()
    try:
        quantity = int(quantity_raw)
    except ValueError:
        quantity = 0

    if quantity <= 0:
        flash("Wareneingangsmenge muss größer als 0 sein.", "danger")
        return redirect(url_for("page6_procurement"))

    ordered_qty = int(order.get("bestellmenge", 0) or 0)
    current_received = int(order.get("geliefert", 0) or 0)
    remaining = max(ordered_qty - current_received, 0)
    if remaining <= 0:
        flash("Kein offener Rückstand vorhanden.", "info")
        return redirect(url_for("page6_procurement"))

    booked_qty = min(quantity, remaining)

    try:
        svc_inv.add_product(
            warehouse_id=order.get("lager_id", ""),
            product_id=order.get("produkt_id", ""),
            quantity=booked_qty,
            performed_by=_current_username(),
        )
    except (KeyError, ValueError) as exc:
        flash(f"Wareneingang fehlgeschlagen: {exc}", "danger")
        return redirect(url_for("page6_procurement"))

    new_received = current_received + booked_qty
    new_backorder = max(ordered_qty - new_received, 0)
    new_status = "abgeschlossen" if new_backorder == 0 else "teilgeliefert"

    db.update(
        COLLECTION_BESTELLUNGEN,
        bestellung_id,
        {
            "geliefert": new_received,
            "status": new_status,
            "letzter_wareneingang": _now_utc_iso(),
        },
    )

    if quantity > booked_qty:
        flash(
            "Wareneingang teilweise gebucht (gelieferte Menge überstieg den offenen Rückstand).",
            "info",
        )
    else:
        flash("Wareneingang erfolgreich gebucht.", "success")

    return redirect(url_for("page6_procurement"))


@app.route("/ui/bestellungen/export-pdf", methods=["POST"])
def export_procurement_pdf():
    """Export reorder suggestions as PDF."""
    db = get_db()
    products = db.find_all(COLLECTION_PRODUKTE)
    warehouses = db.find_all(COLLECTION_LAGER)
    inventory = db.find_all(COLLECTION_INVENTAR)

    warehouse_filter_id = request.form.get("lager_id", "").strip()
    suggestions = _build_reorder_recommendations(
        products,
        warehouses,
        inventory,
        warehouse_filter_id=warehouse_filter_id,
    )

    warehouse_name = "Alle Lager"
    if warehouse_filter_id:
        for warehouse in warehouses:
            if warehouse.get("_id") == warehouse_filter_id:
                warehouse_name = warehouse.get("lagername", "Alle Lager")
                break

    pdf_rows = []
    for suggestion in suggestions:
        pdf_rows.append({
            "name": suggestion.get("produkt_name", "-"),
            "menge": suggestion.get("bestand", 0),
            "mindestbestand": suggestion.get("mindestbestand", 0),
        })

    pdf_bytes = build_inventory_pdf(pdf_rows, f"Bestellvorschläge - {warehouse_name}")
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=bestellvorschlaege.pdf"},
    )


# ---------------------------------------------------------------------------
# Page 7 – Picking lists / route planning
# ---------------------------------------------------------------------------


def _build_picking_candidates(inventory: list, products: list, warehouse_id: str, area: str = "") -> list:
    """Build available picking candidate rows for warehouse and area.

    Args:
        inventory: Inventory entries.
        products: Product documents.
        warehouse_id: Selected warehouse identifier.
        area: Optional warehouse area filter.

    Returns:
        List of selectable picking candidate rows.
    """
    product_by_id = _build_lookup(products)
    rows = []

    for entry in inventory:
        if entry.get("lager_id", "") != warehouse_id:
            continue

        quantity = int(entry.get("menge", 0) or 0)
        if quantity <= 0:
            continue

        product = product_by_id.get(entry.get("produkt_id", ""), {})
        product_area = str(product.get("lagerbereich", "A")).strip() or "A"
        product_zone = str(product.get("lagerzone", product_area)).strip() or product_area
        if area and area != product_area:
            continue

        rows.append({
            "produkt_id": entry.get("produkt_id", ""),
            "produkt_name": product.get("name", "-"),
            "lagerbereich": product_area,
            "lagerzone": product_zone,
            "bestand": quantity,
        })

    rows.sort(key=lambda item: (item.get("lagerbereich", ""), item.get("produkt_name", "")))
    return rows


def _estimate_pick_route(items: list, product_by_id: dict) -> tuple[str, int]:
    """Estimate optimized pick route and path length by warehouse zones.

    Args:
        items: Pick items containing product IDs and quantities.
        product_by_id: Lookup map for product documents.

    Returns:
        Tuple of route string and estimated distance in meters.
    """
    zone_coords = {
        "A": (0, 0),
        "B": (12, 0),
        "C": (24, 0),
        "D": (36, 0),
        "E": (0, 14),
        "F": (12, 14),
        "G": (24, 14),
        "H": (36, 14),
    }
    start = (0, -6)

    route_nodes = []
    for item in items:
        product = product_by_id.get(item.get("produkt_id", ""), {})
        zone = str(product.get("lagerzone", product.get("lagerbereich", "A"))).strip() or "A"
        product_name = product.get("name", "-")
        route_nodes.append((zone, product_name))

    route_nodes.sort(key=lambda node: (node[0], node[1]))
    if not route_nodes:
        return ("", 0)

    route_parts = []
    total_distance = 0
    current = start
    for zone, product_name in route_nodes:
        target = zone_coords.get(zone, (0, 0))
        total_distance += abs(target[0] - current[0]) + abs(target[1] - current[1])
        route_parts.append(f"{zone}:{product_name}")
        current = target

    total_distance += abs(current[0] - start[0]) + abs(current[1] - start[1])
    route = " -> ".join(route_parts)
    return (route, int(total_distance))


@app.route("/ui/kommissionierung")
def page7_picking():
    """Render picking list management with route planning by warehouse area."""
    db = get_db()
    warehouses = db.find_all(COLLECTION_LAGER)
    products = db.find_all(COLLECTION_PRODUKTE)
    inventory = db.find_all(COLLECTION_INVENTAR)
    picklists = db.find_all(COLLECTION_PICKLISTEN)
    departments = db.find_all(COLLECTION_ABTEILUNGEN)

    warehouse_filter_id = request.args.get("lager_id", "").strip()
    area_filter = request.args.get("bereich", "").strip()

    candidates = []
    if warehouse_filter_id:
        candidates = _build_picking_candidates(inventory, products, warehouse_filter_id, area_filter)

    product_by_id = _build_lookup(products)
    warehouse_by_id = _build_lookup(warehouses)
    department_by_id = _build_lookup(departments)

    enriched_picklists = []
    for picklist in sorted(picklists, key=lambda p: p.get("erstellt_am", ""), reverse=True):
        row = dict(picklist)
        row["lager_name"] = warehouse_by_id.get(picklist.get("lager_id", ""), {}).get("lagername", "-")
        row["abteilung_name"] = department_by_id.get(picklist.get("abteilung_id", ""), {}).get("name", "-")

        enriched_items = []
        for item in picklist.get("items", []):
            product_name = product_by_id.get(item.get("produkt_id", ""), {}).get("name", "-")
            enriched_items.append({
                "produkt_id": item.get("produkt_id", ""),
                "produkt_name": product_name,
                "menge": int(item.get("menge", 0) or 0),
                "lagerbereich": item.get("lagerbereich", "A"),
                "lagerzone": item.get("lagerzone", "A"),
            })

        row["items"] = enriched_items
        enriched_picklists.append(row)

    area_values = sorted({str(p.get("lagerbereich", "A")).strip() or "A" for p in products})
    active_filter = None
    for warehouse in warehouses:
        if warehouse.get("_id") == warehouse_filter_id:
            active_filter = warehouse
            break

    return render_template(
        "page7_picking.html",
        active_page=7,
        lager=warehouses,
        departments=departments,
        candidates=candidates,
        picklists=enriched_picklists,
        area_values=area_values,
        active_lager_filter=active_filter,
        active_area_filter=area_filter,
    )


@app.route("/ui/kommissionierung/neu", methods=["POST"])
def page7_create_picklist():
    """Create a new picking list and route for a selected warehouse area."""
    db = get_db()
    warehouse_id = request.form.get("lager_id", "").strip()
    department_id = request.form.get("abteilung_id", "").strip()
    area = request.form.get("bereich", "").strip() or "A"

    if not warehouse_id or not department_id:
        flash("Kommissionierliste konnte nicht erstellt werden: Lager und Abteilung sind Pflicht.", "danger")
        return redirect(url_for("page7_picking"))

    product_ids = request.form.getlist("produkt_id[]")
    quantity_values = request.form.getlist("menge[]")

    items = []
    for product_id, quantity_raw in zip(product_ids, quantity_values):
        product_id = (product_id or "").strip()
        if not product_id:
            continue
        try:
            quantity = int(quantity_raw)
        except ValueError:
            continue

        if quantity <= 0:
            continue

        items.append({
            "produkt_id": product_id,
            "menge": quantity,
            "lagerbereich": area,
            "lagerzone": area,
        })

    if not items:
        flash("Kommissionierliste konnte nicht erstellt werden: Keine gültigen Positionen.", "danger")
        return redirect(url_for("page7_picking", lager_id=warehouse_id, bereich=area))

    products = db.find_all(COLLECTION_PRODUKTE)
    product_by_id = _build_lookup(products)
    pick_route, route_distance_m = _estimate_pick_route(items, product_by_id)

    picklist_doc = {
        "lager_id": warehouse_id,
        "abteilung_id": department_id,
        "bereich": area,
        "status": "offen",
        "erstellt_am": _now_utc_iso(),
        "erstellt_von": _current_username(),
        "pick_route": pick_route,
        "weglaenge_m": route_distance_m,
        "items": items,
    }

    db.insert(COLLECTION_PICKLISTEN, picklist_doc)
    flash("Kommissionierliste erfolgreich erstellt.", "success")
    return redirect(url_for("page7_picking", lager_id=warehouse_id, bereich=area))


@app.route("/ui/kommissionierung/<picklist_id>/abschliessen", methods=["POST"])
def page7_complete_picklist(picklist_id: str):
    """Complete a picking list and deduct inventory quantities.

    Args:
        picklist_id: Picking list identifier.
    """
    db = get_db()
    svc_inv = get_inventory_service()

    picklist = db.find_by_id(COLLECTION_PICKLISTEN, picklist_id)
    if not picklist:
        flash("Kommissionierliste nicht gefunden.", "danger")
        return redirect(url_for("page7_picking"))

    if picklist.get("status", "") == "abgeschlossen":
        flash("Kommissionierliste ist bereits abgeschlossen.", "info")
        return redirect(url_for("page7_picking"))

    warehouse_id = picklist.get("lager_id", "")
    errors = []
    for item in picklist.get("items", []):
        product_id = item.get("produkt_id", "")
        quantity = int(item.get("menge", 0) or 0)
        if quantity <= 0:
            continue

        try:
            svc_inv.remove_stock(
                warehouse_id=warehouse_id,
                product_id=product_id,
                quantity=quantity,
                performed_by=_current_username(),
            )
        except (ValueError, KeyError) as exc:
            errors.append(str(exc))

    if errors:
        flash("Kommissionierung teilweise fehlgeschlagen: " + " | ".join(errors[:2]), "danger")
        return redirect(url_for("page7_picking"))

    db.update(
        COLLECTION_PICKLISTEN,
        picklist_id,
        {
            "status": "abgeschlossen",
            "abgeschlossen_am": _now_utc_iso(),
            "abgeschlossen_von": _current_username(),
        },
    )
    flash("Kommissionierliste abgeschlossen und Bestände gebucht.", "success")
    return redirect(url_for("page7_picking"))


@app.route("/ui/kommissionierung/<picklist_id>/druck")
def page7_print_picklist(picklist_id: str):
    """Render a print-friendly picking list with route details.

    Args:
        picklist_id: Picking list identifier.
    """
    db = get_db()
    picklist = db.find_by_id(COLLECTION_PICKLISTEN, picklist_id)
    if not picklist:
        flash("Kommissionierliste nicht gefunden.", "danger")
        return redirect(url_for("page7_picking"))

    products = db.find_all(COLLECTION_PRODUKTE)
    warehouses = db.find_all(COLLECTION_LAGER)
    departments = db.find_all(COLLECTION_ABTEILUNGEN)

    product_by_id = _build_lookup(products)
    warehouse = _build_lookup(warehouses).get(picklist.get("lager_id", ""), {})
    department = _build_lookup(departments).get(picklist.get("abteilung_id", ""), {})

    items = []
    for item in picklist.get("items", []):
        product = product_by_id.get(item.get("produkt_id", ""), {})
        items.append({
            "produkt_name": product.get("name", "-"),
            "menge": int(item.get("menge", 0) or 0),
            "lagerbereich": item.get("lagerbereich", "A"),
            "lagerzone": item.get("lagerzone", "A"),
            "sku": product.get("sku", ""),
        })

    return render_template(
        "page7_pick_print.html",
        picklist=picklist,
        warehouse=warehouse,
        department=department,
        items=items,
    )


# ---------------------------------------------------------------------------
# Page 8 – Settings / personalization
# ---------------------------------------------------------------------------


@app.route("/ui/einstellungen")
def page8_settings():
    """Render the settings workspace for themes and UI preferences."""
    return render_template("page8_settings.html", active_page=8)


@app.route("/ui/admin/benutzer")
def page9_user_admin():
    """Render manager-only user administration page."""
    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    users = _list_users_for_admin()
    manager_count = _manager_count(users)
    audit_events = _list_user_admin_audit_events(limit=50)
    return render_template(
        "page9_user_admin.html",
        active_page=9,
        users=users,
        manager_count=manager_count,
        audit_events=audit_events,
    )


@app.route("/ui/admin/benutzer/neu", methods=["POST"])
def page9_user_create():
    """Create a new login user from admin UI."""
    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    username = str(request.form.get("username", "")).strip()
    display_name = str(request.form.get("display_name", "")).strip() or username
    role = _normalize_user_role(request.form.get("role", "clerk"))
    password = str(request.form.get("password", ""))
    is_active = request.form.get("active", "1") == "1"

    if not username:
        flash("Benutzername darf nicht leer sein.", "danger")
        return redirect(url_for("page9_user_admin"))

    if len(password) < 4:
        flash("Passwort muss mindestens 4 Zeichen haben.", "danger")
        return redirect(url_for("page9_user_admin"))

    existing = _find_user_by_username(username)
    if existing:
        flash("Benutzername existiert bereits.", "danger")
        return redirect(url_for("page9_user_admin"))

    created_user_id = get_db().insert(
        COLLECTION_USERS,
        {
            "username": username,
            "display_name": display_name,
            "role": role,
            "password_hash": generate_password_hash(password),
            "active": is_active,
            "created_at": _now_utc_iso(),
            "updated_at": _now_utc_iso(),
        },
    )
    _record_user_admin_event(
        "create",
        username,
        f"Benutzer {username} angelegt.",
        target_user_id=created_user_id,
        changes={
            "role": role,
            "active": is_active,
            "display_name": display_name,
        },
    )
    flash(f"Benutzer {username} wurde angelegt.", "success")
    return redirect(url_for("page9_user_admin"))


@app.route("/ui/admin/benutzer/<user_id>/rolle", methods=["POST"])
def page9_user_update_role(user_id: str):
    """Update role of an existing user."""
    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    user = _find_user_by_id(user_id)
    if not user:
        flash("Benutzer nicht gefunden.", "danger")
        return redirect(url_for("page9_user_admin"))

    old_role = _normalize_user_role(user.get("role", "clerk"))
    new_role = _normalize_user_role(request.form.get("role", "clerk"))
    username = str(user.get("username", "")).strip()
    if username == _current_username() and new_role != "manager":
        flash("Eigene Rolle kann nicht auf Clerk gesetzt werden.", "danger")
        return redirect(url_for("page9_user_admin"))

    if old_role == new_role:
        flash("Rolle unverändert.", "info")
        return redirect(url_for("page9_user_admin"))

    get_db().update(
        COLLECTION_USERS,
        user_id,
        {
            "role": new_role,
            "updated_at": _now_utc_iso(),
        },
    )
    _record_user_admin_event(
        "update_role",
        username,
        f"Rolle für {username} geändert: {old_role} -> {new_role}.",
        target_user_id=user_id,
        changes={
            "role": {
                "from": old_role,
                "to": new_role,
            }
        },
    )
    flash(f"Rolle für {username} aktualisiert.", "success")
    return redirect(url_for("page9_user_admin"))


@app.route("/ui/admin/benutzer/<user_id>/status", methods=["POST"])
def page9_user_update_status(user_id: str):
    """Activate/deactivate an existing user."""
    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    user = _find_user_by_id(user_id)
    if not user:
        flash("Benutzer nicht gefunden.", "danger")
        return redirect(url_for("page9_user_admin"))

    username = str(user.get("username", "")).strip()
    old_active = bool(user.get("active", True))
    active = request.form.get("active", "0") == "1"
    role = _normalize_user_role(user.get("role", "clerk"))

    if username == _current_username() and not active:
        flash("Eigener Benutzer kann nicht deaktiviert werden.", "danger")
        return redirect(url_for("page9_user_admin"))

    if role == "manager" and not active:
        users = _list_users_for_admin()
        if _manager_count(users) <= 1:
            flash("Mindestens ein aktiver Manager muss erhalten bleiben.", "danger")
            return redirect(url_for("page9_user_admin"))

    if old_active == active:
        flash("Status unverändert.", "info")
        return redirect(url_for("page9_user_admin"))

    get_db().update(
        COLLECTION_USERS,
        user_id,
        {
            "active": active,
            "updated_at": _now_utc_iso(),
        },
    )
    _record_user_admin_event(
        "update_status",
        username,
        f"Status für {username} geändert: {'aktiv' if old_active else 'deaktiviert'} -> {'aktiv' if active else 'deaktiviert'}.",
        target_user_id=user_id,
        changes={
            "active": {
                "from": old_active,
                "to": active,
            }
        },
    )
    flash(f"Status für {username} gespeichert.", "success")
    return redirect(url_for("page9_user_admin"))


@app.route("/ui/admin/benutzer/<user_id>/passwort", methods=["POST"])
def page9_user_reset_password(user_id: str):
    """Reset password for an existing user."""
    manager_guard = _require_manager()
    if manager_guard is not None:
        return manager_guard

    user = _find_user_by_id(user_id)
    if not user:
        flash("Benutzer nicht gefunden.", "danger")
        return redirect(url_for("page9_user_admin"))

    new_password = str(request.form.get("password", ""))
    if len(new_password) < 4:
        flash("Neues Passwort muss mindestens 4 Zeichen haben.", "danger")
        return redirect(url_for("page9_user_admin"))

    username = str(user.get("username", "")).strip()
    get_db().update(
        COLLECTION_USERS,
        user_id,
        {
            "password_hash": generate_password_hash(new_password),
            "updated_at": _now_utc_iso(),
        },
    )
    _record_user_admin_event(
        "reset_password",
        username,
        f"Passwort für {username} zurückgesetzt.",
        target_user_id=user_id,
        changes={"password_changed": True},
    )
    flash(f"Passwort für {username} wurde aktualisiert.", "success")
    return redirect(url_for("page9_user_admin"))

# ---------------------------------------------------------------------------
# Page 5 – History
# ---------------------------------------------------------------------------

@app.route("/ui/historie")
def page5_history():
    """Render Page 5: a reverse-chronological list of all recorded events."""
    db = get_db()
    all_events = db.find_all(COLLECTION_EVENTS)

    # Sort newest-first by ISO 8601 timestamp string
    events_sorted = sorted(all_events, key=lambda e: e.get("timestamp", ""), reverse=True)

    # Format timestamps for display
    for event in events_sorted:
        raw_timestamp = event.get("timestamp", "")
        display_time = _format_timestamp_for_display(raw_timestamp)
        event["display_time"] = display_time

    return render_template("page5_history.html", events=events_sorted, active_page=5)

@app.route("/ui/historie/export", methods=["POST"])
def export_history():
    """Export the complete event history as a downloadable text file."""
    db = get_db()
    all_events = db.find_all(COLLECTION_EVENTS)

    # Sort oldest-first for a chronological export
    sorted_events = sorted(all_events, key=lambda e: e.get("timestamp", ""))

    lines = []
    lines.append("B.I.E.R – Vollständige Historie")
    lines.append("=" * 80)

    if not sorted_events:
        lines.append("Keine Historie-Einträge vorhanden.")
    else:
        for event in sorted_events:
            raw_timestamp = event.get("timestamp", "")
            display_time = _format_timestamp_for_display(raw_timestamp)
            entity_type = event.get("entity_type", "-")
            action = event.get("action", "-")
            summary = event.get("summary", "")
            performed_by = event.get("performed_by", "system")
            lines.append(f"[{display_time}] ({entity_type}/{action}) [{performed_by}] {summary}")

    content = "\n".join(lines)
    return Response(
        content,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=history.txt"},
    )


@app.route("/ui/historie/export-pdf", methods=["POST"])
def export_history_pdf():
    """Export the complete event history as a downloadable PDF file."""
    db = get_db()
    all_events = db.find_all(COLLECTION_EVENTS)
    sorted_events = sorted(all_events, key=lambda e: e.get("timestamp", ""))

    for event in sorted_events:
        raw_timestamp = event.get("timestamp", "")
        event["display_time"] = _format_timestamp_for_display(raw_timestamp)

    pdf_bytes = build_history_pdf(sorted_events)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=history.pdf"},
    )

# ---------------------------------------------------------------------------
# Private helper functions
# ---------------------------------------------------------------------------

def _format_timestamp_for_display(timestamp: str) -> str:
    """Convert an ISO 8601 UTC timestamp to a human-readable German date/time string.

    Args:
        timestamp: ISO 8601 string, optionally ending with ''Z''.

    Returns:
        A string in the format ''DD.MM.YYYY HH:MM:SS'', or the original
        timestamp if parsing fails.
    """
    try:
        clean_timestamp = timestamp.rstrip("Z")
        parsed = datetime.fromisoformat(clean_timestamp)
        return parsed.strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return timestamp or "?"

def _parse_stock_entries_from_form() -> list:
    """Read warehouse/quantity pairs from the current request form.

    Supports two form layouts:
    1. Multi-warehouse: repeated fields ''lager_ids[]'' and ''mengen[]''.
    2. Single-warehouse: single fields ''lager_id'' and ''menge''.

    Returns:
        A list of (warehouse_id, quantity) tuples with valid, positive quantities.
    """
    stock_entries = []

    # Try the multi-warehouse format first
    warehouse_ids = request.form.getlist("lager_ids[]")
    quantities_raw = request.form.getlist("mengen[]")

    for warehouse_id, quantity_raw in zip(warehouse_ids, quantities_raw):
        warehouse_id = (warehouse_id or "").strip()
        if not warehouse_id:
            continue
        try:
            quantity = int(quantity_raw or 0)
        except ValueError:
            continue
        if quantity <= 0:
            continue
        stock_entries.append((warehouse_id, quantity))

    if stock_entries:
        return stock_entries

    # Fall back to the single-warehouse format
    single_warehouse_id = request.form.get("lager_id", "").strip()
    single_quantity_raw = request.form.get("menge", "").strip()

    if single_warehouse_id:
        try:
            single_quantity = int(single_quantity_raw or 0)
        except ValueError:
            single_quantity = 0

        if single_quantity > 0:
            stock_entries.append((single_warehouse_id, single_quantity))

    return stock_entries

if __name__ == "__main__":
    from bierapp.db.init.seed import seed_database
    seed_database()
    host = environ.get("FLASK_HOST", "0.0.0.0")
    port = int(environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port, debug=False)
