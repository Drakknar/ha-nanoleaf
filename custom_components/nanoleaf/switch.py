"""Support for Nanoleaf switches."""

from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NanoleafConfigEntry, NanoleafCoordinator
from .entity import NanoleafEntity, async_handle_nanoleaf_errors


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NanoleafConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Nanoleaf switches."""
    coordinator = entry.runtime_data
    if coordinator.supports_screen_mirror:
        async_add_entities([NanoleafMusicSyncSwitch(coordinator)])


class NanoleafMusicSyncSwitch(NanoleafEntity, SwitchEntity):
    """Music Sync of the Nanoleaf 4D Screen Mirroring."""

    _attr_translation_key = "music_sync"

    def __init__(self, coordinator: NanoleafCoordinator) -> None:
        """Initialize the Music Sync switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._nanoleaf.serial_no}_music_sync"

    @property
    @override
    def available(self) -> bool:
        """Return False if the firmware does not report Music Sync."""
        return (
            super().available and self.coordinator.screen_mirror.music_sync is not None
        )

    @property
    @override
    def is_on(self) -> bool | None:
        """Return True if Music Sync is on."""
        return self.coordinator.screen_mirror.music_sync

    @override
    @async_handle_nanoleaf_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch Music Sync on."""
        await self.coordinator.screen_mirror.async_set_music_sync(True)
        self.async_write_ha_state()

    @override
    @async_handle_nanoleaf_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch Music Sync off."""
        await self.coordinator.screen_mirror.async_set_music_sync(False)
        self.async_write_ha_state()
