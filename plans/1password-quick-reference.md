# 1Password Integration — Quick Reference One-Pager

## What's Happening?

**Current State:** SSH keys stored locally on disk (`~/.ssh/carefree-*`)  
**Target State:** SSH keys managed by 1Password, zero secrets on disk  
**Why:** Eliminate attack surface, centralize credentials, enable agent security

---

## Three Paths: Which One Do You Use?

```
┌─────────────────────────────────┐
│ INTERACTIVE SSH                 │ → Shell Plugin or IdentityCommand
│ (You typing "ssh host-name")    │   Setup: 10 min, Works: Instantly
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ SCRIPT/AUTOMATION               │ → .env Mounting + dotenv loader
│ (CI/CD, maintenance scripts)    │   Setup: 1 hour, Works: Everywhere
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ AGENTS (Copilot, Subagents)     │ → MCP Codex Server
│ (intrusion-watch, CVE-check)    │   Setup: 2 hours, Works: Securely
└─────────────────────────────────┘
```

---

## Implementation Summary

| Phase | What | Duration | Key Outcome |
|-------|------|----------|-------------|
| **1** | Install 1Password CLI | 1 day | CLI works (`op whoami`) |
| **2** | SSH shell plugin or wrapper | 1 day | SSH without local keys |
| **3** | .env mounting from 1Password | 1 day | Secrets loadable via dotenv |
| **4** | MCP Codex for agents | 1 day | Agents query 1Password safely |
| **5** | Hardening + documentation | 1 day | KB updated, procedures tested |
| | **TOTAL** | **5 days** | Zero secrets on disk ✓ |

---

## Architecture in 30 Seconds

```
User/Agent needs credential
         ↓
1Password Desktop App (Unlocked)
         ↓
Choose method:
├─ Shell plugin → SSH process
├─ CLI wrapper → Temp file
├─ .env mount → FIFO named pipe
└─ MCP query → Agent context
         ↓
Credential delivered (never stored on disk)
         ↓
Operation completes
         ↓
Cleanup (no traces left)
```

---

## Get Started Right Now

### Step 1: Install 1Password CLI (5 min)
```bash
brew install 1password-cli
op --version          # Should show v2.20+
op signin              # Authenticate
```

### Step 2: Verify SSH Keys in 1Password (5 min)
Open 1Password Desktop app:
1. Navigate to **Carefree DevOps** vault
2. Look for these items:
   - `Carefree Edge Nodes SSH Key` ✓
   - `Carefree Servers SSH Key` ✓

### Step 3: Read the Strategy (15 min)
```bash
# Open and review:
open ~/.copilot/plans/1password-integration-plan.md
open ~/.copilot/plans/1password-architecture-map.md
```

### Step 4: Choose Your Path
- [ ] **Quick Win** (1-2 days): SSH shell plugin only
- [ ] **Full Integration** (5 days): All three layers
- [ ] **Phased** (5 weeks): One phase per week

---

## Key Files You Need

```
~/.copilot/plans/1password-integration-plan.md      ← Read first
~/.copilot/plans/1password-architecture-map.md      ← Reference
~/.copilot/instructions/1password-credentials.instructions.md  ← Use during work
```

---

## Decision Tree: Am I Ready?

```
Do I have 1Password for Mac/Linux?
├─ YES  → Continue
└─ NO   → Install it first (free version OK)

Is 1Password version 8.10+?
├─ YES  → Continue
└─ NO   → Update in App Store

Are my SSH keys stored in 1Password?
├─ YES  → Continue
└─ NO   → Manual: Add them to Carefree DevOps vault first

Do I understand the three layers?
├─ YES  → You're ready! Start Phase 1
└─ NO   → Read architecture-map.md again
```

---

## What If Something Goes Wrong?

| Problem | Solution | Docs |
|---------|----------|------|
| SSH key not loading | Restart 1Password app | Emergency Procedures |
| .env file not mounting | Check Desktop app settings | Architecture Map |
| Agent credentials failed | Verify MCP server running | MCP Codex docs |
| Can't connect at all | Use manual fallback procedure | Fallback section |

---

## Security Checklist (Before Going Live)

- [ ] Test SSH to edge node: `ssh carefree-edge-oden-wtp whoami`
- [ ] Test SSH to core server: `ssh carefree-core-data whoami`
- [ ] Verify no plaintext keys on disk: `ls -la ~/.ssh/carefree-*` (should be EMPTY)
- [ ] Verify .env loadable: `python3 -c "from dotenv import load_dotenv; load_dotenv('~/.config/carefree/.env.1password'); import os; print(os.getenv('EMQX_API_KEY'))"`
- [ ] Test MCP query (if using agents): MCP returns secret
- [ ] Review 1Password vault access logs: No unauthorized access
- [ ] All tests PASS → Ready for production

---

## Timeline for Your Workflow

**Today:** Review plans (30 min)  
**Tomorrow:** Install CLI + verify keys (30 min)  
**Day 3:** Implement SSH method (1-2 hours)  
**Day 4:** Test and remove local keys (1 hour)  
**Day 5:** .env mounting (1 hour)  
**Week 2:** Agent integration + docs (2-3 hours)

---

## Key Concepts

| Term | Meaning | Your Use |
|------|---------|----------|
| **1Password Vault** | Encrypted storage for secrets | Carefree DevOps vault holds SSH keys |
| **1Password Environment** | Curated set of secrets that can be mounted | carefree-automation environment (APIs, creds) |
| **Shell Plugin** | 1Password auto-injects SSH keys | For interactive SSH connections |
| **MCP Codex** | API for agents to query secrets | Copilot agents get creds without exposure |
| **FIFO Named Pipe** | Special file 1Password uses for .env | Not real file; never stored on disk |
| **.env Mounting** | Locally mounted Environment file | Scripts load via `source ~/.config/carefree/.env` |

---

## Next Steps

1. **Install 1Password CLI** (brew install 1password-cli)
2. **Read the plans** (~/.copilot/plans/*)
3. **Decide on path** (Quick win vs full integration)
4. **Start Phase 1** (Foundation setup)
5. **Reference instruction file during work** (1password-credentials.instructions.md)

---

## Questions Answered

**Q: Will this break my current workflow?**  
A: No, layered implementation means each phase works independently.

**Q: What if 1Password goes down?**  
A: Fallback procedure documented; can access manually with encrypted backup key.

**Q: Does this affect agents?**  
A: Yes, but in a good way — they become more secure (no credential logging).

**Q: How long until full integration?**  
A: 5 days if fully focused, or one phase per week for 5 weeks if distributed.

**Q: What's the minimal risk start?**  
A: Just use SSH shell plugin (removes local keys in 1 day, nothing else needed).

---

## Resources

- Full Plan: `~/.copilot/plans/1password-integration-plan.md`
- Architecture: `~/.copilot/plans/1password-architecture-map.md`
- Reference: `~/.copilot/instructions/1password-credentials.instructions.md`
- Official Docs: https://www.1password.dev/cli
- Session Notes: `/memories/session/1password-integration-next-steps.md`

---

**Print this page and post it on your desk. Reference daily during implementation.**

**Your current status:** Ready for Phase 1 ✓
