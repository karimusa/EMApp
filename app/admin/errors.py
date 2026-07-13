"""User administration errors."""

from __future__ import annotations


class UserAdminError(ValueError):
    """Validation or business-rule failure for user management."""


class LiveDataRequiredError(RuntimeError):
    """Raised when a mutation requires a validated PRIMARY SQL connection."""
