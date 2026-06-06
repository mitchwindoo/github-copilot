---
description: Credential management using 1Password CLI, local .env mounting, and MCP server for SSH, API keys, and service credentials.
applyTo: "**"
---

# 1Password Credential Management Instruction

## When to Use This

- **Accessing SSH hosts** through the 1Password SSH Agent
- **Reading secrets** with the 1Password CLI when an explicit value is needed
- **Running agents** that need credentials without exposing secrets
- **Provisioning automation scripts** with service accounts or mounted env files
- **Emergency credential recovery** when 1Password is unavailable

## Preferred Order

1. Use the 1Password SSH Agent for SSH keys whenever possible.
2. Use the 1Password CLI for explicit reads, lists, and item metadata.
3. Use the 1Password MCP server when an agent needs a secret in context only.
4. Use locally mounted `.env` files for scripts that need environment variables.

---

## Quick Start

### For SSH Connections
```bash
# Preferred setup:
# - ~/.config/1Password/ssh/agent.toml allows the key item or vault
# - ~/.ssh/config includes ~/.ssh/1Password/config
# - SSH uses the 1Password agent socket automatically

# Validate the resolved host settings
ssh -G <host-alias>

# List keys currently exposed by the 1Password SSH agent
SSH_AUTH_SOCK=~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock ssh-add -l

# Direct CLI approach only when you must materialize a key for a one-off workflow:
op read "op://<vault>/<item>/private key"
```

### For Scripts & Automation
```python
# Load credentials from locally-mounted 1Password .env
from dotenv import load_dotenv
import os

load_dotenv('~/.config/carefree/.env.1password')
api_key = os.getenv('EMQX_API_KEY')
```

### For Agents (Copilot, Subagents)
- Query 1Password MCP for the secret or item metadata.
- Keep the secret in agent context only; never print it, write it to disk, or echo it back to the user.
- If a script needs the value directly, prefer the CLI or the mounted `.env` path instead of MCP.

---

## Architecture Layers

### Layer 1: SSH Key Provisioning (Foundation)
**When:** Every SSH connection  
**How:** 1Password CLI or shell plugin  
**Keys stored in:** `1Password → Carefree DevOps vault`  
**Files on disk:** None (FIFO named pipe or CLI process memory)

**Available SSH Keys:**
- `Carefree Edge Nodes SSH Key` → ~/.ssh/carefree-edge-node
- `Carefree Servers SSH Key` → ~/.ssh/carefree-core-key
- Both keys have passphrases stored in 1Password

**Local policy files:**
- `~/.config/1Password/ssh/agent.toml` controls which vaults and items the agent can offer
- `~/.ssh/1Password/config` is the generated include file for SSH client config
- `~/.ssh/config` should include `~/.ssh/1Password/config` and define host aliases

### Layer 2: Environment-Based Secrets (.env)
**When:** Scripts, automation, testing  
**How:** 1Password Environments + local .env mounting  
**Mounted at:** `~/.config/carefree/.env.1password`  
**How it works:** 1Password Desktop app mounts secrets as FIFO named pipe (not real file)

**Available Secrets in carefree-automation Environment:**
- `CAREFREE_SSH_KEY_EDGE` (reference to private key)
- `CAREFREE_SSH_KEY_CORE` (reference to private key)
- `EMQX_API_KEY`, `EMQX_API_SECRET`
- `DATADOG_API_KEY`
- `IGNITION_GATEWAY_USER`, `IGNITION_GATEWAY_PASSWORD`
- [Add more as needed]

### Layer 3: Agent Credential Lookup (MCP)
**When:** Copilot agents run SSH or API operations  
**How:** 1Password MCP Codex server  
**Process:** Agent queries MCP → returns secret to agent context (not exposed)  
**Never:** Credentials appear in logs, terminal, or file system

**Agent Instruction Pattern:**
```markdown
# For agents that need SSH:
Use 1Password MCP to query credentials:
Query: op://Carefree DevOps/Carefree Edge Nodes SSH Key
Result: Secret passed to agent context only (never logged)
```

---

## Detailed Workflows

### Workflow 1: SSH to Edge Node (Interactive)
```bash
# 1. 1Password shell plugin active (or IdentityCommand configured)
# 2. You run:
ssh carefree-edge-oden-wtp

# 3. What happens:
#    a) SSH reads config → IdentityCommand
#    b) IdentityCommand calls 1Password CLI
#    c) 1Password prompts for biometric unlock (if locked)
#    d) 1Password returns SSH key to SSH process
#    e) SSH authenticates
#    f) Key never stored on disk

# 4. No stored key needed locally!
```

