#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
dry_run=0

target_path="${HOME}/.copilot"
case "${1:-}" in
  "")
    ;;
  --dry-run)
    dry_run=1
    target_path="${2:-${HOME}/.copilot}"
    ;;
  --help|-h)
    echo "Usage: $0 [--dry-run] [target_path]"
    exit 0
    ;;
  *)
    target_path="$1"
    ;;
esac

printf 'Repo root: %s\n' "$repo_root"
printf 'Target path: %s\n' "$target_path"

if [ -e "$target_path" ]; then
  resolved_target="$(realpath "$target_path" 2>/dev/null || printf '%s' "$target_path")"
  resolved_repo="$(realpath "$repo_root" 2>/dev/null || printf '%s' "$repo_root")"

  if [ "$resolved_target" = "$resolved_repo" ]; then
    echo "This repo is already installed as the active Copilot config root. Nothing to do."
    exit 0
  fi

  echo "A different Copilot config already exists at '$target_path'. Remove it or choose a different target path before running this installer."
  exit 1
fi

if [ "$dry_run" -eq 1 ]; then
  echo "[dry-run] Would create a symlink from $target_path -> $repo_root"
  exit 0
fi

mkdir -p "$(dirname "$target_path")"
ln -s "$repo_root" "$target_path"
echo "Portable Copilot setup installed at $target_path"
echo "Keep this repo under version control and pull updates on each machine."
