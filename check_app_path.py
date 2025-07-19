#!/usr/bin/env python
"""
Script to check app path.
"""
import os
from app import create_app

app = create_app()

print(f"app.root_path: {app.root_path}")
print(f"Current working directory: {os.getcwd()}")
print(f"Project root (parent of app.root_path): {os.path.dirname(app.root_path)}")
print(f"Expected migrations path: {os.path.join(os.path.dirname(app.root_path), 'migrations')}")
print(f"Actual migrations path: {os.path.join(os.getcwd(), 'migrations')}")