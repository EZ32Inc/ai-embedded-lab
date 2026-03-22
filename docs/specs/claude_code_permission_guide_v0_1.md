# Claude Code Permission Mode Guide v0.1

**Status:** Draft
**Date:** 2026-03-21
**Source:** Extracted from AEL design discussion with ChatGPT

---

## 1. Overview

Claude Code supports multiple permission modes that control how much it asks for confirmation before taking actions. Understanding these modes allows you to configure the experience between "confirm every step" and "run autonomously."

The goal is not "completely no confirmation, do anything" — but rather "high autonomy with appropriate boundaries."

---

## 2. Three Permission Modes

### Mode 1: Normal / Default

Behavior:
- Asks for permission before each important action
- Every file edit, shell command, and tool use prompts confirmation
- Safest mode, highest interruption frequency

When to use:
- When working in unfamiliar territory
- When working on sensitive systems
- When you want full visibility over every action

### Mode 2: Auto-Accept / acceptEdits

Behavior:
- File edits are accepted automatically without prompting
- Continuous coding experience — no confirmation needed for file changes
- Shell commands may still require approval depending on risk level

When to use:
- Active coding sessions where you've defined the task clearly
- When you trust Claude's judgment on file edits for the current task
- The recommended default for most development work

**This is the mode most people want when they say "stop asking me to confirm everything."**

### Mode 3: bypassPermissions

Behavior:
- Skips all permission checks as much as possible
- Maximum autonomy
- **Officially marked as dangerous by Anthropic**

When to use:
- Only in controlled projects with limited scope
- Only when you fully trust the current task and environment
- Not recommended as a default — use sparingly

---

## 3. How to Switch Modes

### In VS Code

Press **Shift+Tab** to cycle through modes:
- Normal → Auto-Accept (shows "accept edits on" at bottom)
- Auto-Accept → Plan Mode
- Plan Mode → Normal

### In Terminal / CLI

The permission mode can be set in the settings file or via CLI flags.

**Dangerous skip flag (use with caution):**
```bash
claude --dangerously-skip-permissions
```

---

## 4. Settings Configuration

Claude Code uses a layered settings system:

| File | Scope |
|------|-------|
| `~/.claude/settings.json` | Global (all projects) |
| `.claude/settings.json` | Project shared (checked into repo) |
| `.claude/settings.local.json` | Project local personal (not committed) |

Known permission mode keys:
- `default` — normal mode, prompts on every important action
- `acceptEdits` — auto-accept file edits
- `plan` — plan-only mode, no execution
- `bypassPermissions` — skip permission checks (dangerous)

---

## 5. Plan Mode

Plan Mode is distinct from the permission modes above.

In Plan Mode:
- Claude thinks through the approach but does not execute
- No file edits, no commands run
- You review the plan and approve before execution starts

**When to use:**
- Before starting a large or risky task
- When you want to review the approach before any changes are made
- For architecture discussions and design reviews

**Transition:** Switch from Plan Mode to Auto-Accept to start execution after approving a plan.

---

## 6. Recommended Configuration

For most AEL development work:

```
Active coding:      Auto-Accept / acceptEdits
Architecture work:  Plan Mode first, then switch to Auto-Accept
Risky operations:   Normal Mode or explicit confirmation
Fully trusted task: bypassPermissions (rare, controlled)
```

**The best experience is:**
- Auto-accept file edits within the project directory
- Retain confirmation for: dangerous shell commands, deletions, git force push, external network calls, large git changes
- Use Plan Mode when starting complex multi-step tasks

---

## 7. What "SuperClaude" Actually Is

There is a framework called SuperClaude Framework that is sometimes described as "runs without asking for confirmation." Clarification:

- SuperClaude is **not** an official separate product from Anthropic
- It is a community framework that enhances Claude Code with specialized commands, personas, and workflows
- The "no confirmation" experience it enables comes from:
  - More aggressive auto-accept settings
  - More explicit workflow commands that pre-define scope
  - Sub-agents and pre-set permissions
  - Stronger project-level conventions

It is not that SuperClaude can "do anything without constraint" — it is configured to interrupt less while still operating within safety boundaries.

**Conclusion:** What you want is not "SuperClaude" specifically, but:
1. Auto-accept mode for file edits (Claude Code already has this)
2. Stronger project-level workflow conventions (CLAUDE.md, skills)
3. Tiered permission grants (auto-allow low-risk, retain confirmation for high-risk)

---

## 8. Suggested CLAUDE.md Conventions for AEL

To reduce interruptions in AEL development without sacrificing safety:

```markdown
# Claude Code Conventions for this project

## Auto-allowed actions (no confirmation needed)
- Read any file in the project
- Edit any file in ael/, tests/, docs/, configs/
- Run: python, pytest, grep, find, cat, ls
- Git status, git diff, git log

## Always confirm before
- git push
- git reset --hard
- Deleting files
- Commands affecting external systems
- Any command outside the project directory

## Default mode
acceptEdits — auto-accept file edits, retain shell command review
```

---

## 9. Key Insight

> The goal is not "no confirmation, do anything."
> The goal is "high autonomy with appropriate boundaries."

A completely unconfirmed Claude will occasionally take actions you didn't intend. The right configuration is: Claude moves fast on trusted, low-risk actions, and pauses on potentially destructive or irreversible ones.

Anthropic's own guidance explicitly pairs "more autonomous" with "sandboxing and safety boundaries" — not complete freedom.

---

*Extracted from AEL design discussion. For Claude Code official documentation, see the Claude Code help system.*
