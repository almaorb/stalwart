# Vision

The code does not state a vision. This document derives it from the project's own prose: the previous README, `CONTRIBUTING.md`, `SECURITY.md`, the upgrade guides in `UPGRADING/` (especially `v0_16.md`) and commit messages. Where something is an inference rather than a quotation of intent, it says so.

## The problem

The project's documents do not state the problem in one place; this section is an inference from what the server bundles.

Running mail for an organization has traditionally meant assembling several independent daemons: an MTA for SMTP, an IMAP/POP3 server, a filter for spam, a DKIM/DMARC signer and verifier, a CalDAV/CardDAV server, a directory, and glue between them. Each has its own configuration language, storage, and failure modes, and few of them speak the newer standards (JMAP, MTA-STS, DANE, PACC) or were built for horizontal scale.

Stalwart's answer, visible in the workspace layout, is one memory-safe server that implements the whole stack: access protocols (JMAP, IMAP, POP3, ManageSieve), transport (SMTP/LMTP with authentication and transport security), collaboration (CalDAV, CardDAV, WebDAV and their JMAP equivalents), spam filtering, directory integration, TLS automation and observability, over a single pluggable storage layer.

## Why it was built this way

The reasons below are stated in the project's documents.

- **Security and robustness.** The README describes the server as "secure, fast, robust and scalable" and lists memory safety "thanks to Rust" as a security property. The project publishes a security audit report (https://stalw.art/blog/security-audit), and `SECURITY.md` defines a disclosure policy with a matching internal response process (`docs/SECURITY_PROCESS.md`).
- **Open standards first.** Every feature in the README is anchored to an RFC or IETF draft. The `v0.16` redesign was driven partly by a standard: account names became email addresses so that the server can implement PACC (`draft-ietf-mailmaint-pacc`) without leaking account existence.
- **Scale from one box to a cluster.** The README states the design goal of handling "small setups to large-scale deployments of thousands of nodes" with fault tolerance and high availability. `UPGRADING/v0_16.md` explains that configuration moved into the datastore because per-node configuration files drifted in clustered deployments.
- **One model, one API.** `v0.16` replaced TOML files and a REST API with configuration stored as JMAP objects, so that "the same API that serves email metadata also serves server configuration", and the WebUI and `stalwart-cli` operate on a complete, consistent view of the system.
- **Sustainable open source.** The code is AGPL-3.0, with an enterprise license (SELv2) for commercial terms and enterprise-only features. Development has been funded in part by NLnet's NGI0 Entrust and NGI Zero Core programmes and by sponsors.

## Principles

Derived from the documents and from how the code is organized:

1. **Standards compliance over invention.** Implement the published protocol; extend through standard extensions (JMAP capabilities, IMAP extensions, Sieve extensions) rather than private APIs.
2. **Storage is a pluggable concern.** Protocol and business logic depend on the `store` crate's abstractions, never on a specific database. Data, blobs, full-text search and in-memory state can live in different backends.
3. **User data is sacred; configuration can evolve.** The `v0.16` guide stresses that the breaking change touched configuration only: "emails, calendars, contacts, files ... stay exactly where they are."
4. **Configuration is data.** Since `v0.16`, everything except the datastore location lives in the datastore and is managed declaratively (`stalwart-cli apply`, `snapshot`).
5. **Safe by default.** The boot sequence inserts safe defaults, drops privileges after binding (`RUN_AS_USER`/`RUN_AS_GROUP`), refuses to start on pre-0.15 data and runs the `v0.15` to `v0.16` migration only in recovery mode (`crates/migration/src/lib.rs`), and the release profile builds with LTO and stripped binaries.
6. **Human-maintained code.** `CONTRIBUTING.md` states that AI-generated code is not accepted, that using AI as autocomplete is fine only if every generated line is read, understood and reviewed by a human, and that contributors are responsible for every line they submit.

## Direction

The previous README stated that Stalwart is **feature complete** with respect to the protocols it set out to support, and that the next milestone is "finalizing the database schema and focusing on performance optimizations" before releasing **1.0**. The previous README said further enhancements would be prioritized by community votes on GitHub issues labelled `enhancement`; the current `CONTRIBUTING.md` asks for feature requests in the **Feature Ideas** category at support.stalw.art instead. `UPGRADING/v0_16.md` also announced a zero-downtime migration utility and an account-routing proxy; whether those shipped is not recorded in this repository.

## Non-goals

These are stated or directly implied by the project's documents:

- **Not a general-purpose feature playground.** `CONTRIBUTING.md` accepts only bug fixes and translations at this stage; new features are not accepted unless they are a few lines of code, because "the architecture is still evolving."
- **Not file-driven configuration.** Since `v0.16`, the server deliberately does not read its operational configuration from local files beyond `config.json`.
- **Not a REST management API.** The old `/api/...` management endpoints were removed in favour of JMAP (`UPGRADING/v0_16.md`). A few helper endpoints remain under `/api/` (login, account introspection, schema retrieval, live telemetry streams), described in `api/v1/openapi.yml`.
- **Not a webmail client.** No end-user mail UI is part of this repository; clients connect over JMAP, IMAP, POP3 or DAV. The web administration UI is distributed as a separate application bundle that the server loads (`crates/common/src/manager/application.rs`). (Inference from the code layout.)
- **Not dependent on a single database.** No feature should require one specific backend; backends are optional Cargo features.
