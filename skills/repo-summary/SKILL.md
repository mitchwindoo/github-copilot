---
name: repo-summary
description: 'Summarize recent work performed on the repository. Use when: user asks for a changelog, work summary, progress update, standup notes, what changed, recent activity, or commit history summary. Produces a friendly, human-readable summary of git changes grouped by date and type.'
argument-hint: 'Optional: time range like "last 3 days", "since Monday", "this sprint"'
---

# Repository Work Summary

Produce a clean, human-readable summary of recent changes in the repository based on git history. The output should be understandable by anyone — project managers, stakeholders, or developers — without requiring deep technical knowledge.

## When to Use

- User asks "what's been done?", "summarize recent work", "what changed?"
- Generating standup notes or progress updates
- Creating a changelog for a time period
- Reviewing work before a meeting or handoff

## Procedure

### 1. Determine Time Range

Ask the user what period to cover. Offer these common options:
- Since a specific date or day ("since Monday", "last 7 days")
- Since a tag or release
- A number of recent commits ("last 10 commits")
- Between two commits or branches

If the user doesn't specify, ask before proceeding.

### 2. Gather Git Data

Run these commands to collect context:

```bash
# Get commit log with files changed (adjust date/range as needed)
git log --since="<date>" --pretty=format:"%h|%ad|%an|%s" --date=short --name-status

# For a quick overview of what areas were touched
git log --since="<date>" --pretty=format:"%h %ad %s" --date=short --stat
```

If the user specifies a commit range instead of dates:
```bash
git log <start>..<end> --pretty=format:"%h|%ad|%an|%s" --date=short --name-status
```

### 3. Classify Changes

Group the raw changes into these human-friendly categories:

| Category | What to include |
|----------|----------------|
| **Views & UI** | Perspective views, style classes, stylesheets, page configs |
| **Logic & Scripts** | Python scripts, gateway events, timers, tag-change scripts |
| **Data & Queries** | Named queries, tag configurations, database changes |
| **Configuration** | Project settings, session props, global props, permissions |
| **Documentation** | README files, instructions, comments, task notes |
| **Infrastructure** | Docker, CI/CD, git config, build tooling |

### 4. Format the Summary

Use this structure:

```markdown
## Work Summary: [date range]

### [Date or Date Range]

**Views & UI**
- [Plain-language description of what was added/changed/fixed]
- ...

**Logic & Scripts**
- [Plain-language description]
- ...

[other categories as applicable — skip empty ones]

---
[Repeat for other dates if multi-day range]
```

### 5. Tone & Language Rules

- **Default tone**: Friendly and clear — like explaining to a project manager what the team accomplished
- Use plain language: "Added a new status indicator to the dashboard" not "Implemented SVG fill-based alertActive style class on ia.display.icon component"
- Lead with the *what* and *why*, not the *how*
- Use action verbs: Added, Fixed, Updated, Removed, Reorganized, Improved
- If a commit message is cryptic, interpret the file changes to describe the intent
- Keep bullet points to one line each
- Group related commits into a single bullet when they're part of the same effort
- Include the commit hash in parentheses at the end only if the user requests technical detail

### 6. Adjustments by Audience

If the user specifies a different audience, adjust:

| Audience | Adjustments |
|----------|-------------|
| **Project managers** (default) | Focus on features, fixes, progress. Skip implementation details. |
| **Developers** | Include file paths, commit hashes, technical context. Tag each bullet as `[feature]`, `[fix]`, `[refactor]`, or `[chore]`. |
| **Stakeholders** | High-level only. Group into themes like "reliability improvements" or "new features". |
| **All / mixed** | Use the PM default but add a collapsible "Technical Details" section at the end if there's useful detail. |

### 7. Edge Cases

- **Merge commits**: Skip unless they represent meaningful integration points
- **WIP/fixup commits**: Consolidate into the final result they achieved
- **Reverts**: Mention only if the revert itself is significant; otherwise omit both the original and the revert
- **Empty range**: Tell the user "No commits found in that range" and suggest alternative ranges
- **Very large ranges (50+ commits)**: Summarize by theme rather than individual items; offer to break into smaller chunks
- **Long time ranges (1 month+)**: Group by week instead of individual days (e.g., "Week of Jan 13") to keep the summary scannable

## Output Location

- **Default**: Present the summary directly in chat
- If the user asks to save it, write to `tasks/changelog.md` or a path they specify

## Example Output

> ## Work Summary: Jan 13 – Jan 17
>
> ### Monday, Jan 13
>
> **Views & UI**
> - Added a new operator dashboard showing real-time line status
> - Fixed the navigation menu not highlighting the active page
>
> **Logic & Scripts**
> - Set up automatic fault detection for the RTM line
>
> ### Tuesday, Jan 14
>
> **Data & Queries**
> - Added queries to pull tool life data from the ERP system
>
> **Configuration**
> - Updated session timeout from 30 min to 60 min
