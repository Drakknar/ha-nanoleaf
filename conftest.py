"""Test setup for running the integration as a custom component."""

from pathlib import Path
import sys

import pytest

if sys.platform == "win32":
    # The harness assumes Linux: the Proactor loop needs a socket pair.
    import pytest_socket

    pytest_socket.disable_socket = lambda *args, **kwargs: None


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load the integration from custom_components."""
    # The harness's own testing_config/custom_components shadows ours.
    import custom_components  # noqa: PLC0415

    ours = str(Path(__file__).parent / "custom_components")
    if ours not in custom_components.__path__:
        custom_components.__path__.insert(0, ours)


@pytest.fixture
def snapshot(snapshot):
    """Serialize Home Assistant objects as core's tests do."""
    from pytest_homeassistant_custom_component.syrupy import (  # noqa: PLC0415
        HomeAssistantSnapshotExtension,
    )

    return snapshot.use_extension(HomeAssistantSnapshotExtension)
