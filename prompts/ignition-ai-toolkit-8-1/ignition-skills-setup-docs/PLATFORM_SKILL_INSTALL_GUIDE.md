# Platform Skill Install Guide

Stack version: `starter-2026.07.14.01`
Runner API version: `0.3.200`
Ignition target: `8.1`
Updated: `2026-07-14`

## Short Answer

To install and verify the Ignition Web Dev runner, start with `00_START_HERE_API_SETUP.md`. The runner is a Gateway-side setup asset, not an AI skill folder.

The core skill format should stay the same across platforms:

```text
ignition-perspective-import-zip/
  SKILL.md
  agents/openai.yaml
  references/
  scripts/
  assets/
```

What changes by platform is how the buyer installs or uploads that folder.

- Codex and Claude Code usually use extracted skill folders on disk.
- Claude chat, Claude Desktop chat, and Claude Cowork use uploaded zip files.
- Claude API and OpenAI API are separate integration paths and should not be the starter buyer default.
- The Web Dev runner zip is not an AI skill. It is an Ignition setup asset.

Use uppercase `SKILL.md` for best cross-platform compatibility. Keep the folder name and the `name` field in `SKILL.md` identical, lowercase, and hyphenated.

## What We Ship

The starter product ships these skill zips:

- `ignition-perspective-import-zip.zip`
- `ignition-perspective-host-builder.zip`
- `ignition-perspective-button-logging.zip`
- `ignition-ai-log-assistant.zip`
- `ignition-alarm-pipeline-orchestrator.zip`
- `ignition-perspective-performance-profiler.zip`
- `ignition-udt-builder.zip`
- `ignition-jython-script-builder.zip`
- `ignition-sql-query-builder.zip`
- `ignition-sql-query-builder-without-api.zip`
- `ignition-historian-forensics.zip`
- `ignition-8-1-expression-language.zip`
- `ignition-hmi-scada-style-guide.zip`

The shipped Vision product pairs the `ignition-vision` and `ignition-vision-jython` skill folders in one download. The UDT forensic analyzer is not part of the customer bundle.

Each skill zip must contain one top-level skill folder:

```text
ignition-jython-script-builder.zip
  ignition-jython-script-builder/
    SKILL.md
    agents/openai.yaml
    references/
```

Do not package a Claude upload zip with loose files directly at the zip root.

The starter product also ships:

- `ignition-webdev-runner.zip`: Ignition Web Dev API runner scripts and runner setup materials.
- `ignition-skills-setup-docs.zip`: setup, safety, version, and platform install docs.

## Platform Matrix

| Platform | Best customer package | Install shape |
|---|---|---|
| ChatGPT Skills | Skill zip or upload package | Upload through Skills UI |
| OpenAI Codex | Extracted skill folder | Project or user skills directory |
| Claude chat / Claude Desktop chat | Skill zip | Upload zip containing the skill folder |
| Claude Cowork | Skill zip or plugin later | Upload/enable through Claude Desktop or Cowork customization |
| Claude Code | Extracted skill folder | `~/.claude/skills/<skill-name>/SKILL.md` or `.claude/skills/<skill-name>/SKILL.md` |
| Claude API | API-managed skill | Upload/manage through Skills API with code execution beta headers |

## Codex Install

### ChatGPT Skills UI

Use this path when the buyer is using ChatGPT Skills:

1. Open ChatGPT.
2. Select the profile icon.
3. Open `Skills`.
4. Choose `New skill`.
5. Choose `Upload from your computer`.
6. Upload one skill zip at a time.
7. Start a new chat and ask for the skill by name, for example:

```text
Use ignition-perspective-import-zip to build an Ignition 8.1 Perspective package.
```

OpenAI skills do not currently sync across products. A skill uploaded in ChatGPT may still need to be separately installed for Codex.

### Codex Local Or Project Install

Use this path when the buyer is using Codex with local/project files.

Project-local install:

```text
<project>/
  .agents/
    skills/
      ignition-perspective-import-zip/
        SKILL.md
```

User-local install, when supported by the buyer's Codex installation:

```text
%USERPROFILE%\.codex\skills\ignition-perspective-import-zip\SKILL.md
```

Steps:

1. Download the skill zip.
2. Extract it.
3. Copy the extracted skill folder into the target skills directory.
4. Restart Codex if the skill does not appear.
5. Start a new task and call the skill by name.

`agents/openai.yaml` is OpenAI-facing UI metadata. Keep it in the folder for Codex/OpenAI installs. Claude can ignore it.

The `$skill-installer` flow is useful for OpenAI catalog or GitHub-hosted skills. For this paid private bundle, use the downloaded skill folders unless a future marketplace/repo install path is provided.

## Claude Chat, Desktop Chat, And Cowork Install

Use this path when the buyer is using Claude's normal chat UI, Claude Desktop chat, or Claude Cowork.

