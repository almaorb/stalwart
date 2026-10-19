# Development

How to build, run, test and release Stalwart from this repository. The build, test and release commands below are taken from the repository's workflows and Dockerfiles; the lint section notes where a command is not run by CI. Contribution policy (vouched contributors, bug fixes and translations only, no AI-generated code) is in [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Prerequisites

| Requirement | Why |
|-------------|-----|
| Rust toolchain with edition 2024 support (Rust 1.85 or newer) | All crates use `edition = "2024"`. No `rust-toolchain` file pins a version; the container builds use unpinned Rust images (`rust:slim-trixie` in `Dockerfile.build`, `cargo-chef:latest-rust-slim-trixie` in `Dockerfile`). |
| C/C++ toolchain and libclang (`build-essential`, `libclang-dev`) | Native dependencies such as RocksDB and AWS-LC. `Dockerfile` installs `build-essential libclang-19-dev`. |
| Docker | The integration tests start FoundationDB, PostgreSQL, MySQL, MariaDB, Redis, NATS, MinIO, OpenSearch, Meilisearch, Keycloak, OpenLDAP, Pebble, PowerDNS and others via `testcontainers` (`tests/src/utils/containers.rs`). |
| FoundationDB client library 7.4 | Only for the `foundationdb` feature (`Dockerfile.fdb`, `FDB_VERSION_RANGE="7.4"`). |
| CMake | Only for the `kafka` feature (`rdkafka` is built with `cmake-build`). |

## Build

```sh
# Default features: rocks + enterprise
cargo build -p stalwart

# Release build (LTO, single codegen unit, stripped)
cargo build --release -p stalwart

# Feature set used for published Linux, Windows and container builds
cargo build --release -p stalwart --no-default-features \
  --features "sqlite postgres mysql rocks s3 redis azure nats enterprise"

# FoundationDB build
cargo build --release -p stalwart --no-default-features \
  --features "foundationdb s3 redis azure nats enterprise"
```

### Cargo features (`crates/main/Cargo.toml`)

| Feature | Effect |
|---------|--------|
| `rocks` | RocksDB store (default). |
| `sqlite`, `postgres`, `mysql` | SQL stores and SQL directory backend. |
| `foundationdb` | FoundationDB store. |
| `s3`, `azure` | Blob stores. |
| `redis` | Redis store and Redis cluster coordination. |
| `nats`, `kafka`, `zenoh` | Cluster coordination backends. |
| `enterprise` | Enterprise features licensed under SELv2 (default). Build with `--no-default-features` and without this feature for a pure AGPL binary. |
| `dev_mode` | Development helpers; enables `INSERT_TEST_DATA`. |

### Cross-compilation and containers

- `Dockerfile` builds a Debian trixie image for `linux/amd64` and `linux/arm64` using `cargo-chef`.
- `Dockerfile.build` with `docker-bake.hcl` is what CI uses to build every Linux target (gnu and musl for x86_64, aarch64, armv7, armv6) with `cargo-zigbuild` and `sccache`.
- `Dockerfile.fdb` builds the FoundationDB variant.

## Run

```sh
./target/release/stalwart --config /etc/stalwart/config.json
```

| Option | Meaning |
|--------|---------|
| `-c, --config <PATH>` | Configuration file (the datastore location). |
| `-e, --export <PATH>` | Export all store data. Requires `--config`. |
| `-i, --import <PATH>` | Import store data. Requires `--config`. |
| `-o, --console` | Open the store console. |
| `-h, --help`, `-V, --version` | Help and version. |

If the configuration file does not exist the server starts in **bootstrap mode** and opens port 8080 for initial setup through the web UI. The container image exposes ports 443, 25, 110, 587, 465, 143, 993, 995, 4190 and 8080, runs as user `stalwart` (uid 2000), and uses `/etc/stalwart` and `/var/lib/stalwart` as volumes. Its health check calls `/healthz/live`.

To populate a development instance with sample data, build with `--features dev_mode` and set `INSERT_TEST_DATA`.

## Configuration and environment variables

Since `v0.16`, `config.json` describes only the datastore. All other settings are registry objects stored in the datastore and managed through JMAP, the web UI or `stalwart-cli` (`apply`, `snapshot`). See [`UPGRADING/v0_16.md`](../UPGRADING/v0_16.md) for the model and https://stalw.art/docs for the settings themselves.

Environment variables read by the server (names only):

