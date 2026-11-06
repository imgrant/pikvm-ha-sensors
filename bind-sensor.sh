#!/bin/bash

set -uo pipefail

PROGRAM="${0##*/}"
VERSION="0.4.0"

DRIVER="${DRIVER:-htu21}"
I2C_DEVICE="${I2C_DEVICE:-1-0040}"
SYSFS_ROOT="${SYSFS_ROOT:-/sys}"
ATTEMPTS="${ATTEMPTS:-3}"
RETRY_DELAY="${RETRY_DELAY:-3}"

usage() {
  cat <<EOF
Usage: $PROGRAM [OPTION]...

Bind an I2C sensor whose kernel driver failed to probe at boot. The htu21
driver gives up after one failed transaction, which happens on most PiKVM
boots, leaving the chip present on the bus but with no IIO device.

Does nothing when the device is already bound, so it is cheap to run before
every service start.

Options:
  -n, --dry-run   Report whether a bind is needed, but do not bind
  -q, --quiet     Suppress informational output
  -h, --help      Show this help and exit
  -V, --version   Show the version and exit

Environment:
  DRIVER          Driver to bind (default: $DRIVER)
  I2C_DEVICE      I2C device id, bus-address (default: $I2C_DEVICE)
  SYSFS_ROOT      Sysfs mount point (default: $SYSFS_ROOT)
  ATTEMPTS        Bind attempts before giving up (default: $ATTEMPTS)
  RETRY_DELAY     Seconds between attempts (default: $RETRY_DELAY)

Exit codes:
  0  The device is bound, was bound successfully, or is not present
  1  The device is present but could not be bound
  2  Invalid usage
  3  A bind is needed (--dry-run only)
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

device_path="$SYSFS_ROOT/bus/i2c/devices/$I2C_DEVICE"
driver_path="$SYSFS_ROOT/bus/i2c/drivers/$DRIVER"

if [ ! -d "$device_path" ]; then
  info "no I2C device $I2C_DEVICE; nothing to bind"
  exit 0
fi

if [ -e "$device_path/driver" ]; then
  info "$I2C_DEVICE is already bound to a driver"
  exit 0
fi

if $dry_run; then
  info "$I2C_DEVICE is present but unbound"
  exit 3
fi

if [ ! -d "$driver_path" ]; then
  modprobe "$DRIVER" 2>/dev/null
  [ -d "$driver_path" ] || { warn "driver $DRIVER is unavailable"; exit 1; }
fi

attempt=1
while true; do
  # tee rather than a redirect, so a sysfs write rejected by the kernel does
  # not take the whole script down under `set -o pipefail`.
  printf '%s' "$I2C_DEVICE" | tee "$driver_path/bind" >/dev/null 2>&1

  if [ -e "$device_path/driver" ]; then
    info "bound $I2C_DEVICE to $DRIVER after $attempt attempt(s)"
    exit 0
  fi

  if [ "$attempt" -ge "$ATTEMPTS" ]; then
    warn "could not bind $I2C_DEVICE to $DRIVER after $attempt attempt(s)"
    exit 1
  fi

  attempt=$((attempt + 1))
  sleep "$RETRY_DELAY"
done
