# 1Password CLI + MCP Integration Plan for CarefreeSCADA Workflow

**Last Updated:** 2026-06-05  
**Status:** Planning Phase  
**Scope:** Local machine credential & SSH key management

---

## Executive Summary

Your current workflow already references 1Password (SSH keys marked "available in 1Password Carefree DevOps vault"), but stores keys locally on disk (`~/.ssh/`). This plan integrates **1Password CLI**, **local .env mounting**, and **MCP Codex Server** to:

1. **Eliminate local SSH key files** → Load from 1Password on-demand via CLI
2. **Centralize secret provisioning** → Use Environments + local .env for agent/script credentials
3. **Secure credential lookup** → MCP server exposes secrets to agents without plaintext exposure
4. **Reduce attack surface** → No private keys or API credentials stored on disk

---

## Current State Assessment

### SSH Infrastructure
- **Edge nodes** (13 hosts): Use `~/.ssh/carefree-edge-node` key
- **Core servers** (4 hosts): Use `~/.ssh/carefree-core-key` key
- **Management:** SSH config files in `carefree-edge-maintenance/ssh_config` and `carefree-core-maintenance/ssh_config`
- **Already in 1Password:** Comments confirm keys are stored there

### Secrets Currently On Disk
```
~/.ssh/carefree-edge-node        ← SSH private key
~/.ssh/carefree-core-key         ← SSH private key
~/.ssh/config                     ← SSH host configs
~/.ssh/id_ed25519*               ← Personal SSH keys (if any)
```

### Credential Consumers (Agents & Scripts)
1. **Agents** (from `.github/AGENTS.md`):
   - `core-edge-intrusion-watch` — SSH into all core + edge
   - `cve-stack-cve-watch` — SSH connections for CVE triage
   - `emqx-broker-status` — API credentials (Carefree EMQX Cloud)
   - `intrusion-remediation-runbook` — SSH + sudo operations
   - `Sparkplug Monitor` — MQTT client credentials?

2. **Maintenance Scripts** (`carefree-*-maintenance/scripts/`):
   - Audit runners (SSH to hosts)
   - Compliance checkers
   - Health monitors

3. **Ignition Gateway Operations**:
   - Gateway SSH access for deployment/updates
   - Service credentials (Datadog, Splunk, etc.)

---

## Integration Strategy

### Phase 1: SSH Key Management (Foundation)
**Goal:** Replace local SSH keys with 1Password CLI provisioning

#### 1.1 Store SSH Keys in 1Password (Already Done)
- ✅ `Carefree Edge Nodes SSH Key` (private key + passphrase)
- ✅ `Carefree Servers SSH Key` (private key + passphrase)
- Store in: **Carefree DevOps vault** (or create if needed)

#### 1.2 Create 1Password Service Account (Recommended)
For non-interactive automation (agents, CI/CD):
```
Service Account Name: carefree-automation
Vaults: Read access to Carefree DevOps vault
Token: Store in ~/.config/carefree/automation-token (chmod 600)
```

#### 1.3 Update SSH Config to Use 1Password CLI
**New workflow:** SSH keys loaded dynamically instead of static files

**Option A: Shell Plugin (Recommended for Interactive Use)**
- 1Password supports SSH shell plugin (macOS/Linux)
- Automatically loads keys via 1Password agent
- Requires: 1Password 8.10+, CLI 2.20+
- Setup:
  ```bash
  # 1Password automatically injects SSH keys when configured
  # Edit ssh_config entries to remove IdentityFile, use 1Password plugin
  ```

**Option B: Pre-exec Script (Recommended for Agents)**
- Create wrapper that exports SSH key to temp location before SSH call
- Wrapper cleans up after SSH session
- Path: `~/.copilot/bin/ssh-1password-wrapper`

**Option C: SSH Config IdentityCommand (Universal)**
```bash
Host carefree-edge-*
  User carefree
  HostName ...
  IdentityCommand ssh-add -L | grep -i "carefree-edge" || (op read "op://Carefree DevOps/Carefree Edge Nodes SSH Key/private key" | ssh-add -)
```

### Phase 2: Environment-Based Secret Provisioning (Scaling)
**Goal:** Provide agents/scripts with credentials via .env mounting