### Workflow 2: Script Using .env Credentials
```bash
#!/bin/bash
# In a maintenance script

# 1. Load 1Password .env (already mounted by Desktop app)
set -a
source ~/.config/carefree/.env.1password
set +a

# 2. Use credentials
API_KEY=$EMQX_API_KEY
curl -H "Authorization: Bearer $API_KEY" \
  https://broker.emqx.cloud/api/v5/stats

# 3. Variables cleaned up when script exits (not persistent)
```

### Workflow 3: Agent Running SSH Operation
```
User: "Check intrusion watch on carefree-core-data"
↓
Agent loads: 1Password MCP or SSH Agent context as needed
↓
Agent needs: SSH key for core-data
↓
Agent verifies: agent.toml allows the key and ssh config targets the host
↓
Agent runs: ssh -i /dev/stdin carefree@100.67.244.157 "sudo ..."
↓
Agent reports: "Findings: [intrusion data]" (no credentials exposed)
```

### Workflow 4: Emergency Credential Recovery
**When:** 1Password unavailable, offline, or compromised  
**How:** Manual recovery procedure (see Fallback section below)

---

## File Locations & Permissions

| Path | Purpose | Permissions | Managed By |
|------|---------|-------------|-----------|
| `~/.config/carefree/automation-token` | Service account token | `600` (read/write owner only) | Manual (store in Keychain?) |
| `~/.config/carefree/.env.1password` | Mounted 1Password Environments | FIFO (not real file) | 1Password Desktop app |
| `~/.ssh/carefree-edge-node` | **ARCHIVED** (was local key) | N/A (removed) | Removed after migration |
| `~/.ssh/carefree-core-key` | **ARCHIVED** (was local key) | N/A (removed) | Removed after migration |
| `carefree-edge-maintenance/ssh_config` | SSH host configuration | `644` (readable by all) | Git-tracked |
| `carefree-core-maintenance/ssh_config` | SSH host configuration | `644` (readable by all) | Git-tracked |

---

## Security Checklist

### Before Going Live
- [ ] Verify SSH keys exist in 1Password ("Carefree DevOps" vault)
- [ ] Test SSH connection to one edge node: `ssh carefree-edge-oden-wtp whoami`
- [ ] Test SSH connection to one core server: `ssh carefree-core-data whoami`
- [ ] Test .env loading: `python3 -c "from dotenv import load_dotenv; load_dotenv('~/.config/carefree/.env.1password'); import os; print('EMQX_API_KEY:', os.getenv('EMQX_API_KEY', 'NOT SET'))"`
- [ ] Remove old SSH key files: `rm -f ~/.ssh/carefree-edge-node ~/.ssh/carefree-core-key`
- [ ] Verify git status: `git status` (should not show key files)
- [ ] Enable 1Password vault audit logging for "Carefree DevOps"
- [ ] Test emergency recovery procedure (manual SSH fallback)

### Ongoing Hardening
- [ ] Weekly: Review 1Password "Carefree DevOps" vault access logs
- [ ] Monthly: Rotate service account token (if using automation)
- [ ] Quarterly: Test manual SSH key recovery procedure
- [ ] Quarterly: Audit scripts for hardcoded credentials (grep audit-reports/)
- [ ] Annually: Rotate all SSH key passphrases

### Monitoring & Alerts
- Set up 1Password alerts for:
  - Vault access from unexpected IPs
  - Multiple failed unlock attempts
  - SSH key export/access (if 1Password supports this)
- Monitor SSH logs on edge/core servers for:
  - Unusual access patterns
  - Failed authentication attempts
  - New SSH keys added

---

## Fallback: Emergency Credential Recovery

### Scenario 1: 1Password Desktop App Crashes
**Status:** SSH still works if you were already connected  
**Fix:** Restart 1Password Desktop app
```bash
# Restart 1Password
killall "1Password 7"  # or your version
open -a "1Password 7"
# Re-authenticate with biometric unlock
```

### Scenario 2: 1Password Offline (No Internet)
**Status:** SSH keys cached locally by 1Password CLI  
**Behavior:** SSH may still work if CLI cache is warm  
**Test offline:** Try SSH; if it fails, restart 1Password and retry

### Scenario 3: 1Password SSH Agent Config Does Not Expose a Key
**Status:** The key exists in 1Password, but SSH cannot use it yet  
**Fix:** Add the key or vault to `~/.config/1Password/ssh/agent.toml`, then re-run `ssh -G <host-alias>` and `ssh-add -l`

### Scenario 4: 1Password Service Account Token Expired
**Status:** Automation scripts fail  
**Fix:** Regenerate service account token in 1Password
```bash
# 1. Log in to 1Password account (web or app)
# 2. Generate new service account token
# 3. Update: ~/.config/carefree/automation-token
# 4. Set permissions: chmod 600 ~/.config/carefree/automation-token
```

