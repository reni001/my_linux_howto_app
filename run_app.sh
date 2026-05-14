#!/bin/bash

# 1. Force the script to switch to its own directory no matter where it's called from
cd "$(dirname "$0")"

# 2. Activate the virtual environment using the full path
source ./venv/bin/activate

# 3. Run the app with the Wayland fix
KIVY_WINDOW=sdl2 python3 -m src.main

