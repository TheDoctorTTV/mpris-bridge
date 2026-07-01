#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="mpris-bridge.service"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd -P)"

BIN_DIR="${XDG_BIN_HOME:-${HOME}/.local/bin}"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
CONFIG_DIR="${CONFIG_HOME}/mpris-bridge"
SYSTEMD_USER_DIR="${CONFIG_HOME}/systemd/user"

if [[ -n "${MPRIS_BRIDGE_BINARY:-}" ]]; then
  BINARY_SOURCE="${MPRIS_BRIDGE_BINARY}"
elif [[ -x "${ROOT_DIR}/bin/mpris-bridge" ]]; then
  BINARY_SOURCE="${ROOT_DIR}/bin/mpris-bridge"
elif [[ -x "${ROOT_DIR}/dist/mpris-bridge" ]]; then
  BINARY_SOURCE="${ROOT_DIR}/dist/mpris-bridge"
else
  echo "Could not find mpris-bridge binary. Expected bin/mpris-bridge or dist/mpris-bridge." >&2
  exit 1
fi

UNIT_SOURCE="${ROOT_DIR}/systemd/${SERVICE_NAME}"
if [[ ! -f "${UNIT_SOURCE}" ]]; then
  echo "Could not find systemd unit at ${UNIT_SOURCE}." >&2
  exit 1
fi

install -Dm755 "${BINARY_SOURCE}" "${BIN_DIR}/mpris-bridge"
install -Dm644 "${UNIT_SOURCE}" "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"

if [[ -f "${ROOT_DIR}/settings.ini" && ! -f "${CONFIG_DIR}/settings.ini" ]]; then
  install -Dm644 "${ROOT_DIR}/settings.ini" "${CONFIG_DIR}/settings.ini"
elif [[ ! -f "${CONFIG_DIR}/settings.ini" ]]; then
  mkdir -p "${CONFIG_DIR}"
  cat > "${CONFIG_DIR}/settings.ini" <<'EOF'
[SERVER]
host = 127.0.0.1
port = 5000
EOF
fi

systemctl --user daemon-reload
systemctl --user enable --now "${SERVICE_NAME}"

echo "Installed ${SERVICE_NAME}."
echo "API: http://127.0.0.1:5000/now-playing"
echo "Status: systemctl --user status ${SERVICE_NAME}"
