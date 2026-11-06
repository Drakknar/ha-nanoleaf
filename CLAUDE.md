# ha-nanoleaf

Home Assistant core's `nanoleaf` integration, run as a custom integration with the same domain (it overrides the built-in one), plus controls for the Nanoleaf 4D. Forked from loebi-ch/nanoleaf, whose own code was replaced by core's. Nothing from this repository goes upstream.

## Base

- `custom_components/nanoleaf/` and `tests/`: home-assistant/core `2026.11.0` (74cf5a49c63ed8d4d87717844bf14f79c28c9cea, 2026-11-04). The last Nanoleaf change in it is the connectivity metadata in `manifest.json` (#189910, 2026-11-02, after `2026.11.0b1`), which the fork has; the one before is "Remove deprecated device trigger from nanoleaf" (#188656).
- `aionanoleaf2>=1.2.1`: at least the version core pins (hassfest rejects an exact pin of a package core depends on).

To compare with a newer core: `git diff <base> <tag> -- homeassistant/components/nanoleaf tests/components/nanoleaf` in a core clone, then port it here.

## Differences from core

Keep each of these when porting core changes.

- **`manifest.json`:** `version`, `documentation` and `issue_tracker` point to this fork, `@Drakknar` is in `codeowners`, and there is no `categories` (core only).
- **`translations/en.json`** is generated from `strings.json` by `scripts/build_translations.py`: custom integrations get no `[%key:...%]` resolution. `strings.json` also has `reauth_successful` and `reconfigure_successful`, which core gets from its common strings.
- **4D (NL69) entities:**
  - Files: `screen_mirror.py`, `select.py` and `switch.py`, plus `coordinator.py` (`screen_mirror`, `supports_screen_mirror`, `async_refresh_screen_mirror`) and `__init__.py` (`Platform.SELECT`/`SWITCH`, the 15 s `SCREEN_MIRROR_INTERVAL`).
  - Entities: select "Screen mirror mode" (1D–4D; `None` while the effect isn't `*Emersion*`), switch "Music sync" and select "Music sync style" (pulse/fireworks).
  - Music Sync goes through `Nanoleaf._request`, because aionanoleaf2 has no public method for it. The manifest only sets a minimum (`aionanoleaf2>=1.2.1`), so a new library release can break this: the compatibility review checks each one.
- **Light fixes** (`light.py`):
  - turn-on sends power, brightness and color in one `set_state`;
  - a transition without brightness keeps the current level (core: 100 %);
  - after a fade-out (device at brightness 0) the level from before the fade is restored (`_brightness_before_fade`);
  - brightness is rounded both ways (`_to_device_brightness`, minimum 1);
  - `*ExtControl*` is in `RESERVED_EFFECTS`.
- **Tests:**
  - Core's tests import `custom_components.nanoleaf` instead of `homeassistant.components.nanoleaf`. Their `pytest_homeassistant.common` imports are unchanged: core 2026.11.0's tests use the same module (core's harness package, not `pytest-homeassistant-custom-component`, which stops at 2026.10).
  - `tests/test_light.py` expects `set_state` instead of `turn_on` in the error tests.
  - Fork-only tests: `tests/test_screen_mirror.py`, `tests/test_light_state.py`.

## Running the tests

```bash
uv venv -p '>=3.14.2,<3.15' .venv   # Home Assistant 2026.11's requires-python is >=3.14.2
uv pip install -p .venv "homeassistant==<version>" "pytest-homeassistant==<version>"
# then the integration's requirements, within that release's own pins:
uv pip install -p .venv -c "$(.venv/bin/python -c 'import homeassistant, pathlib; print(pathlib.Path(homeassistant.__file__).parent / "package_constraints.txt")')" "aionanoleaf2==1.2.1"
.venv/bin/pytest        # from the repository root
```

Home Assistant's `package_constraints.txt` doesn't list aionanoleaf2, so the constraints only keep its dependencies from moving Home Assistant's own pins.

The minimum is the `hacs.json` version (2026.11.0); CI runs it (`.github/workflows/checks.yml`) with the minimum aionanoleaf2, read from the manifest's `aionanoleaf2>=` requirement (the step fails if it can't be read). Since 2.3.0 there are no compatibility shims: the code matches core's API for that release.

- The harness enables custom integrations by default and uses Home Assistant's snapshot serializer; its bundled test components live inside `pytest_homeassistant`, so nothing shadows this repository's `custom_components`.
- On Windows the root `conftest.py` disables `pytest_socket`, and the venv needs stub `fcntl.py`/`resource.py` modules in site-packages.
- History: up to 2.2.0 the fork kept shims for 2026.10 and ran on `pytest-homeassistant-custom-component` (170 passed on 0.13.371/0.13.375, Linux).

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

- every Home Assistant stable release, including patches (betas are not reviewed: the owner's choice, 2026-10-30);
- every aionanoleaf2 GitHub release.

Model: Sonnet (60 turns) for HA patch releases and aionanoleaf2 releases; Opus (120 turns) when the run includes an X.Y.0 release. The owner's choice, 2026-10-24.

The main task of a Home Assistant review is keeping `custom_components/nanoleaf/` in line with core's Nanoleaf files; see `.github/prompts/ha-compat.md`.

How it works:

- State lives on the `watch-state` branch.
- `.github/scripts/watch.sh` is shared and must stay byte-identical with the owner's other repositories.
- `WATCH_CLEAR_POLICY=strict`: a "clear" review changes nothing; fixes come as pull requests.
- Needs the `CLAUDE_CODE_OAUTH_TOKEN` Actions secret.

## Deploying

The owner deploys `main` with `git ship` (local tool, `projects/_tools`). It copies `custom_components/nanoleaf` to HA's `config/custom_components/nanoleaf` and offers a restart. Merging a new manifest version also publishes a GitHub release for HACS (`.github/workflows/release.yml`). loebi-ch's HACS repository was removed on 2026-10-24.
