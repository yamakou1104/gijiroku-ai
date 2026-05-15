import sys
import pytest

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

windows_only = pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
macos_only = pytest.mark.skipif(not IS_MACOS, reason="macOS-only test")


@pytest.fixture
def platform_audio_format():
    return "dshow" if IS_WINDOWS else "avfoundation"


@pytest.fixture
def platform_screen_format():
    return "gdigrab" if IS_WINDOWS else "avfoundation"
