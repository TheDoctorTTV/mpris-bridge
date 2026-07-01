#!/usr/bin/env bash
set -euo pipefail

#################
### SETTINGS ###
#################

# Name of the systemd user service installed by this script.
SERVICE_NAME="mpris-bridge.service"
# Directory containing this install script.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"

# Release archives place bin and systemd next to this script.
if [[ -d "${SCRIPT_DIR}/bin" && -d "${SCRIPT_DIR}/systemd" ]]; then
  ROOT_DIR="${SCRIPT_DIR}"
else
  # Source checkouts keep scripts one level below the project root.
  ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd -P)"
fi

# User writable install locations.
BIN_DIR="${XDG_BIN_HOME:-${HOME}/.local/bin}"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
CONFIG_DIR="${CONFIG_HOME}/mpris-bridge"
SYSTEMD_USER_DIR="${CONFIG_HOME}/systemd/user"

########################
### CONFIG HELPERS ###
########################

read_config_port() {
  # Read the configured port so the final message shows the correct API URL.
  local config_file="${CONFIG_DIR}/settings.ini"
  local port=""

  # Parse a simple port entry from settings.ini when available.
  if [[ -f "${config_file}" ]]; then
    port="$(awk -F '=' '
      /^[[:space:]]*port[[:space:]]*=/ {
        gsub(/[[:space:]]/, "", $2)
        print $2
        exit
      }
    ' "${config_file}")"
  fi

  # Fall back to the default port when the value is missing or invalid.
  if [[ "${port}" =~ ^[0-9]+$ ]]; then
    echo "${port}"
  else
    echo "5000"
  fi
}

###########################
### SOURCE DISCOVERY ###
###########################

# Allow callers to point at a custom binary.
if [[ -n "${MPRIS_BRIDGE_BINARY:-}" ]]; then
  BINARY_SOURCE="${MPRIS_BRIDGE_BINARY}"
# Prefer release archive layout.
elif [[ -x "${ROOT_DIR}/bin/mpris-bridge" ]]; then
  BINARY_SOURCE="${ROOT_DIR}/bin/mpris-bridge"
# Fall back to source checkout build output.
elif [[ -x "${ROOT_DIR}/dist/mpris-bridge" ]]; then
  BINARY_SOURCE="${ROOT_DIR}/dist/mpris-bridge"
else
  echo "Could not find mpris-bridge binary. Expected bin/mpris-bridge or dist/mpris-bridge." >&2
  exit 1
fi

# Locate the systemd user unit.
UNIT_SOURCE="${ROOT_DIR}/systemd/${SERVICE_NAME}"
if [[ ! -f "${UNIT_SOURCE}" ]]; then
  echo "Could not find systemd unit at ${UNIT_SOURCE}." >&2
  exit 1
fi

########################
### INSTALL FILES ###
########################

# Install binary and systemd service into user locations.
install -Dm755 "${BINARY_SOURCE}" "${BIN_DIR}/mpris-bridge"
install -Dm644 "${UNIT_SOURCE}" "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"

# Install the default config only when the user does not already have one.
if [[ -f "${ROOT_DIR}/settings.ini" && ! -f "${CONFIG_DIR}/settings.ini" ]]; then
  install -Dm644 "${ROOT_DIR}/settings.ini" "${CONFIG_DIR}/settings.ini"
elif [[ ! -f "${CONFIG_DIR}/settings.ini" ]]; then
  # Create a minimal config when no settings.ini ships with the package.
  mkdir -p "${CONFIG_DIR}"
  cat > "${CONFIG_DIR}/settings.ini" <<'EOF'
[SERVER]
host = 127.0.0.1
port = 5000
EOF
fi

############################
### ENABLE USER SERVICE ###
############################

# Reload systemd user units and start the bridge immediately.
systemctl --user daemon-reload
systemctl --user enable --now "${SERVICE_NAME}"

# Report the URL that should answer after install.
PORT="$(read_config_port)"

echo "Installed ${SERVICE_NAME}."
echo "API: http://127.0.0.1:${PORT}/now-playing"
echo "Status: systemctl --user status ${SERVICE_NAME}"
