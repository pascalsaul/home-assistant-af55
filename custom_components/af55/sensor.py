"""AF55 sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTime,
)

from .const import DOMAIN
from .entity import Af55Entity


@dataclass(frozen=True, kw_only=True)
class Desc(SensorEntityDescription):
    """Describe an AF55 sensor."""


SENSORS = (
    Desc(key="data_bearer_tech", translation_key="connection_type", icon="mdi:signal-5g"),
    Desc(
        key="nr_rsrp",
        translation_key="nr_rsrp",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    Desc(
        key="nr_rsrq",
        translation_key="nr_rsrq",
        native_unit_of_measurement="dB",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    Desc(
        key="lte_rsrp",
        translation_key="lte_rsrp",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    Desc(
        key="lte_rsrq",
        translation_key="lte_rsrq",
        native_unit_of_measurement="dB",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    Desc(
        key="signal_strength",
        translation_key="signal_strength",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    Desc(
        key="signal_quality",
        translation_key="signal_quality",
    ),
    Desc(key="ipv4", translation_key="public_ipv4", icon="mdi:ip-network"),
    Desc(key="apn", translation_key="apn", icon="mdi:access-point-network"),
    Desc(key="provider", translation_key="provider", icon="mdi:radio-tower"),
    Desc(
        key="connection_duration_formatted",
        translation_key="connection_duration",
        icon="mdi:timer-outline",
    ),
    Desc(
        key="session_start",
        translation_key="session_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
    ),
    Desc(
        key="last_public_ip_change",
        translation_key="last_public_ip_change",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:ip-network-outline",
    ),
    Desc(key="radio_mode", translation_key="radio_mode", icon="mdi:access-point"),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for description in SENSORS:
        if description.key == "last_public_ip_change":
            entities.append(Af55RestoringTimestampSensor(coordinator, description))
        else:
            entities.append(Af55Sensor(coordinator, description))
    async_add_entities(entities)


class Af55Sensor(Af55Entity, SensorEntity):
    """Representation of an AF55 sensor."""

    def __init__(self, coordinator, description):
        self.entity_description = description
        super().__init__(coordinator, description.key)
        unique_key = "connection_time" if description.key == "connection_duration_formatted" else description.key
        self._attr_unique_id = f"{coordinator.client.host}_{unique_key}"

    @property
    def native_value(self) -> Any:
        """Return the current value."""
        data = self.coordinator.data or {}

        if self.entity_description.key == "signal_quality":
            try:
                level = int(data.get("level", 0))
            except (TypeError, ValueError):
                level = 0
            return {
                5: "excellent",
                4: "very_good",
                3: "good",
                2: "fair",
                1: "weak",
                0: "no_signal",
            }.get(level, "unknown")

        return data.get(self.entity_description.key)

    @property
    def icon(self) -> str | None:
        """Return an icon matching the AF55 signal bars."""
        if self.entity_description.key != "signal_quality":
            return self.entity_description.icon

        try:
            level = int((self.coordinator.data or {}).get("level", 0))
        except (TypeError, ValueError):
            level = 0

        return {
            5: "mdi:signal-cellular-3",
            4: "mdi:signal-cellular-3",
            3: "mdi:signal-cellular-2",
            2: "mdi:signal-cellular-2",
            1: "mdi:signal-cellular-1",
            0: "mdi:signal-cellular-outline",
        }.get(level, "mdi:signal-cellular-outline")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return useful attributes without creating noisy entities."""
        data = self.coordinator.data or {}

        if self.entity_description.key == "connection_duration_formatted":
            return {
                "readable": data.get("connection_duration_formatted"),
                "raw": data.get("connection_time_raw"),
                "session_start": data.get("session_start"),
            }

        if self.entity_description.key == "signal_quality":
            return {
                "bars": data.get("level"),
                "signal_strength_dbm": data.get("signal_strength"),
                "nr_rsrp_dbm": data.get("nr_rsrp"),
                "nr_rsrq_db": data.get("nr_rsrq"),
                "lte_rsrp_dbm": data.get("lte_rsrp"),
                "lte_rsrq_db": data.get("lte_rsrq"),
                "bearer": data.get("data_bearer_tech"),
            }

        if self.entity_description.key == "data_bearer_tech":
            return {
                "raw_bearer": data.get("data_bearer_tech_raw"),
                "radio_mode": data.get("radio_mode"),
                "radio": data.get("radio"),
                "signal_level": data.get("level"),
                "provider": data.get("provider"),
                "network_short_name": data.get("short_name"),
                "spn": data.get("SPN"),
                "apn": data.get("apn"),
                "roaming": bool(int(data.get("roaming", 0))),
                "hostname": data.get("hostname"),
                "product": data.get("product"),
                "customer": data.get("customer"),
                "bridge_mode_supported": bool(int(data.get("bridge_mode", 0))),
            }

        return None

class Af55RestoringTimestampSensor(Af55Entity, RestoreSensor):
    """AF55 timestamp sensor that survives Home Assistant restarts."""

    def __init__(self, coordinator, description):
        self.entity_description = description
        super().__init__(coordinator, description.key)
        self._attr_unique_id = f"{coordinator.client.host}_{description.key}"
        self._restored_value = None

    async def async_added_to_hass(self) -> None:
        """Restore the previous native timestamp."""
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            self._restored_value = last_data.native_value

    @property
    def native_value(self) -> Any:
        """Return a new detected change or the previously restored timestamp."""
        current = (self.coordinator.data or {}).get(self.entity_description.key)
        if current is not None:
            self._restored_value = current
        return self._restored_value

