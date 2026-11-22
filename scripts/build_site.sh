#!/usr/bin/env bash
# Build the GitHub Pages site into ./site exactly as CI does; with --serve, also preview it.
#   scripts/build_site.sh            build only (used by .github/workflows/pages.yml)
#   scripts/build_site.sh --serve    build, then serve on http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf site dist
python -m build --wheel
mkdir -p site/examples
cp web/*.html site/
cp dist/*.whl site/
cp examples/credit/*.json site/examples/
wheel=$(basename dist/*.whl)
version=$(python -c "import casemath; print(casemath.__version__)")
printf '{"wheel": "%s", "version": "%s"}\n' "$wheel" "$version" > site/manifest.json
ls -la site
if [[ "${1:-}" == "--serve" ]]; then
  port="${PORT:-8000}"
  echo
  echo "Home:           http://localhost:${port}/"
  echo "Advisor:        http://localhost:${port}/advisor.html"
  echo "CreditDecision: http://localhost:${port}/credit.html"
  echo "Ctrl-C to stop."
  python -m http.server "$port" --directory site
fi
