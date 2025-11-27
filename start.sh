#!/bin/bash
pip install -r requirements.txt
python -m playwright install-deps
python -m playwright install chromium
python dtek_checker.py
