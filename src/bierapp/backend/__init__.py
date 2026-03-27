"""Backend - Core application and service layers."""

from typing import Any


def create_app() -> Any:
	"""Lazily import and create the Flask application.

	Returns:
		Any: The tuple returned by `bierapp.backend.app.create_app`.
	"""
	from .app import create_app as _create_app
	return _create_app()

__all__ = ["create_app"]

