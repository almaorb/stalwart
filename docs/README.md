<p align="center">
    <a href="https://stalw.art">
    <img src="../img/logo-red.svg" height="150">
    </a>
</p>

# Stalwart

Stalwart is an open-source mail and collaboration server written in Rust. A single binary (`stalwart`) speaks JMAP, IMAP4, POP3, SMTP/LMTP, ManageSieve, CalDAV, CardDAV and WebDAV, ships a built-in spam and phishing filter, and stores everything in a pluggable data, blob, search and in-memory store (RocksDB, FoundationDB, PostgreSQL, MySQL, SQLite, S3-compatible, Azure, Redis and others). It is developed by Stalwart Labs LLC and dual-licensed under AGPL-3.0 and the Stalwart Enterprise License v2.

- Website: https://stalw.art
- User documentation: https://stalw.art/docs/install/get-started
- Support portal: https://support.stalw.art
- Source: https://github.com/stalwartlabs/stalwart

## What it does

| Area | Capabilities |
|------|--------------|
| Email access | [JMAP for Mail](https://datatracker.ietf.org/doc/html/rfc8621), [JMAP for Sieve](https://www.ietf.org/archive/id/draft-ietf-jmap-sieve-22.html), JMAP [WebSocket](https://datatracker.ietf.org/doc/html/rfc8887), [Blob Management](https://www.rfc-editor.org/rfc/rfc9404.html) and [Quotas](https://www.rfc-editor.org/rfc/rfc9425.html); [IMAP4rev2](https://datatracker.ietf.org/doc/html/rfc9051) and [IMAP4rev1](https://datatracker.ietf.org/doc/html/rfc3501) with [extensions](https://stalw.art/docs/development/rfcs#imap4-and-extensions); [POP3](https://datatracker.ietf.org/doc/html/rfc1939) with STLS and SASL; [ManageSieve](https://datatracker.ietf.org/doc/html/rfc5804). |
| Mail transport | SMTP and LMTP with built-in [DMARC](https://datatracker.ietf.org/doc/html/rfc7489), DKIMv1/[DKIMv2](https://datatracker.ietf.org/doc/draft-ietf-dkim-dkim2-spec/), [SPF](https://datatracker.ietf.org/doc/html/rfc7208) and [ARC](https://datatracker.ietf.org/doc/html/rfc8617); [DANE](https://datatracker.ietf.org/doc/html/rfc6698), [MTA-STS](https://datatracker.ietf.org/doc/html/rfc8461) and [TLS reporting](https://datatracker.ietf.org/doc/html/rfc8460); automated DKIM key rotation; Sieve, MTA hooks and milter filtering; distributed queues with routing, throttling, quotas and delayed/priority delivery; envelope rewriting. |
| Collaboration | [CalDAV](https://datatracker.ietf.org/doc/html/rfc4791) with [scheduling](https://datatracker.ietf.org/doc/html/rfc6638) and [JMAP for Calendars](https://datatracker.ietf.org/doc/html/draft-ietf-jmap-calendars-24); [CardDAV](https://datatracker.ietf.org/doc/html/rfc6352) and [JMAP for Contacts](https://datatracker.ietf.org/doc/html/rfc9610); [WebDAV](https://datatracker.ietf.org/doc/html/rfc4918) and [JMAP for File Storage](https://datatracker.ietf.org/doc/html/draft-ietf-jmap-filenode-03); sharing via [WebDAV ACL](https://datatracker.ietf.org/doc/html/rfc3744) and [JMAP Sharing](https://datatracker.ietf.org/doc/html/rfc9670). |
| Spam and phishing | Rule-based filter, statistical classifier with collaborative filtering and automatic training, LLM-driven analysis, DNSBLs, Pyzor, homograph and spoofing protection, reply tracking, sender reputation, greylisting and spam traps. |
| Storage and search | Data, blob, full-text search and in-memory stores are selected independently: RocksDB, FoundationDB, PostgreSQL, MySQL, SQLite, S3-compatible, Azure, Redis, filesystem. Full-text search in 17 languages with the built-in engine or Meilisearch, Elasticsearch, OpenSearch, PostgreSQL or MySQL. |
| Identity and access | Built-in, LDAP, SQL and OIDC directories; OAuth 2.0 authorization code and device flows; [SCIM](https://www.rfc-editor.org/info/rfc7643/) v2 provisioning; TOTP two-factor; app passwords; roles, permissions and ACLs; multi-tenancy with per-user and per-tenant quotas. |
| Operations | Automatic TLS via [ACME](https://datatracker.ietf.org/doc/html/rfc8555) (TLS-ALPN-01, DNS-01, DNS-PERSIST-01, HTTP-01); automated DNS management; autoconfiguration via [PACC](https://datatracker.ietf.org/doc/draft-ietf-mailmaint-pacc/), autoconfig and autodiscover; encryption at rest with S/MIME or OpenPGP; automatic blocking of abusive IPs; rate limiting. |
| Scale-out | Clustering coordinated peer-to-peer or via Kafka, Redpanda, NATS, Redis or Zenoh; read replicas, sharded blob storage; Kubernetes, Apache Mesos and Docker Swarm deployments. |
| Observability and admin | Logging and tracing (OpenTelemetry, journald, files, console), metrics (OpenTelemetry, Prometheus), webhooks, alerts, live tracing; a web administration UI and the `stalwart-cli` tool, both driven by the JMAP management API. |

A security audit report is published at https://stalw.art/blog/security-audit.

![Demo](../img/demo.gif)

## Status

- Current version on this branch: **0.16.23** (`crates/main/Cargo.toml`), tagged `v0.16.23` on 2026-09-21.
- Pre-1.0. The previous README described the project as *feature complete*; the stated next milestone is finalizing the database schema and performance work before **1.0**.
- `v0.16` replaced the TOML configuration and REST API with a small on-disk `config.json` plus configuration stored as JMAP objects in the datastore. Upgrades from `v0.15.x` and earlier require the migration in [`UPGRADING/v0_16.md`](../UPGRADING/v0_16.md).
- Contributions are limited to vouched contributors, and at this stage only bug fixes and translations are accepted. See [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Quick start

Prebuilt binaries and container images are produced by the release workflow (`.github/workflows/ci.yml`). `install.sh` downloads the binary for the host from the latest GitHub release.

**Installer (Linux, macOS, FreeBSD; run as root):**

```sh
sh install.sh            # FHS paths: /usr/local/bin/stalwart, /etc/stalwart/config.json
sh install.sh --fdb      # FoundationDB build
sh install.sh /opt/stalwart   # custom prefix
```

**Docker** (images are pushed to `ghcr.io/stalwartlabs/stalwart` and Docker Hub `stalwartlabs/stalwart`; this command is the one in [`UPGRADING/v0_16.md`](../UPGRADING/v0_16.md) without the recovery-admin variable):

```sh
docker run -d --name stalwart \
  --restart unless-stopped \
  -p 443:443 -p 8080:8080 \
  -p 25:25 -p 587:587 -p 465:465 \
  -p 143:143 -p 993:993 \
  -p 110:110 -p 995:995 \
  -p 4190:4190 \
  -v stalwart-etc:/etc/stalwart \
  -v stalwart-data:/var/lib/stalwart \
  stalwartlabs/stalwart:v0.16
```

**From source:**

```sh
cargo build --release -p stalwart
./target/release/stalwart --config /path/to/config.json
```

When no configuration file exists yet the server starts in bootstrap mode and opens port 8080 for initial setup (`crates/common/src/manager/boot.rs`). Platform-specific guides: [Linux / macOS / FreeBSD](https://stalw.art/docs/install/platform/linux), [Windows](https://stalw.art/docs/install/platform/windows), [Docker](https://stalw.art/docs/install/platform/docker). See [DEVELOPMENT.md](DEVELOPMENT.md) for build features, tests and environment variables.

## Documents

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | This page. |
| [VISION.md](VISION.md) | The problem, motivation, principles and non-goals. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stack, crates, request and data flow, storage model. |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Building, running, testing, releasing, configuration. |
| [HISTORY.md](HISTORY.md) | Origins, authors and milestones from the git log. |
| [SECURITY_PROCESS.md](SECURITY_PROCESS.md) | Internal checklist for handling a security incident. |
| [SECURITY_TEMPLATE.md](SECURITY_TEMPLATE.md) | Template for publishing a security advisory. |
| [tests/docker/INSTRUCTIONS.md](tests/docker/INSTRUCTIONS.md) | Docker Compose stack of external services for testing. |

Kept at the repository root because tooling, GitHub, or links printed by shipped binaries refer to them by path:

| Document | Why it stays |
|----------|--------------|
| [../CHANGELOG.md](../CHANGELOG.md) | Release notes at the conventional root path. |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Linked by `.github/workflows/auto-close-prs.yml`; recognized by GitHub. |
| [../SECURITY.md](../SECURITY.md) | GitHub security policy. |
| [../UPGRADING/](../UPGRADING/) | `UPGRADING/v0_16.md` is linked by URL from `crates/migration` and `crates/jmap` startup messages, `resources/scripts/migrate_v016.py` and the changelog. |
| [../LICENSES/](../LICENSES/) | License texts (REUSE layout). |

## Support

Questions and bug reports go to the [Stalwart Support Portal](https://support.stalw.art). Stalwart Labs sells an [Enterprise License](https://stalw.art/enterprise) with priority support. A slide overview of the project is at https://stalw.art/slides.

## Sponsorship and funding

Sponsors can contribute through [Open Collective](https://opencollective.com/stalwart); sponsors at $5/month or more receive an Enterprise edition license, and at $30/month or more also get [Premium Support](https://stalw.art/support).

Part of the development was funded through the [NGI0 Entrust Fund](https://nlnet.nl/entrust) (grant agreement No 101069594) and [NGI Zero Core](https://nlnet.nl/NGI0/) (grant agreement No 101092990), established by [NLnet](https://nlnet.nl/) with financial support from the European Commission's [Next Generation Internet](https://ngi.eu/) programme.

## License

Dual-licensed under the [GNU Affero General Public License v3.0](../LICENSES/AGPL-3.0-only.txt) and the [Stalwart Enterprise License v2 (SELv2)](../LICENSES/LicenseRef-SEL.txt). Source files carry SPDX notices following the [REUSE guidelines](https://reuse.software/); enterprise-only code is gated behind the `enterprise` Cargo feature and marked with `LicenseRef-SEL` snippets.

Copyright (C) 2020, Stalwart Labs LLC.
