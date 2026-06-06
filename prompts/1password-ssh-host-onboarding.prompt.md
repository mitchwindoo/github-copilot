---
name: 1password-ssh-host-onboarding
description: "Use when adding a new SSH host that should authenticate with a 1Password SSH key. Trigger phrases: add ssh host, onboard ssh target, use 1password key for host, update agent.toml for ssh host, configure ssh alias."
mode: ask
model: GPT-5.3-Codex
---

Onboard one SSH host using a 1Password-managed SSH key with the smallest safe change set.

Inputs to collect or confirm:
1. Host alias (example: wilder-trixie)
2. HostName/IP
3. SSH username
4. 1Password vault name
5. 1Password item name (SSH key item)

Procedure:
1. Verify or add allowlist entry in ~/.config/1Password/ssh/agent.toml:
   [[ssh-keys]]
   item = "<item-name>"
   vault = "<vault-name>"
2. Ensure ~/.ssh/config contains:
   Include ~/.ssh/1Password/config
3. Add/update host block in ~/.ssh/config with:
   - Host
   - HostName
   - User
   - StrictHostKeyChecking accept-new
4. Validate config resolution:
   ssh -G <host-alias>
5. Validate key visibility:
   SSH_AUTH_SOCK=~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock ssh-add -l
6. Validate login non-interactively:
   ssh -o BatchMode=yes <host-alias> whoami

Safety:
- Never print secret values.
- Never export private keys to files unless explicitly requested.
- Prefer item-scoped allowlisting over vault-wide allowlisting.

Response template:
1. Changes made
2. Files touched
3. Validation results
4. Follow-up action if any check fails
