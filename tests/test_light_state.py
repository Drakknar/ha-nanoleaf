"""Tests for the requests the Nanoleaf light sends (fork fixes)."""

from unittest.mock import AsyncMock, call

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant

from . import setup_integration


async def _call(hass: HomeAssistant, service: str, **data: object) -> None:
    await hass.services.async_call(
        LIGHT_DOMAIN,
        service,
        {ATTR_ENTITY_ID: "light.nanoleaf", **data},
        blocking=True,
    )


def _state(**values: object) -> call:
    """Return the expected set_state call."""
    return call(
        **{
            "on": True,
            "brightness": None,
            "brightness_transition": None,
            "hue": None,
            "saturation": None,
            "color_temperature": None,
        }
        | values
    )


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param({}, _state(), id="plain"),
        pytest.param({ATTR_BRIGHTNESS_PCT: 50}, _state(brightness=50), id="50%"),
        pytest.param({ATTR_BRIGHTNESS: 1}, _state(brightness=1), id="lowest"),
        pytest.param({ATTR_BRIGHTNESS: 255}, _state(brightness=100), id="highest"),
        pytest.param(
            {ATTR_HS_COLOR: (200, 80), ATTR_BRIGHTNESS_PCT: 30},
            _state(hue=200, saturation=80, brightness=30),
            id="color and brightness at once",
        ),
        pytest.param(
            {ATTR_COLOR_TEMP_KELVIN: 3000},
            _state(color_temperature=3000),
            id="color temperature",
        ),
        pytest.param(
            {ATTR_TRANSITION: 3},
            _state(on=None, brightness=50, brightness_transition=3),
            id="fade in keeps the level",
        ),
        pytest.param(
            {ATTR_TRANSITION: 3, ATTR_BRIGHTNESS_PCT: 80},
            _state(on=None, brightness=80, brightness_transition=3),
            id="fade in to a level",
        ),
    ],
)
async def test_turn_on_sends_one_request(
    hass: HomeAssistant,
    mock_nanoleaf: AsyncMock,
    mock_config_entry: MockConfigEntry,
    data: dict,
    expected: call,
) -> None:
    """Test turning on sends power, color and brightness in one request."""
    await setup_integration(hass, mock_config_entry)

    await _call(hass, SERVICE_TURN_ON, **data)

    assert mock_nanoleaf.set_state.await_args_list == [expected]
    mock_nanoleaf.turn_on.assert_not_awaited()
    mock_nanoleaf.set_brightness.assert_not_awaited()


async def test_brightness_round_trip(
    hass: HomeAssistant,
    mock_nanoleaf: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test 50% on the device is reported as 50% and sent back as 50%."""
    mock_nanoleaf.is_on = True
    await setup_integration(hass, mock_config_entry)

    brightness = hass.states.get("light.nanoleaf").attributes[ATTR_BRIGHTNESS]
    assert brightness == 128  # what HA uses for 50 %
    await _call(hass, SERVICE_TURN_ON, **{ATTR_BRIGHTNESS: brightness})
    assert mock_nanoleaf.set_state.await_args == _state(brightness=50)


async def test_turn_on_after_fade_out_restores_level(
    hass: HomeAssistant,
    mock_nanoleaf: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test a fade-out (device left at 0) is not followed by 100% on."""
    mock_nanoleaf.is_on = True
    mock_nanoleaf.brightness = 40
    await setup_integration(hass, mock_config_entry)

    await _call(hass, SERVICE_TURN_OFF, **{ATTR_TRANSITION: 2})
    mock_nanoleaf.turn_off.assert_awaited_once_with(2)

    # The device turns off at the end of the fade and keeps brightness 0
    mock_nanoleaf.is_on = False
    mock_nanoleaf.brightness = 0

    await _call(hass, SERVICE_TURN_ON)
    assert mock_nanoleaf.set_state.await_args == _state(brightness=40)

    # Only once: after that the device has its level again
    mock_nanoleaf.brightness = 40
    await _call(hass, SERVICE_TURN_ON)
    assert mock_nanoleaf.set_state.await_args == _state()


async def test_turn_on_at_zero_without_known_level(
    hass: HomeAssistant,
    mock_nanoleaf: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test brightness 0 from before a restart turns on at full brightness."""
    mock_nanoleaf.brightness = 0
    await setup_integration(hass, mock_config_entry)

    await _call(hass, SERVICE_TURN_ON)
    assert mock_nanoleaf.set_state.await_args == _state(brightness=100)


async def test_effect_with_brightness(
    hass: HomeAssistant,
    mock_nanoleaf: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test an effect is selected and power and brightness follow in one request."""
    await setup_integration(hass, mock_config_entry)

    await _call(
        hass, SERVICE_TURN_ON, **{ATTR_EFFECT: "Sunset", ATTR_BRIGHTNESS_PCT: 50}
    )

    mock_nanoleaf.set_effect.assert_awaited_once_with("Sunset")
    assert mock_nanoleaf.set_state.await_args_list == [_state(brightness=50)]


@pytest.mark.parametrize("effect", ["*ExtControl*", "*Static*", "*Dynamic*"])
async def test_reserved_effects_are_not_reported(
    hass: HomeAssistant,
    mock_nanoleaf: AsyncMock,
    mock_config_entry: MockConfigEntry,
    effect: str,
) -> None:
    """Test streaming (e.g. 4D Sync+) and implicit effects are not reported."""
    mock_nanoleaf.is_on = True
    mock_nanoleaf.effect = effect
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get("light.nanoleaf").attributes[ATTR_EFFECT] is None