1. Make sure Skills are enabled for the account/workspace.
2. Download one skill zip from the portal.
3. Open `Customize > Skills`.
4. Click the `+` button.
5. Choose `Create skill`.
6. Choose `Upload a skill`.
7. Upload the zip that contains the skill folder.
8. Toggle the skill on.
9. Start a new chat or Cowork task and either describe the task naturally or invoke the skill with `/skill-name`.

For Cowork, skills and plugins are managed from Claude Desktop/Cowork customization. Cowork can use enabled skills while working across local files/apps. If a future product bundle needs skills plus connectors, MCP servers, subagents, or hooks, package that as a Claude plugin instead of only standalone skill zips.

Custom Claude skills do not automatically sync across every Claude surface. Claude chat/Cowork uploads, Claude Code filesystem skills, and Claude API skills must be managed separately.

## Claude Code Install

Use this path when the buyer is using Claude Code.

Personal install:

```text
~/.claude/skills/ignition-perspective-import-zip/SKILL.md
```

Project install:

```text
<project>/.claude/skills/ignition-perspective-import-zip/SKILL.md
```

Steps:

1. Download the skill zip.
2. Extract it.
3. Copy the extracted skill folder into either `~/.claude/skills/` or `<project>/.claude/skills/`.
4. Start Claude Code in the project.
5. Test direct invocation:

```text
/ignition-perspective-import-zip
```

Claude Code watches existing skill folders for `SKILL.md` changes. If the top-level `.claude/skills` or `~/.claude/skills` directory did not exist when Claude Code started, restart Claude Code after creating it.

## API Surfaces

API skill setup should be treated as an advanced integration path.

- Claude API custom skills are uploaded/managed through the Skills API and require code execution skill headers. Claude API skills are workspace-wide, separate from claude.ai and Claude Code, and have no network access inside the code execution environment.
- OpenAI API skill usage is separate from ChatGPT/Codex product install. Do not assume a buyer's ChatGPT upload is available to their API workflow.

For the starter product, point buyers to ChatGPT/Codex/Claude UI/Claude Code installs first.

## Verification Prompts

After installing a skill, use one of these small tests:

```text
Use ignition-perspective-import-zip to outline the files needed for a portable Ignition 8.1 Perspective view package. Do not build the final zip yet.
```

```text
Use ignition-perspective-button-logging to outline how to log a Perspective Start button with audit, debug log, SQL row, tag outcome, and validation readback.
```

```text
Use ignition-ai-log-assistant to outline how to triage a pasted Ignition Gateway error excerpt with source labels, a time window, and confidence levels.
```

```text
Use ignition-perspective-performance-profiler to outline how to investigate a slow Perspective dashboard. Do not claim live Gateway/session/browser evidence unless the API runner is connected.
```

```text
Use ignition-jython-script-builder to review this Ignition Jython 2.7.3 snippet for Python 3 assumptions.
```

```text
Use ignition-sql-query-builder to draft a read-only Named Query pattern with parameters for a Perspective table.
```

```text
Use ignition-historian-forensics to outline how to diagnose missing or sparse Tag Historian data for one tag path and time range. Do not claim live history probe results unless the API runner is connected.
```

```text
Use ignition-8-1-expression-language to review an Expression Tag formula for divide-by-zero handling, date formatting, and tag quality behavior.
```

```text
Use ignition-udt-builder to outline a Pump UDT with parameters, expression tags, and validation reads. Do not apply changes yet.
```

```text
Use ignition-perspective-host-builder to list the runner health-check request shape. Do not apply changes.
```

## Common Mistakes

- Do not rename `SKILL.md` to `skills.md`.
- Do not package loose files at the zip root for Claude uploads.
- Do not install `ignition-webdev-runner.zip` as an AI skill.
- Do not put tokens, Gateway URLs, usernames, passwords, or customer tag paths into reusable skill folders.
- Do not combine all starter skills into one giant skill unless a future platform bundle/plugin explicitly needs that shape.
- Do not delete existing customer resources unless the user explicitly commands deletion.
- Do not ship internal builder references, draft skills, or unapproved skill folders.

## Sources

- OpenAI Skills in ChatGPT: https://help.openai.com/en/articles/20001066-skills-in-chatgpt
- OpenAI Codex skills catalog: https://github.com/openai/skills
- Agent Skills specification: https://agentskills.io/specification
- Claude Code skills: https://code.claude.com/docs/en/skills
- Claude custom skill upload guide: https://support.claude.com/en/articles/12512198-how-to-create-custom-skills
- Claude skills usage guide: https://support.claude.com/en/articles/12512180-use-skills-in-claude
- Claude API skills overview: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

## Vision Module Skill

`ignition-vision-module-skill.zip` contains two coordinated top-level skill folders: `ignition-vision` for Gateway/resource lifecycle work and `ignition-vision-jython` for native client Jython scope. Install both together. Live Vision validation recommends runner 0.3.200.
