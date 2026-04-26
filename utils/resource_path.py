# utils/resource_path.py
import os
import sys

def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)

def get_credentials_dir():
    return get_resource_path("credentials")

def get_app_data_dir():
    app_dir = os.path.join(os.path.expanduser("~"), ".gijiroku-ai")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir
