"""Define the Nanoleaf data coordinator."""

from datetime import timedelta
import logging
from typing import override

from aionanoleaf2 import AuthError, Nanoleaf, NanoleafError, NoAuthToken

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .screen_mirror import SCREEN_MIRROR_MODELS, ScreenMirror

_LOGGER = logging.getLogger(__name__)

type NanoleafConfigEntry = ConfigEntry[NanoleafCoordinator]


class NanoleafCoordinator(DataUpdateCoordinator[None]):
    """Class to manage fetching Nanoleaf data."""

    config_entry: NanoleafConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: NanoleafConfigEntry, nanoleaf: Nanoleaf
    ) -> None:
        """Initialize the Nanoleaf data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="Nanoleaf",
            update_interval=timedelta(minutes=1),
        )
        self.nanoleaf = nanoleaf
        self.screen_mirror = ScreenMirror(nanoleaf)

    @override
    async def _async_update_data(self) -> None:
        try:
            await self.nanoleaf.get_info()
            if self.supports_screen_mirror:
                await self.screen_mirror.async_update()
        except (AuthError, NoAuthToken) as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_token"
            ) from err
        except NanoleafError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from err

    @property
    def supports_screen_mirror(self) -> bool:
        """Return True if the device has Screen Mirroring (Nanoleaf 4D)."""
        return self.nanoleaf.model in SCREEN_MIRROR_MODELS

    async def async_refresh_screen_mirror(self) -> None:
        """Fetch only the Screen Mirroring settings.

        The device pushes no event when the mode or Music Sync changes while
        Screen Mirroring stays active, so these are polled more often than the
        full state. Errors are left to the regular update.
        """
        if not self.last_update_success:
            return
        nanoleaf = self.nanoleaf
        before = (
            nanoleaf.emersion,
            self.screen_mirror.music_sync,
            self.screen_mirror.music_sync_style,
        )
        try:
            await nanoleaf.get_emersion()
            await self.screen_mirror.async_update()
        except NanoleafError as err:
            _LOGGER.debug("Could not refresh the Screen Mirroring settings: %s", err)
            return
        if before != (
            nanoleaf.emersion,
            self.screen_mirror.music_sync,
            self.screen_mirror.music_sync_style,
        ):
            self.async_update_listeners()
