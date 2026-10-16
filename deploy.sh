#!/bin/bash
# Сборка под GitHub Pages прямо в docs/ (локальная site/ не трогается) и публикация: ./deploy.sh "что поменяли"
set -e
cd "$(dirname "$0")"
OUT="$PWD/docs" BASE=/deloros-perm-maket TODAY=${TODAY:-$(date +%F)} python3 src/build.py
git add -A && git commit -q -m "${1:-обновление макета}" && git push -q origin main
echo "https://halitcan777.github.io/deloros-perm-maket/"
