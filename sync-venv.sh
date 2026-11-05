#!/bin/bash

set -uo pipefail

PROGRAM="${0##*/}"
VERSION="0.4.0"

INSTALL_DIR="${INSTALL_DIR:-/var/lib/kvmd/pst/data/pikvm-ha-sensors}"
SYSTEM_PYTHON="${SYSTEM_PYTHON:-/usr/bin/python3}"
PSTRUN="${PSTRUN-/usr/bin/kvmd-pstrun}"

usage() {
  cat <<EOF
Usage: $PROGRAM [OPTION]...

Rebuild the virtual environment when the system Python no longer matches the
one it was created with. Does nothing when the versions already agree, so it
is cheap to run before every service start.

Options:
  -n, --dry-run   Report whether a rebuild is needed, but do not rebuild
  -q, --quiet     Suppress informational output
  -h, --help      Show this help and exit
  -V, --version   Show the version and exit

Environment:
  INSTALL_DIR     Deployed program directory (default: $INSTALL_DIR)
  SYSTEM_PYTHON   Interpreter to build against (default: $SYSTEM_PYTHON)
  PSTRUN          PiKVM persistent storage wrapper (default: $PSTRUN).
                  Set it empty when already inside a PST session.

Exit codes:
  0  The environment matches, or was rebuilt successfully
  1  The rebuild failed
  2  Invalid usage
  3  A rebuild is needed (--dry-run only)
EOF
}

quiet=false
dry_run=false

while [ $# -gt 0 ]; do
  case "$1" in
    -n|--dry-run) dry_run=true ;;
    -q|--quiet)   quiet=true ;;
    -h|--help)    usage; exit 0 ;;
    -V|--version) echo "$PROGRAM $VERSION"; exit 0 ;;
    *)            echo "$PROGRAM: unrecognised option '$1'" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

info() {
  $quiet || echo "$PROGRAM: $*"
}

warn() {
  echo "$PROGRAM: $*" >&2
}

venv_python_version() {
  sed -n 's/^version_info = \([0-9]\{1,\}\.[0-9]\{1,\}\).*/\1/p' "$INSTALL_DIR/.venv/pyvenv.cfg" 2>/dev/null
}

system_python_version() {
  "$SYSTEM_PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null
}

system_version=$(system_python_version)
if [ -z "$system_version" ]; then
  warn "unable to determine the version of $SYSTEM_PYTHON"
  exit 1
fi

venv_version=$(venv_python_version)

if [ "$venv_version" = "$system_version" ]; then
  info "virtual environment already matches Python $system_version"
  exit 0
fi

if [ -z "$venv_version" ]; then
  info "no usable virtual environment found; building against Python $system_version"
else
  info "Python changed from $venv_version to $system_version; rebuilding the virtual environment"
fi

if $dry_run; then
  exit 3
fi

rebuild="cd '$INSTALL_DIR' && \
  uv venv --clear --system-site-packages --python '$SYSTEM_PYTHON' && \
  uv sync"

# PiKVM mounts the deployed filesystem read-only outside a PST session, and the
# service environment disables syncing, the network and the cache.
if [ -n "$PSTRUN" ]; then
  wrapper=("$PSTRUN" -- /bin/bash -c "$rebuild")
else
  wrapper=(/bin/bash -c "$rebuild")
fi

UV_NO_SYNC=false UV_OFFLINE=false UV_NO_CACHE=false \
UV_CACHE_DIR="$INSTALL_DIR/.cache/uv" \
  "${wrapper[@]}"

status=$?
if [ "$status" -ne 0 ]; then
  warn "rebuild failed (exit $status); the service will retry"
  exit 1
fi

info "virtual environment rebuilt for Python $system_version"
