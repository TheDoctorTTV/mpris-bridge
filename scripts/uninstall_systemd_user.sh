#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="mpris-bridge.service"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
BIN_DIR="${XDG_BIN_HOME:-${HOME}/.local/bin}"
SYSTEMD_USER_DIR="${CONFIG_HOME}/systemd/user"
CONFIG_DIR="${CONFIG_HOME}/mpris-bridge"
PURGE_CONFIG=0
KEEP_BINARY=0

for arg in "$@"; do
  case "${arg}" in
    --purge-config)
      PURGE_CONFIG=1
      ;;
    --keep-binary)
      KEEP_BINARY=1
      ;;
    -h|--help)
      echo "Usage: $0 [--keep-binary] [--purge-config]"
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      exit 1
      ;;
  esac
done

systemctl --user disable --now "${SERVICE_NAME}" >/dev/null 2>&1 || true
rm -f "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
systemctl --user daemon-reload
systemctl --user reset-failed "${SERVICE_NAME}" >/dev/null 2>&1 || true

if [[ "${KEEP_BINARY}" -eq 0 ]]; then
  rm -f "${BIN_DIR}/mpris-bridge"
fi

if [[ "${PURGE_CONFIG}" -eq 1 ]]; then
  rm -rf "${CONFIG_DIR}"
fi

echo "Uninstalled ${SERVICE_NAME}."
if [[ "${PURGE_CONFIG}" -eq 0 ]]; then
  echo "Kept config at ${CONFIG_DIR}. Pass --purge-config to remove it."
fi
