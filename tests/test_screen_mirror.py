"""Tests for the Nanoleaf 4D Screen Mirroring entities."""

from datetime import timedelta
from unittest.mock import AsyncMock, call

from aionanoleaf2 import EndpointNotFoundError, NanoleafConnectionError, Unavailable
from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import setup_integration

MODE = "select.nanoleaf_screen_mirror_mode"
STYLE = "select.nanoleaf_music_sync_style"
MUSIC = "switch.nanoleaf_music_sync"


def _effects_write(command: str, **values: object) -> call:
    return call("put", "effects", {"write": {"command": command, **values}})


@pytest.fixture
def mock_4d(mock_nanoleaf: AsyncMock) -> AsyncMock:
    """Turn the mocked device into a Nanoleaf 4D mirroring in 4D mode."""
    device = {"rhythm": False, "style": 0}

    async def request(method: str, path: str, data: dict | None = None):
        command = data["write"]
        match command["command"]:
            case "getScreenMirrorRhythmMode":
                return {"screenMirrorRhythmMode": device["rhythm"]}
            case "getScreenMirrorRhythmModeType":
                return {"screenMirrorRhythmModeType": device["style"]}
            case "setScreenMirrorRhythmMode":
                device["rhythm"] = command["screenMirrorRhythmMode"]
            case "setScreenMirrorRhythmModeType":
                device["style"] = command["screenMirrorRhythmModeType"]
        return None

    mock_nanoleaf.model = "NL69"
    mock_nanoleaf.is_on = True
    mock_nanoleaf.effect = "*Emersion*"
    mock_nanoleaf.effects_list = ["Film Noir", "SciFi"]
    mock_nanoleaf.emersion_list = ["1D", "2D", "3D", "4D"]
    mock_nanoleaf.emersion = "4D"
    mock_nanoleaf.selected_emersion = "4D"
    mock_nanoleaf._request.side_effect = request  # noqa: SLF001
    mock_nanoleaf.device = device
    return mock_nanoleaf


async def test_no_entities_without_screen_mirroring(
    hass: HomeAssistant,
    mock_nanoleaf: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test other models get no Screen Mirroring entities and no extra requests."""
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get(MODE) is None
    assert hass.states.get(STYLE) is None
    assert hass.states.get(MUSIC) is None
    mock_nanoleaf._request.assert_not_awaited()  # noqa: SLF001


async def test_entities(
    hass: HomeAssistant, mock_4d: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test the Screen Mirroring entities of a 4D."""
    await setup_integration(hass, mock_config_entry)

    mode = hass.states.get(MODE)
    assert mode.state == "4D"
    assert mode.attributes[ATTR_OPTIONS] == ["1D", "2D", "3D", "4D"]
    style = hass.states.get(STYLE)
    assert style.state == "pulse"
    assert style.attributes[ATTR_OPTIONS] == ["pulse", "fireworks"]
    assert hass.states.get(MUSIC).state == STATE_OFF


async def test_mode_is_empty_while_a_scene_is_shown(
    hass: HomeAssistant, mock_4d: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test no mode is selected while the 4D shows a scene."""
    mock_4d.effect = "Film Noir"
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get(MODE).state == STATE_UNKNOWN


async def test_select_mode(
    hass: HomeAssistant, mock_4d: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test selecting a mode starts Screen Mirroring in that mode."""
    await setup_integration(hass, mock_config_entry)

    async def set_emersion(mode: str) -> None:
        mock_4d.emersion = mock_4d.selected_emersion = mode

    mock_4d.set_emersion.side_effect = set_emersion
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: MODE, ATTR_OPTION: "2D"},
        blocking=True,
    )

    mock_4d.set_emersion.assert_awaited_once_with("2D")
    assert hass.states.get(MODE).state == "2D"


async def test_music_sync(
    hass: HomeAssistant, mock_4d: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test switching Music Sync and choosing its style."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: MUSIC}, blocking=True
    )
    assert hass.states.get(MUSIC).state == STATE_ON
    assert mock_4d._request.await_args == _effects_write(  # noqa: SLF001
        "setScreenMirrorRhythmMode", screenMirrorRhythmMode=True
    )

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: STYLE, ATTR_OPTION: "fireworks"},
        blocking=True,
    )
    assert hass.states.get(STYLE).state == "fireworks"
    assert mock_4d._request.await_args == _effects_write(  # noqa: SLF001
        "setScreenMirrorRhythmModeType", screenMirrorRhythmModeType=1
    )

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: MUSIC}, blocking=True
    )
    assert hass.states.get(MUSIC).state == STATE_OFF
    assert mock_4d.device == {"rhythm": False, "style": 1}


