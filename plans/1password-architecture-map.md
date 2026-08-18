# 1Password Integration Architecture Map

## Current State vs. Target State

```
┌─────────────────────────────────────────────────────────────────┐
│ CURRENT STATE: Keys on Disk (Risk)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ~/.ssh/carefree-edge-node    [PLAINTEXT KEY ON DISK]          │
│  ~/.ssh/carefree-core-key     [PLAINTEXT KEY ON DISK]          │
│                                                                 │
│  SSH Config → Local Key File → SSH to Host                     │
│                                                                 │
│  Problems:                                                      │
│  • Plaintext private keys vulnerable if disk compromised       │
│  • Developers may copy keys locally                            │
│  • No audit trail of who uses keys                             │
│  • Backup procedures expose secrets                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ⬇
                        (MIGRATE)
                              ⬇
┌─────────────────────────────────────────────────────────────────┐
│ TARGET STATE: Zero Secrets on Disk                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1Password Desktop App (Biometric Unlock)                      │
│  ├─ Carefree DevOps Vault                                      │
│  │  ├─ Carefree Edge Nodes SSH Key [ENCRYPTED VAULT]          │
│  │  └─ Carefree Servers SSH Key [ENCRYPTED VAULT]             │
│  │                                                             │
│  └─ carefree-automation Environment [.env MOUNT]              │
│     ├─ EMQX_API_KEY (reference)                              │
│     ├─ DATADOG_API_KEY (reference)                           │
│     └─ Service credentials (encrypted)                       │
│                                                             │
│  Access Methods:                                             │
│  1. Shell Plugin → SSH key injected to SSH process           │
│  2. CLI wrapper → SSH key via subprocess                     │
│  3. .env mounting → Secrets via FIFO named pipe             │
│  4. MCP Codex → Agent queries (no plaintext exposure)       │
│                                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Credential Flow Diagram

```
USER REQUESTS SSH OPERATION
                │
                ├────────────────────────────────────────────┐
                │                                            │
           INTERACTIVE                              AUTOMATED/AGENT
                │                                            │
                ├──────────────────┬───────────────────────┬─┴──────────┐
                │                  │                       │            │
         IdentityCommand      SSH Wrapper              .env mount     MCP Query
         (Shell Plugin)       (Python/Bash)           (Script/App)    (Agent)
                │                  │                       │            │
                ├──────────────┬───┴───┬──────────────┬────┴──┬────────┘
                │              │       │              │       │
         1Password CLI loads key from vault
                │              │       │              │       │
         Returns to:      SSH process  Temp file    .env FIFO Agent context
                │              │       │              │       │
         SSH authenticates to host
                │
         Connection established
                │
         SSH command executed
                │
         Credential cleaned up (no disk traces)
```

---

## Integration Layer Architecture

```
┌────────────────────────────────────────────────────────────────┐
│ LAYER 3: Agents & Automation (MCP + CLI)                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  core-edge-intrusion-watch ──┐                                │
│  cve-stack-cve-watch         ├─→ Query MCP Codex Server       │
│  emqx-broker-status          │    for credentials (no logs)    │
│  intrusion-remediation-runbook─→  "Get SSH key for X"         │
│                                   ↓                            │
│                                [AGENT CONTEXT]                │
│                                (hidden from user)             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                         ⬆
                    (MCP Protocol)
                         ⬆
┌────────────────────────────────────────────────────────────────┐
│ LAYER 2: Environment Provisioning (.env + CLI)                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  carefree-automation Environment (1Password)                  │
│  ├─ Mounted at: ~/.config/carefree/.env.1password            │
│  ├─ Type: FIFO named pipe (not real file)                    │
│  └─ Access: python-dotenv, bash source, MCP                  │
│                                                                │
│  Secrets available:                                           │
│  ├─ EMQX_API_KEY                                              │
│  ├─ DATADOG_API_KEY                                           │
│  ├─ IGNITION credentials                                      │
│  └─ SSH keys (optional)                                       │
│                                                                │
│  Used by:                                                     │
│  ├─ Python scripts (dotenv library)                           │
│  ├─ Shell scripts (source command)                            │
│  ├─ Docker Compose (built-in .env support)                   │
│  └─ Automation runners                                        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                         ⬆
              (1Password Desktop App)
                         ⬆
