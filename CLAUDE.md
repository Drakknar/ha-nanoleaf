# ha-nanoleaf

Home Assistant core's `nanoleaf` integration, run as a custom integration with the same domain (it overrides the built-in one), plus controls for the Nanoleaf 4D. Forked from loebi-ch/nanoleaf, whose own code was replaced by core's. Nothing from this repository goes upstream.

## Base

- `custom_components/nanoleaf/` and `tests/`: home-assistant/core `2026.11.0b0` (dev up to 2026-10-28; adds "Remove deprecated device trigger from nanoleaf", core#188656, on top of the earlier base `dev` 724cefe29dd3e866d9fe4024d815f21b1729a0b0).
- `aionanoleaf2==1.2.1`, the same version core pins.

To compare with a newer core: `git diff <base> <tag> -- homeassistant/components/nanoleaf tests/components/nanoleaf` in a core clone, then port it here.

## Differences from core

Keep each of these when porting core changes.

- **2026.10 compatibility shims** (`hacs.json` allows `2026.10.0`). Core `dev` uses APIs that 2026.10 lacks:
  - `async_setup_entry` and `async_unload_entry` return `bool`; unloading uses `async_unload_platforms`, not `async_unload_platforms_or_raise`. 2026.11 still accepts `bool` from custom integrations, with no deprecation (core reports it only for core integrations).
  - This can go once `hacs.json` requires a version that has the newer APIs (2026.11).
- **`manifest.json`:** `version`, `documentation` and `issue_tracker` point to this fork, `@Drakknar` is in `codeowners`, and there is no `categories` (core only).
- **`translations/en.json`** is generated from `strings.json` by `scripts/build_translations.py`: custom integrations get no `[%key:...%]` resolution. `strings.json` also has `reauth_successful` and `reconfigure_successful`, which core gets from its common strings.
- **4D (NL69) entities:**
  - Files: `screen_mirror.py`, `select.py` and `switch.py`, plus `coordinator.py` (`screen_mirror`, `supports_screen_mirror`, `async_refresh_screen_mirror`) and `__init__.py` (`Platform.SELECT`/`SWITCH`, the 15 s `SCREEN_MIRROR_INTERVAL`).
  - Entities: select "Screen mirror mode" (1D–4D; `None` while the effect isn't `*Emersion*`), switch "Music sync" and select "Music sync style" (pulse/fireworks).
  - Music Sync goes through `Nanoleaf._request`, because aionanoleaf2 has no public method for it. That's why the version is pinned.
- **Light fixes** (`light.py`):
  - turn-on sends power, brightness and color in one `set_state`;
  - a transition without brightness keeps the current level (core: 100 %);
  - after a fade-out (device at brightness 0) the level from before the fade is restored (`_brightness_before_fade`);
  - brightness is rounded both ways (`_to_device_brightness`, minimum 1);
  - `*ExtControl*` is in `RESERVED_EFFECTS`.
- **Tests:**
  - Core's tests import `custom_components.nanoleaf` and `pytest_homeassistant_custom_component.common`.
  - `tests/test_light.py` expects `set_state` instead of `turn_on` in the error tests.
  - The snapshot is in the 2026.10 serializer format (`'device_id': <ANY>`; core 2026.11 writes the `DeviceEntry` and `'config_subentry_id': None`).
  - Fork-only tests: `tests/test_screen_mirror.py`, `tests/test_light_state.py`.

## Running the tests

```bash
uv venv -p 3.14 .venv   # the Python version the Home Assistant release requires
uv pip install -p .venv "pytest-homeassistant-custom-component==<release for that HA version>" "aionanoleaf2==1.2.1"
.venv/bin/pytest        # from the repository root
```

- The root `conftest.py` enables custom integrations, puts this repository's `custom_components` first, and uses Home Assistant's snapshot serializer.
- On Windows it also disables `pytest_socket`, and needs stub `fcntl.py`/`resource.py` modules in site-packages.
- Verified 2026-10-24: 166 passed with harness 0.13.373 (HA 2026.10.2), Python 3.14, Windows.
- Verified 2026-10-29: 170 passed with harness 0.13.375 (HA 2026.10.4), Python 3.14, Linux. Harness 0.13.375 can't load HA 2026.11.0b0 (`httpx` alias, removed `_clear_logger_overwrites`); in core's own 2026.11.0b0 test setup (`packages/pytest-home-assistant`), with the bool shims reverted and imports rewritten, all 170 passed. The only errors were core's teardown check that rejects the duplicated `reauth_successful`/`reconfigure_successful` strings.

## Device facts

Verified on the owner's 4D (NL69, firmware 12.3.3, hardware 1.2-1, 47 zones) on 2026-10-24:

- `PUT effects {"write":{"command":...}}` with `getScreenMirrorMode`, `getScreenMirrorRhythmMode` and `getScreenMirrorRhythmModeType` → 200 with `{"screenMirrorMode":5}`, `{"screenMirrorRhythmMode":false}` and `{"screenMirrorRhythmModeType":0}`.
- `activateScreenMirror`, `setScreenMirrorRhythmMode` (bool) and `setScreenMirrorRhythmModeType` (0 pulse, 1 fireworks) → 204, and read back correctly.
- Mode numbers: 1D=6, 2D=2, 3D=3, 4D=5 (Nanoleaf OpenAPI 5.9).
- No SSE event for mode or Music Sync changes. Hence the 15 s refresh.
- `activateScreenMirror` and brightness writes turn the light on.
- A fade-off (`brightness 0` with `duration`) ends `on:false, brightness:0`; a plain `on` then gives 100 %.
- The effect list only holds the 4D's own scenes; `effects.select` is `*Emersion*` while mirroring.
- Live through HA after deploy: mode, Music Sync and style changes reach the device, and changes made directly on the device show up within 15 s.

## Upstream watch

`.github/workflows/compat-review.yml` runs daily and reviews only published versions, never upstream commits:

- every Home Assistant stable release, including patches;
- the first beta of a new minor release;
- every aionanoleaf2 GitHub release.

Model: Sonnet (60 turns) for HA patch releases and aionanoleaf2 releases; Opus (120 turns) when the run includes a beta or an X.Y.0 release. The owner's choice, 2026-10-24.

The main task of a Home Assistant review is keeping `custom_components/nanoleaf/` in line with core's Nanoleaf files; see `.github/prompts/ha-compat.md`.

How it works:

- State lives on the `watch-state` branch.
- `.github/scripts/watch.sh` is shared and must stay byte-identical with the owner's other repositories.
- `WATCH_CLEAR_POLICY=strict`: a "clear" review changes nothing; fixes come as pull requests.
- Needs the `CLAUDE_CODE_OAUTH_TOKEN` Actions secret.

## Deploying

The owner deploys `main` with `git ship` (local tool, `projects/_tools`). It copies `custom_components/nanoleaf` to HA's `config/custom_components/nanoleaf` and offers a restart. HA has no HACS entry for this repository; loebi-ch's HACS repository was removed on 2026-10-24.
