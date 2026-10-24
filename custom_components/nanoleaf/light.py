"""Support for Nanoleaf Lights."""

from typing import Any, override

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import NanoleafConfigEntry, NanoleafCoordinator
from .entity import NanoleafEntity, async_handle_nanoleaf_errors

# *ExtControl* is reported while the light is streamed to, e.g. by a 4D with Sync+.
RESERVED_EFFECTS = ("*Solid*", "*Static*", "*Dynamic*", "*ExtControl*")
# Reported as the active effect while a Screen Mirroring mode of a Nanoleaf 4D runs.
EMERSION_EFFECT = "*Emersion*"
DEFAULT_NAME = "Nanoleaf"


def _to_device_brightness(brightness: int) -> int:
    """Convert Home Assistant brightness (1-255) to device brightness (1-100)."""
    return max(1, round(brightness * 100 / 255))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NanoleafConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Nanoleaf light."""
    async_add_entities([NanoleafLight(entry.runtime_data)])


class NanoleafLight(NanoleafEntity, LightEntity):
    """Representation of a Nanoleaf Light."""

    _attr_supported_color_modes = {ColorMode.COLOR_TEMP, ColorMode.HS}
    _attr_supported_features = LightEntityFeature.EFFECT | LightEntityFeature.TRANSITION
    _attr_name = None
    _attr_translation_key = "light"

    def __init__(self, coordinator: NanoleafCoordinator) -> None:
        """Initialize the Nanoleaf light."""
        super().__init__(coordinator)
        self._attr_unique_id = self._nanoleaf.serial_no
        # A fade-out leaves the device at brightness 0. Turning on without a
        # brightness then restores this level instead of the device's 100%.
        self._brightness_before_fade: int | None = None
        self._attr_max_color_temp_kelvin = self._nanoleaf.color_temperature_max
        self._attr_min_color_temp_kelvin = self._nanoleaf.color_temperature_min

    @property
    @override
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return round(self._nanoleaf.brightness * 255 / 100)

    @property
    @override
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature value in Kelvin."""
        return self._nanoleaf.color_temperature

    @property
    @override
    def effect(self) -> str | None:
        """Return the current effect."""
        # The API returns the *Solid* effect if the Nanoleaf is in HS or CT mode.
        # The effects *Static* and *Dynamic* are not supported by Home Assistant.
        # These reserved effects are implicitly set and are not in the effect_list.
        # https://forum.nanoleaf.me/docs/openapi#_byoot0bams8f
        effect = self._nanoleaf.effect
        if effect == EMERSION_EFFECT:
            # Screen Mirroring modes (1D, 2D, 3D, 4D) are offered as effects.
            return self._nanoleaf.selected_emersion
        return None if not effect or effect in RESERVED_EFFECTS else effect

    @property
    @override
    def effect_list(self) -> list[str]:
        """Return the list of supported effects.

        Devices with Screen Mirroring (Nanoleaf 4D) additionally offer their
        modes (1D, 2D, 3D, 4D) as effects. A regular effect with the same name
        takes precedence.
        """
        effects = self._nanoleaf.effects_list
        return [
            *effects,
            *(mode for mode in self._nanoleaf.emersion_list if mode not in effects),
        ]

    @property
    @override
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._nanoleaf.is_on

    @property
    @override
    def hs_color(self) -> tuple[int, int]:
        """Return the color in HS."""
        return self._nanoleaf.hue, self._nanoleaf.saturation

    @property
    @override
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        # According to API docs, color mode is "ct", "effect" or "hs"
        # https://forum.nanoleaf.me/docs/openapi#_4qgqrz96f44d
        if self._nanoleaf.color_mode == "ct":
            return ColorMode.COLOR_TEMP
        # Home Assistant does not have an "effect" color mode, just report hs
        return ColorMode.HS

    @override
    @async_handle_nanoleaf_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        hs_color = kwargs.get(ATTR_HS_COLOR)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        effect = kwargs.get(ATTR_EFFECT)
        transition = kwargs.get(ATTR_TRANSITION)

        if effect:
            if effect not in self.effect_list:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_effect",
                    translation_placeholders={"effect": str(effect)},
                )
            if effect in self._nanoleaf.effects_list:
                await self._nanoleaf.set_effect(effect)
            else:
                # Not a regular effect, so it is a Screen Mirroring mode.
                await self._nanoleaf.set_emersion(effect)

        if brightness:
            device_brightness: int | None = _to_device_brightness(brightness)
        elif self._nanoleaf.brightness == 0 or transition:
            # After a fade-out, or for a fade-in: back to the last level.
            device_brightness = (
                self._nanoleaf.brightness or self._brightness_before_fade or 100
            )
        else:
            device_brightness = None

        hue = saturation = color_temperature = None
        if not effect:
            if hs_color:
                hue, saturation = (int(value) for value in hs_color)
            elif color_temp_kelvin:
                color_temperature = color_temp_kelvin

        # One request, so color and brightness change together. Brightness
        # with a duration fades in and turns the light on by itself.
        await self._nanoleaf.set_state(
            on=None if transition else True,
            brightness=device_brightness,
            brightness_transition=int(transition) if transition else None,
            hue=hue,
            saturation=saturation,
            color_temperature=color_temperature,
        )
        self._brightness_before_fade = None
        await self.coordinator.async_refresh()

    @override
    @async_handle_nanoleaf_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        transition: float | None = kwargs.get(ATTR_TRANSITION)
        if transition is not None and self._nanoleaf.brightness:
            self._brightness_before_fade = self._nanoleaf.brightness
        await self._nanoleaf.turn_off(None if transition is None else int(transition))
        await self.coordinator.async_refresh()
