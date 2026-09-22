---
name: git-commit
description: Inspect tracked Git changes, respond in Chinese, and draft or create repository-aware commits without editing workspace files. Use when the user asks for a Git commit message, wants current changes summarized, or explicitly asks Codex to commit; in commit mode, audit read-only, stage every tracked workspace change, never stage or commit untracked files, and stop for the user's ruling instead of fixing or omitting any problematic tracked file.
---

# Git Commit

Create accurate commit messages from the actual tracked diff. When a commit is authorized, commit every tracked workspace change without editing file contents, and leave untracked files untouched.

Use Chinese for all user-facing replies and commit subjects and bodies. Keep repository-specific prefixes, identifiers, and technical terms unchanged when translating them would reduce clarity.

## Choose the Mode

- If the user asks only to generate, draft, translate, or suggest a commit message, return the message without changing Git state.
- If the user explicitly asks to commit, finish the read-only audit, stage the complete tracked workspace, validate the staged diff, and create the commit.
- Do not interpret a request for a commit message as authorization to stage or commit.

## Non-Negotiable Commit Rules

A trailing blank line at EOF reported by `git diff --check` is an accepted warning and does not block a commit. Per the user's standing preference, trailing whitespace on lines is also accepted without asking for a ruling and does not block a commit.

- Never modify, generate, delete, rename, format, or fix any workspace file during a commit task. Git index and commit metadata operations are allowed; file-content changes are not.
- Commit every tracked change in the target repository, including already staged changes and tracked unstaged modifications or deletions. Do not silently omit tracked files or split the tracked scope based on relevance or coherence.
- Never stage or commit an untracked (`??`) file. Report untracked paths separately and leave them untouched. If the user wants one included, ask them to add it to the index themselves and then rerun the commit workflow.
- If any conflict, validation failure other than the accepted EOF warning, suspicious file, credential, local configuration, build output, archive, large binary, unrelated change, or release-note mismatch is found within the tracked commit scope, stop before committing and ask the user to decide. Report the exact issue and affected paths; do not edit, delete, unstage, ignore, or exclude tracked paths on your own. When the user explicitly confirms that a previously reported credential or other sensitive item should be committed, record that ruling and proceed without repeating the same confirmation question in the current or subsequent commit workflow.
- Use only read-only inspection and validation commands before staging. Do not run builds, tests, formatters, generators, fixers, packaging commands, or other commands that may write files during the commit workflow.

## Inspect the Repository

1. Locate the repository root and read applicable `AGENTS.md` instructions.
2. Run `git status --short --untracked-files=all`, `git diff --stat`, `git diff`, and `git diff --cached`.
3. Classify changes as staged additions, tracked unstaged modifications or deletions, and untracked files. State the difference precisely: a normal `git commit` uses the index, while `git add -u` stages tracked modifications and deletions without adding untracked files.
4. Inspect recent subjects with `git log -10 --oneline` to match local prefixes and tone.
5. Treat all existing worktree and index changes as user work. Never discard them.
6. List every untracked path for reporting, but do not inspect its contents or metadata unless the user explicitly asks. Untracked files are outside the commit scope and do not block a tracked commit by themselves.
7. Detect conflicts and unusual two-column states such as `AD`, `MD`, `UU`, or a staged file deleted again in the worktree. Report them and wait for the user's ruling.

## Define the Commit Scope

- In commit mode, the intended scope is every changed path already staged in the index plus all tracked unstaged modifications and deletions in the target repository.
- Include staged additions, staged or unstaged tracked modifications, and tracked deletions in one commit unless the user explicitly instructs otherwise. Exclude every untracked (`??`) path.
- After the read-only audit passes, use `git add -u` from the repository root. Never use `git add -A`, `git add .`, or another command that could add untracked files during this workflow.
- Ignored and untracked files are outside the commit scope. Never force-add them during a commit task.
- If the repository boundary or the meaning of “all files” is ambiguous, ask the user before staging.

## Choose the Commit Language

- Use Chinese for every commit subject and body.
- Preserve established repository prefixes and necessary English technical terms.

## Write the Message

Use this structure:

```text
[可选的仓库前缀] 简洁、明确的主题
- 说明第一项实质性行为变化
- 说明下一项相关变化
- 说明重要的兼容性或迁移细节
```

