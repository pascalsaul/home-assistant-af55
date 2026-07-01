"""Button platform for WNC AF55."""

from __future__ import annotations

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN
from .entity import Af55Entity
from .exceptions import Af55ApiError, Af55AuthenticationError, Af55CannotConnect

BUTTONS = (
    ButtonEntityDescription(
        key="reboot",
        translation_key="reboot",
        device_class=ButtonDeviceClass.RESTART,
        icon="mdi:restart",
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AF55 buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Af55Button(coordinator, description) for description in BUTTONS
    )


class Af55Button(Af55Entity, ButtonEntity):
    """AF55 action button."""

    def __init__(self, coordinator, description):
        self.entity_description = description
        super().__init__(coordinator, description.key)
        self._attr_unique_id = f"{coordinator.client.host}_{description.key}"

    async def async_press(self) -> None:
        """Reboot the AF55 modem."""
        if self.entity_description.key != "reboot":
            return
        try:
            await self.coordinator.client.async_reboot()
            await self.coordinator.client.async_reset_session()
        except (Af55ApiError, Af55AuthenticationError, Af55CannotConnect) as err:
            raise UpdateFailed(str(err)) from err