#### 2.1 Create 1Password Environments
```
Environment 1: carefree-automation
├─ Secrets:
│  ├─ CAREFREE_SSH_KEY_EDGE (reference to private key)
│  ├─ CAREFREE_SSH_KEY_CORE (reference to private key)
│  ├─ EMQX_API_KEY
│  ├─ EMQX_API_SECRET
│  ├─ DATADOG_API_KEY
│  ├─ IGNITION_GATEWAY_USER
│  ├─ IGNITION_GATEWAY_PASSWORD
│  └─ [other service credentials]
```

#### 2.2 Mount Local .env File
**Desktop App UI:**
1. 1Password → Settings → Environments → carefree-automation
2. Destinations tab → Configure destination for Local .env file
3. Mount at: `~/.config/carefree/.env.1password`
4. 1Password automatically remounts on restart

**File Location:** `~/.config/carefree/.env.1password`  
**Git Status:** Not tracked (FIFO named pipe, safe)

#### 2.3 Load in Agent/Script Workflows
```python
# Python: Load via python-dotenv
from dotenv import load_dotenv
import os

load_dotenv('~/.config/carefree/.env.1password')
api_key = os.getenv('EMQX_API_KEY')
```

```bash
# Bash: Source the .env file
set -a
source ~/.config/carefree/.env.1password
set +a
ssh-command $CAREFREE_SSH_KEY_EDGE
```

### Phase 3: MCP Codex Server Integration (Agent-First)
**Goal:** Agents access secrets without exposing them to stdout/logs

#### 3.1 What is MCP Codex Server?
- Model Context Protocol server that exposes 1Password Environments
- Allows AI agents (Claude in VS Code/Copilot) to lookup secrets by name
- **Critical:** Never exposes secrets directly; only returns them to agent context
- No secrets appear in terminal, logs, or file system

#### 3.2 Setup MCP Server
**Installation:**
```bash
# Install 1Password CLI (if not already installed)
brew install 1password-cli

# Enable MCP Codex in 1Password
# Desktop app → Settings → Developer → MCP Codex Server
# Authorize and enable
```

**VS Code Integration:**
Add to `~/.copilot/settings/mcp-servers.json` (or relevant config):
```json
{
  "servers": {
    "1password": {
      "command": "op",
      "args": ["mcp-codex"],
      "env": {}
    }
  }
}
```

#### 3.3 Agent Usage Pattern
In `AGENTS.md` or agent definitions, document:
```
# Within Agent Tasks
When agent needs SSH credentials:
1. Query MCP: "Get SSH key for carefree-edge-oden-wtp"
2. MCP returns secret to agent context (not exposed to user)
3. Agent uses secret for SSH operation
4. No credential logging, no disk writes
```