┌────────────────────────────────────────────────────────────────┐
│ LAYER 1: SSH Key Management (Shell Plugin or CLI)             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1Password Desktop App (Unlocked)                             │
│  ├─ Carefree DevOps Vault                                    │
│  │  ├─ Carefree Edge Nodes SSH Key                           │
│  │  ├─ Carefree Servers SSH Key                              │
│  │  └─ [Other credentials]                                   │
│  │                                                            │
│  └─ Access Methods:                                          │
│     ├─ Shell Plugin → SSH process                            │
│     ├─ 1Password CLI → stdout/pipe                           │
│     └─ Local caching (for offline)                           │
│                                                            │
│  Result: SSH connections to:                              │
│  ├─ carefree-edge-* (13 nodes)                           │
│  ├─ carefree-core-* (4 servers)                          │
│  └─ Ignition gateways                                    │
│                                                            │
└────────────────────────────────────────────────────────────────┘
                         ⬆
                  (Biometric Unlock)
                         ⬆
            1Password Local Vault (Encrypted)
```

---

## Decision Tree: Which Integration Path?

```
START: Need to access credentials
│
├─ "I want to SSH interactively"
│  │
│  └─→ SSH SHELL PLUGIN PATH
│      Setup: 1Password shell plugin on macOS/Linux
│      Usage: ssh carefree-edge-oden-wtp
│      Auth: Biometric unlock (first call only)
│      Result: Key injected to SSH process
│      Pros: Seamless, no scripts needed
│      Cons: 1Password must be running
│
├─ "I'm writing a script that needs SSH"
│  │
│  ├─ "For local testing/development"
│  │  └─→ SSH WRAPPER PATH
│  │      Setup: ~/.copilot/bin/ssh-1password-wrapper
│  │      Usage: ssh-1password-wrapper carefree@host
│  │      Auth: 1Password CLI prompts biometric
│  │      Result: Key passed to SSH process
│  │      Pros: Works with any SSH command
│  │      Cons: Manual wrapper calls
│  │
│  └─ "For production/automation"
│     └─→ SERVICE ACCOUNT + CLI PATH
│         Setup: 1Password service account token
│         Usage: op read "op://vault/item/field"
│         Auth: Non-interactive (token-based)
│         Result: Credential returned to script
│         Pros: Fully automated, audit-logged
│         Cons: Token management overhead
│
├─ "I need API credentials in my script"
│  │
│  └─→ .ENV MOUNTING PATH
│      Setup: carefree-automation Environment + .env mount
│      Usage: source ~/.config/carefree/.env.1password
│      Auth: 1Password app handles mounting
│      Result: Variables available in script
│      Pros: Standard .env workflow
│      Cons: Beta feature, FIFO limitations
│
├─ "I'm an agent/automation running SSH"
│  │
│  └─→ MCP CODEX PATH
│      Setup: 1Password MCP server for agents
│      Usage: Query MCP for "op://Carefree DevOps/SSH Key"
│      Auth: 1Password unlocked in background
│      Result: Secret to agent context (no logging)
│      Pros: Secure, no credential exposure
│      Cons: Requires 1Password running, MCP setup
│
└─ FALLBACK: "1Password is down, I need SSH NOW"
   └─→ MANUAL EMERGENCY RECOVERY
       Method: Restore SSH key from encrypted backup
       Usage: ssh -i /backup/carefree-edge-node carefree@host
       Result: SSH connection (no 1Password needed)
       Pros: Last resort works
       Cons: Requires pre-staging backup
```

---

## Implementation Timeline & Responsibility

```
WEEK 1: Foundation
├─ Task: Verify SSH keys in 1Password
│  Owner: User
│  Gate: Confirm vault exists, keys present
│
├─ Task: Install 1Password CLI
│  Owner: User
│  Command: brew install 1password-cli
│  Gate: op --version shows v2.20+
│
└─ Task: Create instruction file (this document)
   Owner: Copilot (DONE ✓)
   Gate: Added to ~/.copilot/instructions/

