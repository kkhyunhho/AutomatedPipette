# ToDo

> Cumulative task history for the AutomatedPipette project.
> Append new tasks below; never delete or rewrite past entries
> (see CLAUDE.md §4 Task Management).

## 2026-06-05 | Apply CommonClaude conventions to project root

### Background
The CommonClaude conventions repo is vendored under `CommonClaude/`.
Install its configuration at the project root so Claude Code picks it
up for the AutomatedPipette (Picus2 BLE pipette automation) project.

### Work items
- [x] Copy `CommonClaude/CLAUDE.md` to project root
- [x] Copy `CommonClaude/.claude/settings.json` to `.claude/`
- [x] Copy the 5 hook scripts to `.claude/hooks/`
- [x] Copy `CommonClaude/.clang-format` to project root
- [x] Create fresh `ToDo.md` for this project (this file)
- [x] Create fresh `LearnedPatterns.md` skeleton for this project
- [x] Leave `README.md` and `.gitignore` untouched (per user)

## 2026-06-05 | Commit CommonClaude install and PR to upstream

### Background
`coport-uni/AutomatedPipette` is a fork of the original
`kkhyunhho/AutomatedPipette` (fork main == upstream main, identical).
Commit the CommonClaude install, push to the fork, and open a PR
against the upstream original.

### Work items
- [ ] Cut branch `chore/apply-commonclaude-conventions` from `main`
- [ ] Stage explicit paths only (config files; not `CommonClaude/` or `docs/`)
- [ ] Commit with Conventional Commits format
- [ ] Push branch to fork (`origin` = coport-uni)
- [ ] Open PR: `coport-uni:chore/...` -> `kkhyunhho:main`
