# GitHub Copilot reusable skill repo

This repository is a portable source of truth for the Copilot runtime experience: custom instructions, skills, agent definitions, and lifecycle hooks. The goal is to keep the same workflow, quality guardrails, and reusable patterns across every machine without reconfiguring Copilot by hand.

## What lives here

- [agents/](agents) — reusable agent definitions
- [instructions/](instructions) — repository-specific customization and operational guardrails
- [skills/](skills) — reusable skill packs for common workflows
- [hooks/](hooks) — session lifecycle checks and safety automation
- [bin/](bin) — installation and bootstrap scripts for portable setup
- [copilot-instructions.md](copilot-instructions.md) — repo-level default Copilot instructions

See [instructions/awesome-copilot-addons.md](instructions/awesome-copilot-addons.md) for the curated addon map and the broader Copilot ecosystem references.

Lightpanda browser automation support is available in [skills/lightpanda-browser/](skills/lightpanda-browser) and summarized in [plans/lightpanda-browser-quick-reference.md](plans/lightpanda-browser-quick-reference.md).

## Why this is portable

This repo is intentionally designed to be cloned into a normal git working directory and then linked into the machine-local Copilot config folder. That means:

- the custom experience lives in version control
- updates can be pulled with a standard git workflow
- a new machine can get the same setup in a few minutes
- local runtime state stays separate from the portable repo content

## Recommended workflow

Use a single Git repo as the canonical copy, then install it as the active Copilot home on each computer.

### 1) Clone the repo

```bash
git clone https://github.com/mitchwindoo/github-copilot.git ~/src/github-copilot
cd ~/src/github-copilot
```

### 2) Bootstrap the machine-local Copilot runtime

PowerShell:

```powershell
pwsh ./bin/install-portable.ps1
```

bash / zsh:

```bash
./bin/install-portable.sh
```

The installer creates a symlink at `$HOME/.copilot` pointing at the cloned repo. If this repo is already installed as the active Copilot config root, it exits cleanly without touching the current state.

### 3) Keep it in sync

```bash
cd ~/src/github-copilot
git pull --ff-only
```

If the repo is used as the active runtime, the changes are immediately available the next time Copilot starts.

## Project layout for reuse

```text
github-copilot/
├── agents/
├── bin/
├── hooks/
├── instructions/
├── skills/
├── copilot-instructions.md
├── README.md
├── .gitignore
├── .git/
└── ...
```

This layout follows the standard Copilot additive model and makes it easy to add or remove reusable assets without disturbing the local runtime state.

## Local runtime vs portable repo

Keep the portable repo clean and version controlled. Runtime caches, indexed data, and editor state remain local to the machine and are intentionally ignored by git.

The default `.gitignore` includes the runtime artifacts that should not be committed:

- cache directories
- local session state
- logs
- runtime database files
- plugin install state

## Cross-platform notes

- Windows: use the PowerShell installer.
- macOS / Linux: use the shell installer.
- If your environment blocks symlinks, remove the existing local Copilot home and re-run the installer with a path that matches your preferred working directory.

## Useful commands

```bash
# update repo content on this machine
git pull --ff-only

# verify the active Copilot config target
ls -ld ~/.copilot

# or on Windows
Get-Item $HOME/.copilot | Format-List FullName,LinkType,Target
```

## Safety and standards

This repo is intended for reusable guidance and automation, not for machine-specific secrets. Keep credentials, service tokens, and local-only configuration outside the tracked repo and use the existing environment or 1Password-based patterns for runtime secrets.

## Related files

- [bin/install-portable.ps1](bin/install-portable.ps1)
- [bin/install-portable.sh](bin/install-portable.sh)
- [bin/ssh-1password-wrapper](bin/ssh-1password-wrapper)
- [skills/lightpanda-browser/SKILL.md](skills/lightpanda-browser/SKILL.md)
- [plans/lightpanda-browser-quick-reference.md](plans/lightpanda-browser-quick-reference.md)
