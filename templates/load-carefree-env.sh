#!/usr/bin/env bash
# load-carefree-env.sh — Source the 1Password-mounted .env for Carefree automation
#
# Usage (source this file, do not execute it):
#   source ~/.copilot/templates/load-carefree-env.sh
#
# Prerequisites:
#   1. 1Password Desktop app must be running and unlocked
#   2. Create a "carefree-automation" Environment in 1Password
#   3. In 1Password → Environments → carefree-automation → Destinations:
#      Mount local .env at: ~/.config/carefree/.env.1password
#
# After sourcing, the following variables are available (if configured in the Environment):
#   EMQX_API_KEY, EMQX_API_SECRET
#   DATADOG_API_KEY
#   IGNITION_GATEWAY_USER, IGNITION_GATEWAY_PASSWORD
#   CAREFREE_SSH_KEY_EDGE, CAREFREE_SSH_KEY_CORE  (optional)

ENV_FILE="${HOME}/.config/carefree/.env.1password"

# Check for the FIFO pipe (normal) or regular file (fallback)
if [[ ! -p "${ENV_FILE}" ]] && [[ ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: 1Password .env not found at ${ENV_FILE}" >&2
    echo "" >&2
    echo "To mount it:" >&2
    echo "  1. Open 1Password Desktop app" >&2
    echo "  2. Settings → Environments → carefree-automation" >&2
    echo "  3. Destinations tab → Configure destination for Local .env file" >&2
    echo "  4. Set path: ${HOME}/.config/carefree/.env.1password" >&2
    echo "  5. Select Mount .env file" >&2
    return 1 2>/dev/null || exit 1
fi

# Source the .env — 1Password will prompt for authorization on first read
set -a
# shellcheck source=/dev/null
if ! source "${ENV_FILE}" 2>/dev/null; then
    echo "ERROR: Failed to source 1Password .env — is 1Password unlocked?" >&2
    return 1 2>/dev/null || exit 1
fi
set +a

echo "Carefree credentials loaded from 1Password Environments"