### Scenario 5: Lost Access to 1Password (Account Compromised)
**Status:** CRITICAL — credential exposure risk  
**Immediate Actions:**
1. Notify your security team
2. Revoke all SSH keys in 1Password (rotate on all hosts)
3. Disable service account token
4. Check server SSH logs for unauthorized access
5. Consider disabling NetBird VPN temporarily
6. Change 1Password master password
7. Enable 1Password emergency access procedure

**Recovery:**
- Use emergency access code (if enabled in 1Password)
- Manual SSH key recovery from encrypted backup (if available)
- Contact 1Password support

### Scenario 6: Manual SSH Connection (Last Resort)
**When:** All automation fails and you need direct SSH  
**If local SSH key still exists:**
```bash
ssh -i ~/.ssh/carefree-edge-node carefree@100.67.6.63
```
**If no local key:**
- Restore from encrypted backup (if available)
- Contact infrastructure team for emergency access
- Use shared bastion/jump host (if available)

---

## Limitations & Workarounds

| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| **FIFO not a real file** — IDEs can't watch .env for changes | Dev tools (Vite, etc.) restart on FIFO events | Disable .env watching in dev tools |
| **Concurrent .env reads** — Multiple processes may conflict | Scripts run in parallel → credential access fails | Queue operations; add locks or retry logic |
| **1Password must be unlocked** — Requires biometric auth | First SSH call waits for unlock | Unlock 1Password once per session; auto-lock time is configurable |
| **CLI response time** — ~100-200ms per call | Slow for many sequential SSH operations | Batch operations; use SSH multiplexing (-M) |
| **Offline behavior** — Outdated secrets while offline | Changes made on other devices not reflected immediately | Test offline scenarios; manually refresh when online |
| **MCP context-only** — Agents can't export secrets for scripts | Scripts can't use MCP directly | Use .env or service account token instead |

---

## Validation Checklist

- Confirm `~/.config/1Password/ssh/agent.toml` includes the vault or item you need.
- Confirm `~/.ssh/config` includes `~/.ssh/1Password/config`.
- Confirm host aliases resolve with `ssh -G <host-alias>`.
- Confirm the agent can see the key with `ssh-add -l`.
- Confirm CLI access with `op item get`, `op vault list`, or `op read` as appropriate.
- Use MCP only when the secret should stay in agent context.

---

## Credential Inventory

### SSH Keys (in 1Password)
```
Vault: Carefree DevOps
Items:
├─ Carefree Edge Nodes SSH Key
│  ├─ Private key (multi-line PEM)
│  ├─ Passphrase
│  └─ Username: carefree
│  └─ Note: All edge nodes (carefree-edge-*)
├─ Carefree Servers SSH Key
│  ├─ Private key (multi-line PEM)
│  ├─ Passphrase
│  └─ Username: carefree
│  └─ Note: All core servers (carefree-core-*)
```

### API Credentials (in carefree-automation Environment)
```
Environment: carefree-automation
Secrets:
├─ EMQX_API_KEY (from EMQX Cloud portal)
├─ EMQX_API_SECRET (from EMQX Cloud portal)
├─ DATADOG_API_KEY (from Datadog org)
├─ IGNITION_GATEWAY_USER (carefree account on gateways)
├─ IGNITION_GATEWAY_PASSWORD (secure password)
```

### Service Accounts (for Automation)
```
Name: carefree-automation
Type: 1Password Service Account
Vaults: Carefree DevOps (read), carefree-automation (read)
Token: ~/.config/carefree/automation-token
Used by: CI/CD, scheduled scripts, agent runners
```

---

## Related Documentation

- **Local .env Mounting:** https://www.1password.dev/environments/local-env-file
- **1Password CLI:** https://www.1password.dev/cli
- **MCP Codex Server:** https://www.1password.dev/environments/mcp-codex-server
- **Shell Plugins:** https://www.1password.dev/cli/shell-plugins
- **Technician KB:** [[1Password Credential Management]] (Obsidian vault)

---

## Glossary

- **1Password Environment:** A collection of secrets (references) that can be mounted as a .env file or queried via MCP
- **Service Account:** Non-interactive 1Password account with limited vault access (for automation)
- **MCP (Model Context Protocol):** Codex server that exposes 1Password secrets to AI agents without plaintext exposure
- **FIFO Named Pipe:** Special file type used by 1Password to mount .env files securely (not stored on disk)
- **Shell Plugin:** 1Password feature that injects SSH keys into SSH command automatically
- **Secret Reference:** A pointer to a secret in 1Password (e.g., `op://vault/item/field`)

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-06-05 | Initial instruction created | (User) |
| TBD | SSH wrapper implemented | TBD |
| TBD | .env mounting tested | TBD |
| TBD | MCP integration verified | TBD |
