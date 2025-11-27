#!/bin/bash
set -e
# Перехід у каталог, де лежить скрипт
cd "$(dirname "$0")"
# Встановлення залежностей
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
# Інсталяція браузерів для playwright
python3 -m playwright install
# Запуск основного скрипта
python3 dtek_checker.py