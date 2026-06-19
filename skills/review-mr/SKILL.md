---
name: review-mr
description: Lightweight local code review for diffs, branches, and GitLab merge requests. Use when asked to review local changes or an MR without posting to a remote PR. For automated GitHub PR reviews that post comments, use the code-review plugin instead.
---
# Review (local / MR)

## Process
1. Read the full diff before commenting
2. Check for: type safety, error handling, edge cases, security
3. Verify tests cover the changes
4. Flag breaking changes explicitly

## Priorities (highest to lowest)
1. Security vulnerabilities (injection, auth bypass, secrets)
2. Correctness bugs
3. Missing error handling / edge cases
4. Performance issues
5. Code style / readability

## Output Format
- Group findings by severity: 🔴 Critical, 🟡 Warning, 🔵 Suggestion
- Include file path and line context
- Suggest a fix, don't just flag problems
