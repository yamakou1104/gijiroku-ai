# tests/test_resource_path.py
import os
import sys
import pytest
from unittest.mock import patch
from utils.resource_path import get_resource_path, get_credentials_dir, get_app_data_dir

def test_get_resource_path_dev_mode():
    if hasattr(sys, "_MEIPASS"):
        pytest.skip("Running in PyInstaller bundle")
    path = get_resource_path("credentials")
    assert os.path.isabs(path)

def test_get_resource_path_frozen():
    with patch.object(sys, "_MEIPASS", "/fake/bundle", create=True):
        path = get_resource_path("credentials")
        assert path.startswith("/fake/bundle")

def test_get_credentials_dir():
    creds = get_credentials_dir()
    assert creds.endswith("credentials")

def test_get_app_data_dir():
    app_dir = get_app_data_dir()
    assert ".gijiroku-ai" in app_dir
