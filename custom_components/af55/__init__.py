"""WNC AF55 integration."""

from __future__ import annotations

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Af55Client
from .const import (
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import Af55Coordinator


async def async_setup_entry(hass, entry):
    """Set up WNC AF55 from a config entry."""
    client = Af55Client(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.options.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )
    coordinator = Af55Coordinator(
        hass,
        client,
        entry.entry_id,
        entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    coordinator.config_entry = entry
    await coordinator.async_load_persisted_state()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    registry = er.async_get(hass)
    obsolete_unique_id = f"{client.host}_connection_duration_formatted"
    obsolete_entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, obsolete_unique_id
    )
    if obsolete_entity_id:
        registry.async_remove(obsolete_entity_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_shutdown(_event: Event) -> None:
        await client.async_logout()

    remove_stop_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP,
        _async_shutdown,
    )
    entry.async_on_unload(remove_stop_listener)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def async_unload_entry(hass, entry):
    """Unload WNC AF55 and release its administrator session."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not ok:
        return False
    if coordinator is not None:
        await coordinator.client.async_logout()
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


async def _reload(hass, entry):
    """Reload the config entry after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