WEEK 2: SSH Integration
├─ Task: Implement SSH wrapper
│  Owner: Copilot
│  Output: ~/.copilot/bin/ssh-1password-wrapper
│  Gate: Test SSH to carefree-edge-oden-wtp works
│
├─ Task: Update SSH configs
│  Owner: User/Copilot
│  Files: carefree-edge-maintenance/ssh_config
│  Gate: Remove IdentityFile lines (or update IdentityCommand)
│
├─ Task: Test SSH connections
│  Owner: User
│  Manual: ssh carefree-edge-oden-wtp whoami
│  Gate: All SSH tests pass
│
└─ Task: Archive local SSH keys
   Owner: User
   Command: rm -f ~/.ssh/carefree-edge-node ~/.ssh/carefree-core-key
   Gate: No plaintext keys on disk

WEEK 3: Environment Setup
├─ Task: Create 1Password Environment
│  Owner: User (1Password Desktop app)
│  Steps: Create "carefree-automation" environment
│  Gate: Environment created and populated
│
├─ Task: Mount .env file
│  Owner: User (1Password Desktop app)
│  Steps: Environments → Destinations → Mount .env
│  Gate: ~/.config/carefree/.env.1password accessible
│
├─ Task: Test .env loading
│  Owner: Copilot (scripts)
│  Tests: Python dotenv, shell source
│  Gate: Credentials loadable without errors
│
└─ Task: Create .env loader templates
   Owner: Copilot
   Output: ~/.copilot/templates/*.sh, *.py
   Gate: Templates work with real credentials

WEEK 4: Agent Integration
├─ Task: Enable MCP Codex Server
│  Owner: User (1Password app settings)
│  Steps: Developer → MCP Codex Server
│  Gate: MCP server authorized and running
│
├─ Task: Configure agent credential patterns
│  Owner: Copilot
│  Updates: AGENTS.md, agent instructions
│  Gate: Agent docs updated with MCP pattern
│
├─ Task: Test agent credential queries
│  Owner: Copilot (test agent)
│  Tests: Query MCP for SSH key, get secret
│  Gate: Agent can use credentials without logging
│
└─ Task: Document MCP usage
   Owner: Copilot
   Output: Knowledge base page
   Gate: Agents documented with examples

WEEK 5: Hardening & Docs
├─ Task: Security review
│  Owner: User + Copilot
│  Review: File permissions, secret exposure
│  Gate: No plaintext secrets found
│
├─ Task: Emergency recovery procedure
│  Owner: Copilot + User
│  Test: Manual SSH key restoration
│  Gate: Fallback procedure verified working
│
├─ Task: Update technician KB
│  Owner: Copilot
│  Pages: [[1Password Credential Management]]
│  Gate: KB page linked from [[Home]]
│
└─ Task: Final validation
   Owner: User
   Gate: All workflows functional, no credentials on disk
```

---

## Integration Checklist

### Pre-Implementation
- [ ] 1Password account created / accessible
- [ ] Carefree DevOps vault exists with SSH keys
- [ ] SSH keys stored in 1Password (not on local disk)
- [ ] SSH key passphrases also in 1Password
- [ ] User has 1Password for Mac/Linux (required)
- [ ] Plan reviewed and approved

### Week 1: Foundations
- [ ] 1Password CLI installed (version 2.20+)
- [ ] `op --version` confirms version
- [ ] 1Password Desktop app updated to latest
- [ ] This instruction file reviewed
- [ ] SSH key names confirmed in 1Password

### Week 2: SSH Setup
- [ ] SSH wrapper script created (`~/.copilot/bin/ssh-1password-wrapper`)
- [ ] Script is executable (`chmod +x`)
- [ ] SSH config files updated (or IdentityCommand configured)
- [ ] Test SSH to edge node: PASS
- [ ] Test SSH to core server: PASS
- [ ] Local SSH key files removed/archived
- [ ] `git status` shows no tracked key files

### Week 3: Environment Setup
- [ ] carefree-automation Environment created in 1Password
- [ ] All needed secrets added to Environment
- [ ] .env file mounted at `~/.config/carefree/.env.1password`
- [ ] 1Password Desktop app remounts .env on restart
- [ ] Test .env loading in Python script: PASS
- [ ] Test .env loading in shell script: PASS
- [ ] No errors loading credentials

### Week 4: Agent Integration
- [ ] MCP Codex server enabled in 1Password
- [ ] 1Password MCP server responding to queries
- [ ] Agent credential patterns documented in AGENTS.md
- [ ] Test agent SSH operation (with MCP): PASS
- [ ] Test agent API operation (with MCP): PASS
- [ ] Credentials not logged in agent output

### Week 5: Validation
- [ ] Security audit: no plaintext secrets on disk
- [ ] Emergency recovery procedure tested and documented
- [ ] Technician KB pages updated and linked
- [ ] All agent/script workflows tested end-to-end
- [ ] Team/colleagues notified of changes
- [ ] Audit log monitoring set up in 1Password

### Ongoing
- [ ] Weekly: Review 1Password vault access logs
- [ ] Monthly: Rotate service account token (if using)
- [ ] Quarterly: Test emergency SSH fallback
- [ ] Annually: Rotate SSH key passphrases

---

## Quick Reference: Command Cheat Sheet

```bash
# ─────────────────────────────────────────────────────────
# SSH OPERATIONS
# ─────────────────────────────────────────────────────────

# Interactive SSH (with shell plugin)
ssh carefree-edge-oden-wtp

# SSH with wrapper (manual)
ssh-1password-wrapper carefree@100.67.6.63

# SSH with key from CLI pipe
ssh -i <(op read "op://Carefree DevOps/Carefree Edge Nodes SSH Key/private key") \
  carefree@100.67.6.63

# List available SSH keys in vault
op list items --vault "Carefree DevOps" | grep -i "ssh\|key"

# ─────────────────────────────────────────────────────────
# ENVIRONMENT & CREDENTIALS
# ─────────────────────────────────────────────────────────

# Load .env and verify credentials
source ~/.config/carefree/.env.1password
echo "EMQX_API_KEY: $EMQX_API_KEY"

# Get a specific secret from CLI
op read "op://Carefree DevOps/Carefree Edge Nodes SSH Key/private key"

# List all secrets in Environment
op list items --vault "carefree-automation"

# List all vaults
op vault list

# ─────────────────────────────────────────────────────────
# TROUBLESHOOTING
# ─────────────────────────────────────────────────────────

# Check if 1Password CLI is working
op whoami

# Check if 1Password Desktop app is running
pgrep -i "1Password"

# Check if .env file is mounted
ls -la ~/.config/carefree/.env.1password
# Should show: prw------- 1 user staff ... (FIFO, not regular file)

# Verify SSH config
ssh -G carefree-edge-oden-wtp | grep -i identity

# Test SSH without actually connecting
ssh -T -i <(op read "op://Carefree DevOps/...") \
  carefree@100.67.6.63 "echo 'Connected'"

# ─────────────────────────────────────────────────────────
# EMERGENCY PROCEDURES
# ─────────────────────────────────────────────────────────

# Restart 1Password app
killall "1Password 7"
open -a "1Password 7"

# Authenticate CLI again
op signin

# Check what's in your current 1Password session
op item list --format json | jq '.[] | .title'
```

---

## References & Resources

| Resource | Purpose | Link |
|----------|---------|------|
| 1Password CLI Guide | Installation, commands, reference | https://www.1password.dev/cli |
| Local .env Mounting | Setup and limitations | https://www.1password.dev/environments/local-env-file |
| MCP Codex Server | Agent credential queries | https://www.1password.dev/environments/mcp-codex-server |
| Shell Plugins | SSH key auto-injection | https://www.1password.dev/cli/shell-plugins |
| Best Practices | Security & reliability | https://www.1password.dev/cli/best-practices |

---

**End of Architecture Map**