**Example Agent Instruction:**
```markdown
### Credential Handling
- Use 1Password MCP to query SSH keys: `op://Carefree DevOps/Carefree Edge Nodes SSH Key`
- Never log or echo credentials
- Always run SSH commands with `-o StrictHostKeyChecking=accept-new`
- Clean up temporary files: `/tmp/carefree-*`
```

---

## Implementation Roadmap

### Week 1: Foundation Setup
- [ ] **Task 1.1:** Verify SSH keys stored in 1Password (confirm names/vault)
- [ ] **Task 1.2:** Create or elevate Service Account for automation
- [ ] **Task 1.3:** Install 1Password CLI v2.20+ on local machine
- [ ] **Task 1.4:** Create instruction file: `1password-credentials.instructions.md`

### Week 2: SSH Wrapper Implementation
- [ ] **Task 2.1:** Create `~/.copilot/bin/ssh-1password-wrapper` script
- [ ] **Task 2.2:** Update SSH config in `carefree-edge-maintenance/ssh_config`
- [ ] **Task 2.3:** Test SSH connections to edge nodes (manual)
- [ ] **Task 2.4:** Test SSH connections to core servers (manual)
- [ ] **Task 2.5:** Remove or archive local SSH key files (after validation)

### Week 3: Environment Setup
- [ ] **Task 3.1:** Create `carefree-automation` Environment in 1Password
- [ ] **Task 3.2:** Add secrets/references to Environment
- [ ] **Task 3.3:** Mount local .env file via Desktop app
- [ ] **Task 3.4:** Test .env loading in Python script
- [ ] **Task 3.5:** Test .env loading in shell script

### Week 4: Agent Integration
- [ ] **Task 4.1:** Enable MCP Codex Server in 1Password app
- [ ] **Task 4.2:** Configure MCP server for agents
- [ ] **Task 4.3:** Update agent definitions with credential handling patterns
- [ ] **Task 4.4:** Test agents with MCP credential queries (test only)
- [ ] **Task 4.5:** Document MCP limitations (concurrent access, offline behavior)

### Week 5: Hardening & Documentation
- [ ] **Task 5.1:** Write technician KB page: "1Password Credential Management"
- [ ] **Task 5.2:** Create runbook for emergency credential recovery
- [ ] **Task 5.3:** Audit audit-reports/ for hardcoded credentials
- [ ] **Task 5.4:** Update AGENTS.md with credential expectations
- [ ] **Task 5.5:** Security review & testing

---

## Files to Create/Modify

### New Files
1. **`~/.copilot/instructions/1password-credentials.instructions.md`**
   - When to use 1Password CLI vs .env vs MCP
   - Credential handling best practices
   - Security checklist

2. **`~/.copilot/bin/ssh-1password-wrapper`**
   - Python or shell script
   - Loads SSH key from 1Password
   - Calls SSH with dynamic key injection
   - Cleans up temp files

3. **`~/.copilot/templates/1password-dotenv-loader.py`**
   - Reusable Python snippet for .env loading
   - Error handling, logging, timeout support

4. **`~/.copilot/templates/1password-dotenv-loader.sh`**
   - Reusable shell snippet for .env sourcing
   - Portable across bash/zsh

5. **`knowledge-base/technician-kb/Security/1Password-Credential-Management.md`**
   - Obsidian vault page documenting the flow
   - Wikilinks to related pages
   - Troubleshooting guide

### Modified Files
1. **`carefree-edge-maintenance/ssh_config`**
   - Update IdentityFile references or use IdentityCommand
   - Add comments explaining 1Password integration

2. **`carefree-core-maintenance/ssh_config`**
   - Same as above

3. **`AGENTS.md`**
   - Document credential expectations for agents
   - Explain MCP Codex usage pattern
   - Link to new 1password-credentials instruction

4. **`.gitignore` (if not already)**
   - Ensure `~/.ssh/carefree-*` keys are ignored if they exist
   - Ensure `.env.1password` is ignored

---

## Security Considerations

### Threat Model
| Threat | Current Risk | Mitigated By |
|--------|-------------|--------------|
| SSH keys on disk | **HIGH** — plaintext private keys | 1Password vault + CLI provisioning |
| Leaked credentials in logs | **MEDIUM** — agents might echo keys | MCP Codex (agent-only access) |
| Concurrent .env access conflicts | **MEDIUM** — multiple tools reading .env | 1Password named-pipe FIFO handling |
| Offline credential access | **LOW** — not always needed | 1Password local cache (synced) |
| Service account token compromise | **HIGH** — automation token in ~/.config/ | File permissions (600), vault audit logs |

### Best Practices
1. **Service Account Token Security**
   - File permissions: `chmod 600 ~/.config/carefree/automation-token`
   - Store in encrypted location (consider macOS Keychain integration)
   - Rotate quarterly

2. **SSH Key Passphrase**
   - Store passphrase in 1Password (separate from key)
   - 1Password CLI can use passphrase automatically

3. **Audit Trail**
   - 1Password logs all credential access
   - Monitor "Carefree DevOps vault" access logs weekly
   - Set up alerts for unusual SSH key usage

4. **Fallback / Emergency Access**
   - Document manual SSH key recovery procedure
   - Keep encrypted backup of SSH keys (separate from 1Password)
   - Test recovery process quarterly

---

## Limitations & Trade-offs

### 1Password Local .env File
| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| **Beta feature** (Mac/Linux only) | Risk of changes | Check release notes before updates |
| **FIFO named pipe** (not real file) | IDEs can't watch for changes | Disable file watching in dev tools (e.g., Vite) |
| **Concurrent access conflicts** | Multiple processes → first wins | Queue operations; use locks in scripts |
| **Offline behavior** | Outdated secrets while offline | Test offline scenarios; manual refresh |
| **1Password must be unlocked** | Requires biometric unlock | Acceptable for local development |

### 1Password CLI Performance
- First call takes ~200ms (1Password agent startup)
- Subsequent calls ~100ms (cached agent)
- Solution: Batch calls, cache results during session

### MCP Codex Server
- Secrets only exposed to agent context (not logs/stdout)
- Cannot be used by non-agent scripts directly
- Requires 1Password Desktop app to be running
- No programmatic secret retrieval outside of agent

---

## Decision Matrix: Which Integration to Use?

| Use Case | Recommended | Reason |
|----------|------------|--------|
| **Interactive SSH** | Shell Plugin or IdentityCommand | User-friendly, biometric unlock |
| **Agent SSH operations** | SSH wrapper + MCP queries | Secure, no plaintext in logs |
| **Automated scripts** | .env mounting + python-dotenv | Simple, works offline (cached) |
| **CI/CD pipelines** | Service Account + CLI commands | Non-interactive, audit-logged |
| **Emergency/fallback** | Manual SSH key recovery + docs | Keep manual process tested |

---

## Next Steps

1. **Review this plan** with your security/ops team
2. **Choose integration approach** (recommend: SSH wrapper + .env + MCP layered)
3. **Schedule implementation** (4-5 weeks, low-risk changes)
4. **Test in staging** before deploying to agents
5. **Update AGENTS.md and KB** with new credential handling

---

## References

- **1Password CLI:** https://www.1password.dev/cli
- **Local .env Mounting:** https://www.1password.dev/environments/local-env-file
- **MCP Codex Server:** https://www.1password.dev/environments/mcp-codex-server
- **Shell Plugins:** https://www.1password.dev/cli/shell-plugins
- **Best Practices:** https://www.1password.dev/cli/best-practices

---

## Appendix: Example Implementation Snippets

### A. SSH Wrapper Script (Python)
```python
#!/usr/bin/env python3
# ~/.copilot/bin/ssh-1password-wrapper
# Usage: ssh-1password-wrapper [SSH_ARGS]

