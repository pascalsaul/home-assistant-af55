"""Binary sensor platform for the WNC AF55 integration."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .const import DOMAIN
from .entity import Af55Entity

SENSORS = (
    BinarySensorEntityDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="connected_5g",
        translation_key="connected_5g",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="roaming",
        translation_key="roaming",
        icon="mdi:earth",
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AF55 binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Af55BinarySensor(coordinator, description) for description in SENSORS
    )


class Af55BinarySensor(Af55Entity, BinarySensorEntity):
    """Representation of an AF55 binary sensor."""

    def __init__(self, coordinator, description):
        self.entity_description = description
        super().__init__(coordinator, description.key)
        self._attr_unique_id = f"{coordinator.client.host}_{description.key}"

    @property
    def is_on(self):
        """Return the binary sensor state."""
        data = self.coordinator.data or {}
        key = self.entity_description.key
        if key == "connected":
            return int(data.get("state", 0)) == 3
        if key == "connected_5g":
            return str(data.get("data_bearer_tech", "")).upper() == "NR5G"
        if key == "roaming":
            return bool(int(data.get("roaming", 0)))
        return False
