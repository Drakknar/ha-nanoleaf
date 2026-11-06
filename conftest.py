"""Windows-only pytest_socket patch for the test harness."""

import sys

if sys.platform == "win32":
    # The harness assumes Linux: the Proactor loop needs a socket pair.
    import pytest_socket

    pytest_socket.disable_socket = lambda *args, **kwargs: None
