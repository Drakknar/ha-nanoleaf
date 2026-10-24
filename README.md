# Nanoleaf (with 4D Screen Mirroring controls)

A fork of [loebi-ch/nanoleaf](https://github.com/loebi-ch/nanoleaf), kept in line with Home Assistant's built-in [Nanoleaf integration](https://www.home-assistant.io/integrations/nanoleaf/) and extended with the Nanoleaf 4D Screen Mirroring settings that the built-in integration doesn't offer yet.

The code is the built-in integration from Home Assistant `dev` (October 2026), adapted to run on Home Assistant **2026.10 and later**. It uses the same domain (`nanoleaf`), so it replaces the built-in integration while installed and keeps your existing config entries and entities.

## What it adds

### Nanoleaf 4D (NL69)

| Entity | What it does |
|---|---|
| **Screen mirror mode** (select: 1D, 2D, 3D, 4D) | Starts Screen Mirroring in that mode and turns the light on. Empty while a scene or color is shown. The modes are also in the light's effect list, as in the built-in integration. |
| **Music sync** (switch) | Turns Music Sync on or off for Screen Mirroring. |
| **Music sync style** (select: Pulse, Fireworks) | How Music Sync reacts to sound. |

The device doesn't push mode or Music Sync changes (for example from the Nanoleaf app), so these three are also fetched every 15 seconds. That's three small requests, made only for a 4D. Everything else is pushed or polled every minute, as before.

These commands come from section 5.9 of the Nanoleaf OpenAPI and were tested on a 4D running firmware 12.3.3. If your firmware doesn't answer them, the Music Sync entities show as unavailable.

Not supported: Sync+ (mirroring onto other Nanoleaf devices), because it isn't part of the local API. While Sync+ streams to another Nanoleaf light, that light shows no effect instead of `*ExtControl*`.

### Light fixes (all models)

- **Turning on with a transition keeps the brightness.** The built-in integration fades to 100 % when no brightness is given.
- **Turning on after a fade-out restores the previous brightness.** A fade-out leaves the device at brightness 0, and the device would otherwise come back at 100 %.
- **Color, color temperature, brightness and power go in one request**, so the light doesn't show an in-between color.
- **Brightness converts without drift.** 50 % stays 50 %, and the lowest Home Assistant brightness no longer sends 0.

## Installation

### HACS

1. In HACS, open the menu → **Custom repositories**.
2. Add `https://github.com/Drakknar/ha-nanoleaf` as an **Integration**.
3. Download **Nanoleaf**, then restart Home Assistant.

If you used `loebi-ch/nanoleaf` before, remove that custom repository from HACS first. It uses the same folder, `custom_components/nanoleaf`.

### Manual

Copy `custom_components/nanoleaf` into your `config/custom_components/` folder and restart Home Assistant.

Setup is the same as for the built-in integration: Settings → Devices & services → Add integration → Nanoleaf.

## Going back to the built-in integration

Remove `custom_components/nanoleaf` (in HACS, or by deleting the folder) and restart. Your config entry and entities stay. The 4D select and switch entities then become unavailable and can be deleted.

## Development

- `pytest` runs Home Assistant core's Nanoleaf tests, adapted to the custom component, plus tests for this fork's additions (`tests/test_screen_mirror.py`, `tests/test_light_state.py`). It needs `pytest-homeassistant-custom-component` for the Home Assistant version you target.
- `translations/en.json` is generated: edit `strings.json`, then run `python scripts/build_translations.py`.

## License

MIT, see [LICENSE](LICENSE). Based on the Home Assistant Nanoleaf integration (Apache 2.0) and loebi-ch/nanoleaf.
