# VS Code Env Settings - Local Only (Git Bypass)

Action:
Function:
Frequency:
Process:

Action: Track workspace settings that are intentionally local and not pushed.
Function: VS Code workspace/folder settings (`.vscode/settings.json`, `.code-workspace`).
Frequency: On setup and when Python env behavior changes.
Process:
1. Keep `.vscode/settings.json` local in each repo because `.vscode/` is git-ignored.
2. Use `CommerceExpert.code-workspace` to centralize multi-root settings.
3. Re-apply folder settings manually on a new machine if `.vscode/` is ignored.

## Hidden from push

The following files are currently git-ignored and will not be pushed:

- `/Users/williamjames/Documents/CommerceExpert/webClerk3/.vscode/settings.json`
- `/Users/williamjames/Documents/CommerceExpert/React2025/.vscode/settings.json`
- `/Users/williamjames/Documents/CommerceExpert/vue2020/.vscode/settings.json` (ignored by global gitignore: `settings.json`)

Additional visibility notes:

- `/Users/williamjames/Documents/CommerceExpert/00WebClerk19/Project/Sources` is not a git repo in this workspace, so its `.vscode/settings.json` has no push target.
- `/Users/williamjames/Documents/CommerceExpert/CommerceExpert.code-workspace` is outside any git repo in this workspace root, so it is local-only unless you place it inside a repository.

## Current local settings

```json
{
  "python.envFile": "${workspaceFolder}/.env",
  "python.terminal.useEnvFile": true
}
```

wc3 also pins interpreter locally:

```json
{
  "python.defaultInterpreterPath": "/Users/williamjames/Documents/CommerceExpert/webClerk3/bin/python"
}
```

## Verification commands

```bash
git -C /Users/williamjames/Documents/CommerceExpert/webClerk3 check-ignore -v .vscode/settings.json
git -C /Users/williamjames/Documents/CommerceExpert/React2025 check-ignore -v .vscode/settings.json
```