Rules:

- Write the subject and body in the selected language.
- Match established repository prefixes such as `[build]`, `[fix]`, or a product tag.
- Keep the subject specific and preferably no longer than 72 characters.
- Use an imperative subject where it fits the repository style.
- Put the first body bullet immediately after the subject on the next line. Do not include blank or whitespace-only lines anywhere in the commit message.
- Use two to five factual body bullets for a non-trivial commit.
- Before drafting, inventory the material change categories in the complete intended diff, such as delivery assets, runtime behavior, lifecycle or state handling, compatibility, configuration, and documentation. Cover every material category in the subject or body, grouping repeated mechanical edits by behavior.
- Do not let staging state bias the description. Write the draft from the complete tracked `git diff HEAD`, excluding untracked files, then confirm it against `git diff --cached` after `git add -u`.
- Describe behavior and intent, not a file-by-file inventory.
- Do not hide a broad code or lifecycle change under a vague umbrella bullet merely to keep the message short. Use dense, specific bullets and omit only details that are genuinely implementation-level.
- If the intended commit includes a changelog or release note, compare it with the code and configuration diff. If they disagree, report the mismatch and wait for the user's ruling; never edit either file during the commit task.
- Treat x86 debug artifacts as implicit delivery. Their presence in the manifest and omission from the changelog is not, by itself, a release-note mismatch or blocker. Explicit contradictions about x86 support still require a ruling.
- Mention compatibility, migration, or preserved behavior when it matters.
- Do not claim tests, validation, issue IDs, or customer impact unless supported by the request or evidence.

Example:

```text
[build] 区分 SDK 版本与交付版本
- 为非待机唤醒项目新增 release_version
- 生成共享的交付版本头文件并用于包名
- 保留待机唤醒项目现有的 sdk_version 流程
```

## Commit Safely

Perform these steps only when the user explicitly requested a commit:

1. Run only focused, read-only validation appropriate to the changed files and repository. If useful validation would write files, do not run it; report that limitation to the user.
2. If any audit or validation problem other than the accepted EOF warning is found, stop and request the user's ruling without changing files or selectively excluding paths.
3. Record the output of `git ls-files --others --exclude-standard`, then stage all tracked modifications and deletions from the repository root with `git add -u`. Preserve any already staged additions; never add an untracked path.
4. Review the staged scope with:
   - `git diff --cached --name-status`
   - `git diff --cached --stat`
   - `git diff --cached`
   - `git diff --cached --check`
5. Confirm that `git diff` is empty and `git ls-files --others --exclude-standard` still matches the recorded untracked-path list. If tracked changes remain or the untracked set changes, restart the read-only audit; never stage the untracked paths.
6. If `git diff --cached --check` finds a trailing blank line at EOF or trailing whitespace on a line, record it as accepted and continue. For all other findings, stop and ask the user. Do not fix files, unstage paths, or narrow the commit.
7. Confirm the reviewed diff matches the subject and every body bullet exactly.
8. Create one non-interactive commit from the reviewed index with the Chinese subject and body as one continuous multiline message with no blank lines.
9. Never amend, push, create a tag, or open a pull request unless explicitly requested.

## Report the Result

After creating a commit, report:

- commit hash and subject;
- validation performed and its result;
- confirmation that all tracked workspace changes were committed;
- any remaining staged or unstaged tracked changes, which are an issue;
- every remaining untracked path, identified as deliberately excluded rather than silently left behind.

If only a message was requested, return a copy-ready code block containing the subject followed immediately by the body bullets, with no blank lines.

## 提交消息格式检查

- 提交消息必须保留真实的多行格式：第一行是主题，后续每行是一个正文条目，所有行连续排列，不得出现空行或仅含空白字符的行。
- 不要为主题和各正文条目分别使用多个 `git commit -m` 参数，因为 Git 会把每个参数作为独立段落并插入空行。使用一次 `git commit -F -`，从标准输入传入完整消息。
- 禁止把字面量 `\\n` 写入提交消息。提交后使用 `git show --format=fuller --no-patch HEAD` 检查显示格式，并用 `git cat-file commit HEAD | sed '1,/^$/d' | awk 'NF == 0 { exit 1 }'` 确认消息正文不存在空行。
