---
name: 1password-seamless
description: 'Use when working with 1Password SSH Agent, 1Password CLI, or 1Password MCP. Covers SSH key allowlists, SSH host config, secret reads, vault lookups, and safe agent-context secret retrieval without exposing credentials.'
argument-hint: 'Optional: host name, vault name, item name, or secret flow to set up'
---

# 1Password Seamless Workflow

Use this skill when a task depends on 1Password for SSH access, secret retrieval, or automation.

## Choose the Right Path

- **SSH hosts**: use the 1Password SSH Agent.
- **Explicit secret reads**: use the 1Password CLI.
- **Agent-only secret access**: use the 1Password MCP server.
- **Environment variables for scripts**: use a mounted `.env` or a local env loader.

## SSH Agent Workflow

1. Add the key or vault to `~/.config/1Password/ssh/agent.toml`.
2. Make sure `~/.ssh/config` includes `~/.ssh/1Password/config`.
3. Define a host alias with `HostName` and `User`.
4. Validate the final SSH config with `ssh -G <host-alias>`.
5. Confirm the key is visible with `ssh-add -l` using the 1Password agent socket.

## CLI Workflow

- Use `op account list` to confirm the active account.
- Use `op vault list` to confirm the vault name.
- Use `op item get "Item Name" --vault "Vault Name"` to inspect metadata.
- Use `op read "op://Vault/Item/field"` when an explicit value is needed.
- Avoid interactive pickers when automation or repeatability matters.

## MCP Workflow

- Use MCP when the secret should stay in the model context and not be printed.
- Treat MCP results as sensitive data.
- Do not write MCP-fetched secrets to disk unless the user explicitly asks for a file-based handoff.
- Prefer CLI or mounted env files for scripts that need persistent process access.

## Safe Defaults

- Never echo a secret back to the user.
- Never log secrets in terminal output, prompts, or files.
- Prefer item-scoped access over broad vault access when the key is specific.
- Use `BatchMode=yes` when testing SSH connectivity non-interactively.

## Troubleshooting

- If SSH fails, check `agent.toml`, `ssh -G`, and `ssh-add -l` before changing host settings.
- If the CLI prompts for account selection, specify the account explicitly.
- If MCP is unavailable, fall back to CLI only for non-secret metadata or explicit user-approved secret reads.