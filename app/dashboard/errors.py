"""Dashboard execution errors."""

from __future__ import annotations


class ExecutionError(ValueError):
    """Validation or business-rule failure for run/step execution."""


class LiveExecutionRequiredError(RuntimeError):
    """Raised when execution requires a validated PRIMARY SQL connection."""
