"""Diagnostics support for WNC AF55."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {
    "ipv4",
    "ipv6",
    "public_ipv4",
    "imsi",
    "imei",
    "mac",
    "password",
    "token",
    "cgitoken",
    "CGISID",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return redacted diagnostics for an AF55 config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "coordinator": async_redact_data(dict(coordinator.data or {}), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
    }
