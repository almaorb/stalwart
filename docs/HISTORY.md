# History

Everything here is derived from the git history of this repository (1,799 commits on `main` up to `v0.16.23`, the commit this documentation is based on; tags `v0.16.24` and `v0.16.25` exist upstream but are not on this branch), its tags, and the project's own documents.

## Origins

- **First commit:** 2023-03-06, `ca889365c` "Initial commit", by Mauro D `<mauro@degennaro.me>`.
- **Earlier work predates this repository.** Source headers carry `SPDX-FileCopyrightText: 2020 Stalwart Labs LLC`, and `UPGRADING/v0_16.md` (2026) says Stalwart "has been under continuous development for close to five years". The log shows existing codebases being brought in: "SMTP codebase import" (2023-05-16), "Imported Stalwart CLI crate" (2023-07-03) and "Imap-proto imported into repository" (2023-06-13). The pre-2023 history of those components is not in this repository.
- **Repository name.** Merge commits up to 2025-04-29 reference `github.com:stalwartlabs/mail-server`; from 2025-05-28 they reference `github.com:stalwartlabs/stalwart`.

## Who made it

| Author | Commits | Notes |
|--------|---------|-------|
| Mauro D / Mauro D. / Maurus Decimus / mdecimus (`mauro@stalw.art`, `mauro@degennaro.me` and GitHub user `mdecimus`) | 1,702 | The same maintainer under several git identities; about 95% of all commits. |
| dependabot[bot] | 27 | Dependency updates. |
| 53 other author names | 70 in total, 1 to 5 each | Including vickunwu, Renato Caldas, stratacast, Cameron Little, Lukas Lihotzki, Manuel Rüger and others; one of them, "Me" (`me@Stalwart-Labs.local`, 2 commits), may be a maintainer machine but git does not say. See `git shortlog -sn HEAD`. |

The copyright holder named in the SPDX headers of the source files is Stalwart Labs LLC.

**AI attribution.** No commit in the history carries a `Co-Authored-By` trailer naming an AI model, and no commit message credits one. The only `Co-Authored-By` trailers credit dependabot and the maintainer's own identities. `CONTRIBUTING.md` states that AI-generated code is not accepted in this project. (Commit messages such as "AI models" on 2024-10-05 refer to the LLM-based spam-filtering feature, not to authorship.)

## Activity

| Year | Commits |
|------|---------|
| 2023 (from March) | 246 |
| 2024 | 461 |
| 2025 | 514 |
| 2026 (to 2026-09-21) | 578 |

## Milestones

Dates are the first commit or tag that shows each milestone.

| Date | Milestone |
|------|-----------|
| 2023-03-06 | Initial commit. A bloom text index follows on 2023-03-26, FoundationDB on 2023-03-30 and SQLite on 2023-04-02. |
| 2023-04 to 2023-05 | JMAP Email/get, Email/query, thread merge and Email/set tests passing in April, Mailbox tests on 2023-05-03; crates renamed (2023-04-14). |
| 2023-05-16 | SMTP codebase imported; Sieve scripts and VacationResponse follow (2023-05-19). |
| 2023-06-13 | IMAP protocol crate imported. |
| 2023-07-16 | **v0.3.0**, first tag in this repository. |
| 2023-08-01 | Encryption at rest. |
| 2023-08-11 | Built-in spam filter ("Antispam implementation - part 1"). |
| 2023-10-25 | v0.4.0. |
| 2023-12-03 | Elasticsearch full-text backend. |
| 2023-12-27 | v0.5.0. |
| 2024-01-05 | ACME TLS-ALPN-01 certificate automation. |
| 2024-02-14 | v0.6.0. |
| 2024-04-09 | v0.7.0. |
| 2024-05-10 | Gossip-based cluster node discovery. |
| 2024-05-13 | v0.8.0. |
| 2024-05-22 | POP3 server. |
| 2024-08-01 | v0.9.0. |
| 2024-09-12 | Roles and multi-tenancy. |
| 2024-09-21 | v0.10.0. |
| 2024-10-02 | OIDC directory. |
| 2024-10-05 | LLM ("AI models") support in the spam filter. |
| 2024-11-10 | Azure blob storage. |
| 2025-01-06 | v0.11.0. |
| 2025-03-28 to 2025-04-29 | CardDAV, CalDAV and WebDAV. |
| 2025-05-14 to 2025-05-21 | NATS, Redis pub/sub, Kafka and Zenoh cluster coordination replace gossip. |
| 2025-05-26 | v0.12.0. |
| 2025-07-15 | v0.13.0. |
| 2025-10-01 to 2025-10-14 | JMAP for Contacts, Calendars and File Storage. |
| 2025-10-22 | v0.14.0. |
| 2025-12-14 | Meilisearch full-text backend. |
| 2025-12-16 | v0.15.0. |
| 2026-01-23 | Registry crate: configuration as typed JMAP objects. |
| 2026-04-20 | **v0.16.0**: TOML configuration and REST API replaced by `config.json` plus registry objects in the datastore; account names become email addresses; new WebUI and `stalwart-cli` (see `UPGRADING/v0_16.md`). |
| 2026-07-01 | DKIM2 verification. |
| 2026-08-27 | SCIM v2 (`scim-dev` branch merged). |
| 2026-09-21 | v0.16.23. |

## Last commit before this documentation change

| Date | Short hash | Subject |
|------|------------|---------|
| 2026-09-21 | `9d1c75ab6` | Meilisearch fail on timeout changes |

This commit is tagged `v0.16.23`.