import subprocess
import sys
import os
import tempfile
from pathlib import Path

def get_ssh_key(key_name: str) -> bytes:
    """Fetch SSH key from 1Password CLI"""
    result = subprocess.run(
        ['op', 'read', f'op://Carefree DevOps/{key_name}/private key'],
        capture_output=True,
        check=True
    )
    return result.stdout

def main():
    key_name = os.environ.get('CAREFREE_SSH_KEY_SOURCE', 'Carefree Edge Nodes SSH Key')
    
    # Get key from 1Password
    key_data = get_ssh_key(key_name)
    
    # Write to temp file (mode 600)
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pem') as tmp:
        tmp.write(key_data)
        tmp_path = tmp.name
    os.chmod(tmp_path, 0o600)
    
    try:
        # Inject into SSH call
        ssh_cmd = ['ssh', '-i', tmp_path] + sys.argv[1:]
        subprocess.run(ssh_cmd, check=False)
    finally:
        os.unlink(tmp_path)

if __name__ == '__main__':
    main()
```

### B. Shell .env Loader
```bash
#!/bin/bash
# ~/.copilot/templates/1password-dotenv-loader.sh

# Load secrets from 1Password mounted .env
ENV_FILE="${HOME}/.config/carefree/.env.1password"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: 1Password .env file not found at $ENV_FILE"
    echo "Check: Is 1Password running? Is environment mounted?"
    exit 1
fi

# Load with error handling
set -a
if ! source "$ENV_FILE"; then
    echo "ERROR: Failed to source 1Password .env file"
    exit 1
fi
set +a

echo "✓ Loaded credentials from 1Password Environments"
```

### C. Agent Credential Pattern (Instruction)
```markdown
## Credential Lookup with 1Password MCP

When your agent needs to connect to a Carefree resource:

1. **Query 1Password MCP Server** (within agent context):
   ```
   Retrieve secret: op://Carefree DevOps/Carefree Edge Nodes SSH Key/private key
   ```

2. **MCP returns secret** to agent context (not visible to user)

3. **Agent uses secret** for SSH/API operations

4. **No credential logging** — secrets never appear in logs, terminal, or files

### Example Flow
- User: "Check intrusion watch on carefree-core-data"
- Agent queries: "Get SSH key for core servers"
- MCP returns key to agent context
- Agent SSHes to carefree-core-data (key never logged)
- Agent returns findings to user (no credentials exposed)
```

---

**End of Plan**
