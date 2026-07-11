# Security Policy

RazorBackRoar takes security seriously. This policy applies to **Nexus** and matches the organization-wide standard used across RazorBackRoar product repositories.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest release on `main` | Yes |
| Older releases | Best effort |

Security fixes ship on `main` and in the next published release when applicable.

## Reporting a Vulnerability

**Please do not open a public issue for security vulnerabilities.**

Preferred reporting channels (in order):

1. **GitHub Private Vulnerability Reporting** — use [Report a vulnerability](https://github.com/RazorBackRoar/Nexus/security/advisories/new) on this repository when enabled.
2. **Maintainer contact** — message [@RazorBackRoar](https://github.com/RazorBackRoar) on GitHub with a clear subject such as `SECURITY: Nexus`.

Include as much of the following as you can:

- Description of the issue and impact
- Steps to reproduce (PoC if available)
- Affected version / commit / platform (macOS version, Apple Silicon)
- Whether the issue is already public knowledge

## What to Expect

- **Acknowledgement** within a few days when the report is actionable
- **Status updates** while we investigate and prepare a fix
- **Credit** in release notes when you want to be named (optional)

We may decline reports that are out of scope (for example, issues that require physical access to an unlocked Mac, or theoretical issues without a practical impact path).

## Scope

In scope examples:

- Unexpected local file overwrite / path traversal in packaging or media tools
- Secrets or credentials committed to the repository
- Unsafe handling of untrusted input that leads to code execution or data loss

Out of scope examples:

- Social engineering
- Denial of service against a single local machine without a security boundary bypass
- Bugs in third-party dependencies that are already tracked upstream (please link the upstream advisory)

## Safe Harbor

We will not pursue legal action against researchers who:

- Make a good-faith effort to avoid privacy violations and data destruction
- Do not exploit the issue beyond what is needed to demonstrate it
- Report the issue promptly and keep it private until we have shipped a fix or agreed on disclosure

## Non-Security Bugs

Please use [GitHub Issues](https://github.com/RazorBackRoar/Nexus/issues) for ordinary bugs and feature requests.
