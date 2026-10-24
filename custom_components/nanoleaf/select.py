"""Support for Nanoleaf selects."""

from typing import override

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NanoleafConfigEntry, NanoleafCoordinator
from .entity import NanoleafEntity, async_handle_nanoleaf_errors
from .light import EMERSION_EFFECT
from .screen_mirror import MUSIC_SYNC_STYLE_VALUES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NanoleafConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Nanoleaf selects."""
    coordinator = entry.runtime_data
    if coordinator.supports_screen_mirror:
        async_add_entities(
            [
                NanoleafScreenMirrorModeSelect(coordinator),
                NanoleafMusicSyncStyleSelect(coordinator),
            ]
        )


class NanoleafScreenMirrorModeSelect(NanoleafEntity, SelectEntity):
    """Screen Mirroring mode (1D, 2D, 3D, 4D) of a Nanoleaf 4D.

    Selecting a mode starts Screen Mirroring and turns the light on. While a
    scene or color is shown, no mode is selected.
    """

    _attr_translation_key = "screen_mirror_mode"

    def __init__(self, coordinator: NanoleafCoordinator) -> None:
        """Initialize the Screen Mirroring mode select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._nanoleaf.serial_no}_screen_mirror_mode"

    @property
    @override
    def options(self) -> list[str]:
        """Return the Screen Mirroring modes."""
        return self._nanoleaf.emersion_list

    @property
    @override
    def current_option(self) -> str | None:
        """Return the active mode, None while Screen Mirroring is off."""
        if self._nanoleaf.effect != EMERSION_EFFECT:
            return None
        return self._nanoleaf.selected_emersion

    @override
    @async_handle_nanoleaf_errors
    async def async_select_option(self, option: str) -> None:
        """Start Screen Mirroring in the selected mode."""
        await self._nanoleaf.set_emersion(option)
        await self.coordinator.async_refresh()


class NanoleafMusicSyncStyleSelect(NanoleafEntity, SelectEntity):
    """Music Sync style (pulse or fireworks) of a Nanoleaf 4D."""

    _attr_translation_key = "music_sync_style"
    _attr_options = list(MUSIC_SYNC_STYLE_VALUES)

    def __init__(self, coordinator: NanoleafCoordinator) -> None:
        """Initialize the Music Sync style select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._nanoleaf.serial_no}_music_sync_style"

    @property
    @override
    def available(self) -> bool:
        """Return False if the firmware does not report the style."""
        return (
            super().available
            and self.coordinator.screen_mirror.music_sync_style is not None
        )

    @property
    @override
    def current_option(self) -> str | None:
        """Return the Music Sync style."""
        return self.coordinator.screen_mirror.music_sync_style

    @override
    @async_handle_nanoleaf_errors
    async def async_select_option(self, option: str) -> None:
        """Set the Music Sync style."""
        await self.coordinator.screen_mirror.async_set_music_sync_style(option)
        self.async_write_ha_state()