async def test_music_sync_error(
    hass: HomeAssistant, mock_4d: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test a failed Music Sync write is a Home Assistant error."""
    await setup_integration(hass, mock_config_entry)
    mock_4d._request.side_effect = NanoleafConnectionError("down")  # noqa: SLF001

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: MUSIC}, blocking=True
        )
    assert hass.states.get(MUSIC).state == STATE_OFF


async def test_firmware_without_music_sync(
    hass: HomeAssistant, mock_4d: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test Music Sync entities are unavailable if the firmware lacks them."""
    mock_4d._request.side_effect = EndpointNotFoundError("effects")  # noqa: SLF001
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get(MUSIC).state == STATE_UNAVAILABLE
    assert hass.states.get(STYLE).state == STATE_UNAVAILABLE
    assert hass.states.get(MODE).state == "4D"


async def test_music_sync_refused_by_the_device(
    hass: HomeAssistant, mock_4d: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test an HTTP error on a Music Sync read leaves the rest of the device up."""
    mock_4d._request.side_effect = Unavailable("Device returned HTTP 400 for 'effects'")  # noqa: SLF001
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get("light.nanoleaf").state != STATE_UNAVAILABLE
    assert hass.states.get(MODE).state == "4D"
    assert hass.states.get(MUSIC).state == STATE_UNAVAILABLE
    assert hass.states.get(STYLE).state == STATE_UNAVAILABLE


async def test_music_sync_read_connection_error(
    hass: HomeAssistant, mock_4d: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test a lost connection on a Music Sync read still fails the update."""
    await setup_integration(hass, mock_config_entry)
    mock_4d._request.side_effect = NanoleafConnectionError("down")  # noqa: SLF001

    await mock_config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("light.nanoleaf").state == STATE_UNAVAILABLE
    assert hass.states.get(MODE).state == STATE_UNAVAILABLE


@pytest.mark.parametrize("style", [[0], {"0": 1}, True, 2, None])
async def test_unexpected_music_sync_style(
    hass: HomeAssistant,
    mock_4d: AsyncMock,
    mock_config_entry: MockConfigEntry,
    style: object,
) -> None:
    """Test a style value of an unexpected type or value makes the select unavailable."""
    mock_4d.device["style"] = style
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get(STYLE).state == STATE_UNAVAILABLE
    assert hass.states.get(MUSIC).state == STATE_OFF


async def test_changes_from_the_app_are_polled(
    hass: HomeAssistant,
    mock_4d: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test mode and Music Sync changes made elsewhere show up within 15 s."""
    await setup_integration(hass, mock_config_entry)
    full_updates = mock_4d.get_info.await_count

    async def get_emersion() -> None:
        mock_4d.emersion = mock_4d.selected_emersion = "3D"

    mock_4d.get_emersion.side_effect = get_emersion
    mock_4d.device["rhythm"] = True

    freezer.tick(timedelta(seconds=15))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.states.get(MODE).state == "3D"
    assert hass.states.get(MUSIC).state == STATE_ON
    # Only the Screen Mirroring settings were fetched, not the full state
    assert mock_4d.get_info.await_count == full_updates


async def test_partial_poll_is_still_reported(
    hass: HomeAssistant,
    mock_4d: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a value read before a failing request of the quick poll shows up."""
    await setup_integration(hass, mock_config_entry)
    mock_4d.device["rhythm"] = True
    request = mock_4d._request.side_effect  # noqa: SLF001

    async def style_fails(method: str, path: str, data: dict | None = None):
        if data["write"]["command"] == "getScreenMirrorRhythmModeType":
            raise NanoleafConnectionError("blip")
        return await request(method, path, data)

    mock_4d._request.side_effect = style_fails  # noqa: SLF001
    freezer.tick(timedelta(seconds=15))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.states.get(MUSIC).state == STATE_ON


async def test_poll_errors_are_left_to_the_regular_update(
    hass: HomeAssistant,
    mock_4d: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a failing quick poll does not make the entities unavailable."""
    await setup_integration(hass, mock_config_entry)
    mock_4d.get_emersion.side_effect = NanoleafConnectionError("blip")

    freezer.tick(timedelta(seconds=15))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.states.get(MODE).state == "4D"
    assert hass.states.get(MUSIC).state == STATE_OFF
