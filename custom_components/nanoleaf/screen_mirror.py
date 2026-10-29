"""Music Sync of the Nanoleaf 4D Screen Mirroring.

aionanoleaf2 1.2.1 only implements the Screen Mirroring mode. The Music Sync
commands are documented in section 5.9 of the Nanoleaf OpenAPI and are sent
through the library's request method, so they share its retries and errors.
"""

from typing import Any

from aionanoleaf2 import (
    EndpointNotFoundError,
    InvalidResponseError,
    Nanoleaf,
    NanoleafConnectionError,
    NanoleafTimeoutError,
    Unavailable,
)

# Models with Screen Mirroring (Nanoleaf 4D)
SCREEN_MIRROR_MODELS = {"NL69"}

# API value -> option of the Music Sync style select
MUSIC_SYNC_STYLES = {0: "pulse", 1: "fireworks"}
MUSIC_SYNC_STYLE_VALUES = {style: value for value, style in MUSIC_SYNC_STYLES.items()}


class ScreenMirror:
    """Music Sync settings of a Nanoleaf 4D."""

    def __init__(self, nanoleaf: Nanoleaf) -> None:
        """Initialize the Music Sync settings."""
        self._nanoleaf = nanoleaf
        self.music_sync: bool | None = None
        self.music_sync_style: str | None = None

    async def _write(self, command: str, **values: Any) -> Any:
        """Send a write command to the effects endpoint."""
        return await self._nanoleaf._request(  # noqa: SLF001
            "put", "effects", {"write": {"command": command, **values}}
        )

    async def _read(self, command: str, key: str) -> Any:
        """Return one value of a get command, None if the firmware lacks it.

        Only a lost connection or a timeout is raised. An HTTP error status
        (other than 401) means the device is reachable but refused this
        command, which should only make the Music Sync entities unavailable,
        not the whole device.
        """
        try:
            payload = await self._write(command)
        except NanoleafConnectionError, NanoleafTimeoutError:
            raise
        except EndpointNotFoundError, InvalidResponseError, Unavailable:
            return None
        return payload.get(key) if isinstance(payload, dict) else None

    async def async_update(self) -> None:
        """Fetch the Music Sync settings."""
        music_sync = await self._read(
            "getScreenMirrorRhythmMode", "screenMirrorRhythmMode"
        )
        self.music_sync = music_sync if isinstance(music_sync, bool) else None
        style = await self._read(
            "getScreenMirrorRhythmModeType", "screenMirrorRhythmModeType"
        )
        self.music_sync_style = (
            MUSIC_SYNC_STYLES.get(style)
            if isinstance(style, int) and not isinstance(style, bool)
            else None
        )

    async def async_set_music_sync(self, music_sync: bool) -> None:
        """Switch Music Sync on or off."""
        await self._write(
            "setScreenMirrorRhythmMode", screenMirrorRhythmMode=music_sync
        )
        self.music_sync = music_sync

    async def async_set_music_sync_style(self, style: str) -> None:
        """Set the Music Sync style (pulse or fireworks)."""
        await self._write(
            "setScreenMirrorRhythmModeType",
            screenMirrorRhythmModeType=MUSIC_SYNC_STYLE_VALUES[style],
        )
        self.music_sync_style = style
