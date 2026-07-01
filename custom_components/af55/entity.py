"""AF55 entity base."""
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
class Af55Entity(CoordinatorEntity):
    _attr_has_entity_name=True
    def __init__(self,coordinator,key):
        super().__init__(coordinator); self._key=key; host=coordinator.client.host
        metadata = coordinator.data or {}
        self._attr_device_info=DeviceInfo(
            identifiers={(DOMAIN,host)},
            manufacturer="WNC",
            model=str(metadata.get("product") or "AF55 Outdoor"),
            name="WNC AF55 Outdoor",
            configuration_url=host if host.startswith(("http://","https://")) else f"https://{host}",
        )
