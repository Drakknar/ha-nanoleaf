"""Test setup for running the integration as a custom component."""

from pathlib import Path
import sys

import pytest

if sys.platform == "win32":
    # The harness assumes Linux: the Proactor loop needs a socket pair.
    import pytest_socket

    pytest_socket.disable_socket = lambda *args, **kwargs: None


@pytest.fixture(autouse=True)
def use_repo_custom_components():
    """Load the integration from this repository's custom_components."""
    # The harness enables custom integrations, but its own
    # testing_config/custom_components package shadows ours.
    import custom_components  # noqa: PLC0415

    ours = str(Path(__file__).parent / "custom_components")
    if ours not in custom_components.__path__:
        custom_components.__path__.insert(0, ours)