| Variable | Read in | Purpose |
|----------|---------|---------|
| `CONFIG_PATH` | `common/src/manager/boot.rs` | Configuration file path; alternative to `--config`. |
| `STALWART_HOSTNAME` | `store/src/registry/local.rs` | Override the local hostname. |
| `STALWART_PUBLIC_URL` | same | Public base URL of the server. |
| `STALWART_HTTPS_PORT` | same | HTTPS port used when deriving URLs. |
| `STALWART_ROLE` | same | Cluster role of this node. |
| `STALWART_PUSH_SHARD` | same | Push-notification shard of this node (1-based). |
| `STALWART_RECOVERY_MODE` | same | `1` or `true` starts in recovery mode (port 8080 open for troubleshooting). |
| `STALWART_RECOVERY_ADMIN` | same | Recovery-mode administrator, as `user:password`. Treat as a secret. |
| `STALWART_RECOVERY_MODE_PORT` | `common/src/config/server/listener.rs` | Port for recovery mode. |
| `STALWART_RECOVERY_MODE_LOG_LEVEL` | `common/src/config/telemetry.rs` | Log level in recovery mode. |
| `LOG` | `common/src/config/telemetry.rs` | Log level override. |
| `RUN_AS_USER`, `RUN_AS_GROUP` | `common/src/network/listen.rs` | Drop privileges after binding listeners. |
| `API_TOKEN_ADMIN` | `common/src/auth/authentication.rs` | Static administrator bearer token. Treat as a secret. |
| `EXPORT_TYPES` | `common/src/manager/backup.rs` | Restrict `--export` to selected data families. |
| `DANGER_FORCE_MIGRATE` | `migration/src/lib.rs` | Set to `1` to re-run the `v0.16` migration on a database already at the current schema version (otherwise skipped). |
| `INSERT_TEST_DATA` | `main/src/main.rs` | Insert sample data (`dev_mode` builds only). |
| `STALWART_HEALTHCHECK_URL` | `Dockerfile` | Health-check URL used by the container image. |

## Test

The test workflow (`.github/workflows/test.yml`, manually dispatched) runs:

```sh
cargo fmt --all --check

export STORE=RocksDb RUST_MIN_STACK=16777216
cargo test -p jmap_proto -- --nocapture
cargo test -p imap_proto -- --nocapture
cargo test -p store -- --nocapture
cargo test -p tests directory -- --nocapture
cargo test -p tests smtp -- --nocapture
cargo test -p tests imap -- --nocapture
cargo test -p tests jmap -- --nocapture
```

`tests/src/` also contains `webdav`, `scim`, `store`, `cluster`, `telemetry`, `system` and `automation` suites, run the same way (`cargo test -p tests <module>`). The `tests` crate enables `rocks` and `sqlite` by default; enable `postgres`, `mysql`, `foundationdb`, `s3`, `redis`, `azure`, `nats` or `kafka` to test other backends.

Test-only environment variables:

| Variable | Purpose |
|----------|---------|
| `STORE` | Data store under test (required by store tests; CI uses `RocksDb`). |
| `BLOB_STORE`, `SEARCH_STORE`, `MEMORY_STORE` | Blob, search and in-memory store under test (default: `default`). |
| `COORDINATOR` | Coordinator backend for cluster tests (required by them). |
| `QUICK_TEST` | Run a reduced query test set. |
| `NO_INSERT` | Reuse existing test data instead of resetting it. |
| `SLOW_FDB_TRX` | Simulate slow FoundationDB transactions. |
| `TEST_NAME`, `SPAM_RULES_URL` | Select a single spam-filter test; override the spam rules source. |
| `SCIM_CONFORMANCE` | Set to `1` to run the SCIM conformance suite. |

For manual testing against external services, [`tests/docker/INSTRUCTIONS.md`](tests/docker/INSTRUCTIONS.md) describes a Docker Compose stack (`tests/docker/docker-compose.yml`) with the same services and their test credentials.

## Lint

```sh
cargo fmt --all --check     # run by .github/workflows/test.yml
cargo clippy --workspace    # standard Cargo; not run by any workflow
```

Workspace clippy lints are set in the root `Cargo.toml` (`result_unit_err = "allow"`); `crates/main/src/main.rs` additionally warns on `large_futures` and lossy integer casts. Rust source files carry an SPDX header (REUSE); `crates/common/build.rs` is the one exception at `v0.16.23`.

## Release

Releases are produced by `.github/workflows/ci.yml` on a pushed `v*.*.*` tag (or manual dispatch with `Docker`/`Release` inputs):

1. Build Linux binaries for eight targets via `Dockerfile.build`, plus Windows (`x86_64-pc-windows-msvc`), macOS (`aarch64-apple-darwin`, `x86_64-apple-darwin`) and FreeBSD.
2. Push per-architecture images by digest to `ghcr.io/stalwartlabs/stalwart` and Docker Hub, merge them into multi-arch manifests (gnu and `-alpine` musl variants), sign them with cosign and attach build-provenance attestations.
3. Create a draft GitHub release with the artifacts; a `publish` job un-drafts it once every job succeeds, and `ci-retry.yml` re-runs failed jobs up to twice, and if the run still fails on its third attempt a cleanup job deletes the draft release and the tag.

All workspace members, including `tests/`, carry the same `version` (currently `0.16.23`), so a release bumps every manifest. Each release has a section in [`CHANGELOG.md`](../CHANGELOG.md), and breaking upgrades have a guide in `UPGRADING/`. No release checklist is written down in the repository; this is what the history shows.

Other workflows: `scorecard.yml` (OpenSSF Scorecard), `trivy.yml` (vulnerability scanning), `auto-close-prs.yml` (closes PRs from authors not in `.github/allowed-pr-authors.txt`), `auto-close-issues.yml` and `auto-redirect-discussions.yml`. Dependabot is configured in `.github/dependabot.yml`.
