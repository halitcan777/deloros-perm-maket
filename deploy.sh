#!/bin/bash
# Сборка под GitHub Pages и публикация: ./deploy.sh "что поменяли"
set -e
cd "$(dirname "$0")"
BASE=/deloros-perm-maket TODAY=${TODAY:-$(date +%F)} python3 src/build.py
rm -rf docs && cp -R site docs
git add -A && git commit -q -m "${1:-обновление макета}" && git push -q origin main
echo "https://halitcan777.github.io/deloros-perm-maket/"
