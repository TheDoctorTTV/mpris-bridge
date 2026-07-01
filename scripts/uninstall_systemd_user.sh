#!/usr/bin/env bash
set -euo pipefail

#################
### SETTINGS ###
#################

# Name of the systemd user service removed by this script.
SERVICE_NAME="mpris-bridge.service"
# User writable install locations.
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
BIN_DIR="${XDG_BIN_HOME:-${HOME}/.local/bin}"
SYSTEMD_USER_DIR="${CONFIG_HOME}/systemd/user"
CONFIG_DIR="${CONFIG_HOME}/mpris-bridge"
# Optional cleanup flags default to preserving config and removing binary.
PURGE_CONFIG=0
KEEP_BINARY=0

##########################
### OPTION PARSING ###
##########################

for arg in "$@"; do
  case "${arg}" in
    --purge-config)
      # Remove the user config directory.
      PURGE_CONFIG=1
      ;;
    --keep-binary)
      # Leave the installed binary in place.
      KEEP_BINARY=1
      ;;
    -h|--help)
      # Print usage and stop before changing anything.
      echo "Usage: $0 [--keep-binary] [--purge-config]"
      exit 0
      ;;
    *)
      # Unknown options are treated as errors.
      echo "Unknown option: ${arg}" >&2
      exit 1
      ;;
  esac
done

########################
### REMOVE SERVICE ###
########################

# Stop and disable the user service if it exists.
systemctl --user disable --now "${SERVICE_NAME}" >/dev/null 2>&1 || true
# Remove the user unit file.
rm -f "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
# Reload systemd and clear any failed state left behind.
systemctl --user daemon-reload
systemctl --user reset-failed "${SERVICE_NAME}" >/dev/null 2>&1 || true

#######################
### REMOVE FILES ###
#######################

# Remove the installed binary unless the caller asked to keep it.
if [[ "${KEEP_BINARY}" -eq 0 ]]; then
  rm -f "${BIN_DIR}/mpris-bridge"
fi

# Remove config only when explicitly requested.
if [[ "${PURGE_CONFIG}" -eq 1 ]]; then
  rm -rf "${CONFIG_DIR}"
fi

###################
### SUMMARY ###
###################

echo "Uninstalled ${SERVICE_NAME}."
if [[ "${PURGE_CONFIG}" -eq 0 ]]; then
  echo "Kept config at ${CONFIG_DIR}. Pass --purge-config to remove it."
fi
