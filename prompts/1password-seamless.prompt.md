---
name: 1password-seamless
description: "Use when setting up or troubleshooting 1Password SSH Agent, 1Password CLI, or 1Password MCP workflows. Trigger phrases: 1password setup, ssh agent config, op cli secret read, mcp secret access, configure agent.toml, add ssh host with 1password key."
mode: ask
model: GPT-5.3-Codex
---

Set up or troubleshoot 1Password end to end for the current machine and task.

Goals:
1. Prefer 1Password SSH Agent for SSH authentication.
2. Use 1Password CLI for explicit metadata lookups and one-off secret reads.
3. Use 1Password MCP only for in-context secret access without exposing plaintext.
4. Keep credentials out of logs, files, and chat responses.

Workflow:
1. Inspect and validate SSH agent policy at ~/.config/1Password/ssh/agent.toml.
2. Ensure SSH config includes ~/.ssh/1Password/config.
3. Add or update host entries in ~/.ssh/config with Host, HostName, and User.
4. Validate config resolution with ssh -G <host-alias>.
5. Validate key availability with:
   SSH_AUTH_SOCK=~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock ssh-add -l
6. For CLI tasks, use non-interactive commands whenever possible:
   - op account list
   - op vault list
   - op item get "Item Name" --vault "Vault Name"
   - op read "op://Vault/Item/field"

Safety rules:
- Never print secret values.
- Never write secrets to disk unless explicitly asked.
- Prefer item-scoped access over broad vault access.
- Use BatchMode for non-interactive SSH probes when validating.

Output format:
- Summarize what changed.
- List exact files touched.
- Report verification command results.
- If blocked, report the precise blocker and the smallest next action.
