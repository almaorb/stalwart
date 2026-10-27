# Updating this fork from upstream

- `origin` = `git@github.com:almaorb/stalwart.git` (the fork), `upstream` = `git@github.com:stalwartlabs/stalwart.git`
  (formerly `stalwartlabs/mail-server`).
- Upstream tags releases `vX.Y.Z` on `upstream/main`. Pick the newest tag without a pre-release suffix.

## Fork commits (as of 2026-10-26)

The only fork-specific commit is **"Move documents into docs/ and document the project"**
(README/SECURITY_* moved to `docs/`, VISION/ARCHITECTURE/DEVELOPMENT/HISTORY added). It is kept.
"Redis fixes" and "Meilisearch fail on timeout changes" are *upstream* commits (by the upstream
maintainer) that were on the fork's base; they are contained in `v1.0.0`, so nothing to carry.
Everything else (deployment notes) lives in `memory/` and does not touch upstream files.

## 2026-10-26 update: v0.16.23(+fork) → v1.0.0

- Old main tagged `pre-update-2026-10-26` (= `bdfd53bc4`).
- Branch `update-v1.0.0` created from tag `v1.0.0`; fork docs commit cherry-picked. Conflicts:
  - `README.md` modify/delete: upstream edited the root README; the fork had moved it to
    `docs/README.md`. Resolved by keeping it deleted (docs/README.md is the front page) and noting
    1.0 in docs/README.md.
  - `tests/docker/INSTRUCTIONS.md` delete/modify: upstream deleted the whole `tests/` crate in 1.0
    (test suites moved to a private repo); the fork had moved+edited it. Resolved by deleting it
    and dropping its row from the docs index.
  - `SECURITY.md` merged cleanly (upstream's new text + the fork's `docs/SECURITY_PROCESS.md` link).
- Then merged into `main`.
- Tests: v1.0.0 contains **no tests at all** (0 `#[test]` in the workspace; v0.16.23 had 447
  unit tests plus the `tests/` crate). `cargo test --release -p jmap_proto -p imap_proto
  -p smtp-proto -p sieve-rs -p calcard -p dav-proto -p scim-proto -p utils -p jmap-tools -p types
  -p trc -p smtp-report -p nlp` compiles and runs 0 tests. The real check is the local proof in
  `stalwart-on-the-mac.md`.
- v1.0 has a new database layout: a v0.16 data dir cannot be opened in place. The Mac server
  started fresh on 1.0.0. **The VPS servers (almaorb.dev, almaorb.cloud) are on 0.16.x and need
  the official migration tool (stalwart-migrate) before they can move to 1.0 — do not just swap
  binaries there.**

## Procedure for the next release

```sh
cd ~/code/stalwart
git fetch upstream --tags
git tag --sort=-v:refname | head            # pick newest vX.Y.Z
git tag pre-update-$(date +%F) main
git checkout -b update-vX.Y.Z vX.Y.Z
git cherry-pick <fork commits from: git log --oneline <old-tag>..pre-update-$(date +%F)>
cargo build --release -p stalwart --bin stalwart
# read CHANGELOG.md for the release: breaking DB/schema changes need a migration, not a binary swap
launchctl bootout gui/$(id -u)/com.almaorb.mac.stalwart
cp -a ~/srv/stalwart/data ~/srv/stalwart/data.bak-$(date +%F)     # rollback point
cp target/release/stalwart ~/srv/stalwart/bin/stalwart
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.almaorb.mac.stalwart.plist
# rerun the local proof (send info@ -> appreview@, read via IMAP and JMAP), then:
git checkout main && git merge --ff-only update-vX.Y.Z   # or a merge commit if main moved
git branch -d update-vX.Y.Z
```

Never push without Marco asking.
