"""Data update coordinator for WNC AF55."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Af55Client
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .exceptions import Af55ApiError, Af55AuthenticationError, Af55CannotConnect

_LOGGER = logging.getLogger(__name__)

BEARER_DEBOUNCE_SECONDS = 60
SESSION_START_TOLERANCE_SECONDS = 120
STORAGE_VERSION = 1


def parse_connection_duration(value: str | None) -> int | None:
    """Convert AF55 DD:HH:MM:SS session duration to seconds."""
    if not value:
        return None
    try:
        days, hours, minutes, seconds = (int(part) for part in value.split(":"))
    except (TypeError, ValueError):
        return None
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def format_connection_duration(seconds: int | None) -> str | None:
    """Format seconds as days, hours, minutes and seconds."""
    if seconds is None:
        return None
    days, remainder = divmod(max(0, int(seconds)), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{days}d {hours:02d}h {minutes:02d}m {secs:02d}s"


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a stored ISO timestamp."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class Af55Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate polling of the AF55."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: Af55Client,
        entry_id: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.state",
        )
        self._last_public_ip: str | None = None
        self._last_public_ip_change: datetime | None = None
        self._last_session_start: datetime | None = None
        self._previous_duration: int | None = None
        self._last_stable_bearer: str | None = None
        self._bearer_unavailable_since: datetime | None = None

    async def async_load_persisted_state(self) -> None:
        """Restore state needed to distinguish restarts from real changes."""
        stored = await self._store.async_load()
        if not stored:
            return

        last_public_ip = stored.get("last_public_ip")
        if last_public_ip:
            self._last_public_ip = str(last_public_ip)

        self._last_public_ip_change = _parse_datetime(
            stored.get("last_public_ip_change")
        )
        self._last_session_start = _parse_datetime(
            stored.get("last_session_start")
        )

        last_stable_bearer = stored.get("last_stable_bearer")
        if last_stable_bearer:
            self._last_stable_bearer = str(last_stable_bearer)

    async def _async_save_persisted_state(self) -> None:
        """Persist state that cannot be reconstructed reliably after restart."""
        await self._store.async_save(
            {
                "last_public_ip": self._last_public_ip,
                "last_public_ip_change": (
                    self._last_public_ip_change.isoformat()
                    if self._last_public_ip_change
                    else None
                ),
                "last_session_start": (
                    self._last_session_start.isoformat()
                    if self._last_session_start
                    else None
                ),
                "last_stable_bearer": self._last_stable_bearer,
            }
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            status = await self.client.async_get_status()
            raw_duration = await self.client.async_get_connection_time()
        except Af55AuthenticationError as err:
            message = str(err)
            if "failed" in message.lower() or "invalid password" in message.lower():
                raise ConfigEntryAuthFailed("AF55 authentication failed") from err
            raise UpdateFailed(
                f"AF55 session temporarily unavailable: {message}"
            ) from err
        except (Af55CannotConnect, Af55ApiError) as err:
            raise UpdateFailed(str(err)) from err

        now = datetime.now(timezone.utc)
        duration_seconds = parse_connection_duration(raw_duration)
        state_changed = False

        # Debounce transient one-cycle NULL bearer states.
        raw_bearer = status.get("data_bearer_tech")
        normalized_bearer = str(raw_bearer or "").strip()
        bearer_available = normalized_bearer.upper() not in {
            "",
            "NULL",
            "NONE",
            "UNKNOWN",
        }

        if bearer_available:
            if normalized_bearer != self._last_stable_bearer:
                self._last_stable_bearer = normalized_bearer
                state_changed = True
            self._bearer_unavailable_since = None
        else:
            if self._bearer_unavailable_since is None:
                self._bearer_unavailable_since = now

            unavailable_for = (
                now - self._bearer_unavailable_since
            ).total_seconds()
            if (
                self._last_stable_bearer is not None
                and unavailable_for < BEARER_DEBOUNCE_SECONDS
            ):
                status["data_bearer_tech_raw"] = raw_bearer
                status["data_bearer_tech"] = self._last_stable_bearer

        # Track real public IP changes, including changes that occurred while HA
        # was restarting, because the previous IP is now persisted.
        public_ip = status.get("ipv4")
        if public_ip:
            public_ip = str(public_ip)
            if self._last_public_ip is None:
                self._last_public_ip = public_ip
                state_changed = True
            elif public_ip != self._last_public_ip:
                self._last_public_ip = public_ip
                self._last_public_ip_change = now
                state_changed = True

        # Preserve the previous session-start timestamp across HA restarts when
        # the newly calculated value only differs by normal polling jitter.
        if duration_seconds is not None:
            calculated_start = now - timedelta(seconds=duration_seconds)
            if self._previous_duration is None:
                if (
                    self._last_session_start is None
                    or abs(
                        (
                            calculated_start - self._last_session_start
                        ).total_seconds()
                    )
                    > SESSION_START_TOLERANCE_SECONDS
                ):
                    self._last_session_start = calculated_start
                    state_changed = True
            elif duration_seconds + 60 < self._previous_duration:
                self._last_session_start = calculated_start
                state_changed = True

            self._previous_duration = duration_seconds

        if state_changed:
            await self._async_save_persisted_state()

        return {
            **self.client.device_metadata,
            **status,
            "connection_time_raw": raw_duration,
            "connection_duration": duration_seconds,
            "connection_duration_formatted": format_connection_duration(
                duration_seconds
            ),
            "session_start": self._last_session_start,
            "last_public_ip_change": self._last_public_ip_change,
        }
