"""Alarm Mail Service - Email parsing and forwarding for emergency alerts."""

__version__ = "0.1.0"

from .app import create_app
from .config import load_config

__all__ = ["create_app", "load_config"]
