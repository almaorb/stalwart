# Stalwart on the Mac (phase 1, set up 2026-10-26)

Approved by Marco 2026-10-26: AlmaOrb's own mail server runs natively on his Mac (no Docker),
built from this repo. Local only for now; almaorb.dev becomes the public edge in phase 2
(see `phase-2-vps-edge.md`).

## What runs

- Version: upstream `v1.0.0` + fork docs commit (branch `main` of this repo).
- Build: `cargo build --release -p stalwart --bin stalwart` (default features `rocks,enterprise`,
  same as upstream release binaries; no Enterprise license is installed, so it runs as the AGPL
  community edition). Release build takes ~15 min on the Mac.
- Binary: `~/srv/stalwart/bin/stalwart` (copied from `target/release/stalwart`).
- Config: `~/srv/stalwart/etc/config.json` — only the datastore location (v0.16+ model). Every
  other setting lives in the database as registry objects, managed via JMAP (`/jmap`,
  `urn:stalwart:jmap`, methods `x:<Object>/get|set|query`) — the same API the web admin uses.
- Data: `~/srv/stalwart/data/` (RocksDB, mode 700). Blobs, search index and in-memory store use
  the `Default` backends, i.e. the same RocksDB. Back up by stopping the service and copying the folder, or `stalwart --config ... --export <dir>`; verify the hourly Kopia snapshot covers `~/srv/stalwart`.
- Log: `~/Library/Logs/stalwart.log` (Stdout tracer, level info, no ANSI; launchd does not rotate it).
- Service: `~/Library/LaunchAgents/com.almaorb.mac.stalwart.plist` (RunAtLoad, KeepAlive,
  env `STALWART_HOSTNAME=mail.almaorb.com`). Runs as marco, not root.
  - start: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.almaorb.mac.stalwart.plist`
  - restart: `launchctl kickstart -k gui/$(id -u)/com.almaorb.mac.stalwart`
  - stop: `launchctl bootout gui/$(id -u)/com.almaorb.mac.stalwart`
  - never `launchctl submit`.

### Why RocksDB

Single machine, single node: RocksDB is the upstream default and the backend Stalwart is tuned
and CI-tested on for embedded use; it handles blobs + full-text search in the same store and
needs no external service. SQLite also works but is the less exercised path for large mail
volumes and full-text search. FoundationDB/Postgres/Redis are for clusters, not needed here.

## Ports (all bound to 127.0.0.1 only)

| Port | Listener name | Protocol | Notes |
|------|---------------|----------|-------|
| 12525 | `smtp-relay-in` | SMTP inbound (MX traffic) | **PROXY protocol required** from 127.0.0.1 (`overrideProxyTrustedNetworks`). Connections without a PROXY v1/v2 header are dropped. STARTTLS offered (self-signed). No AUTH. |
| 10587 | `submission` | SMTP submission | AUTH PLAIN/LOGIN, STARTTLS offered; plaintext AUTH allowed (loopback only). |
| 10993 | `imaps` | IMAP implicit TLS | Self-signed cert (Stalwart's built-in fallback). |
| 10143 | `imap` | IMAP + STARTTLS | Plaintext LOGIN allowed (`Imap.allowPlainTextAuth=true`, loopback only). |
| 14190 | `sieve` | ManageSieve | STARTTLS. |
| 18080 | `http` | HTTP: JMAP, web admin `/admin`, account portal `/account`, CalDAV/CardDAV/WebDAV | Plain HTTP. |

Why PROXY on 12525: Stalwart's default SMTP rules key on `local_port == 25` (SPF/DKIM/DMARC
verification, Authentication-Results, EHLO checks, "auth required unless port 25"). With PROXY,
`local_port` is the *destination* port in the header, so the edge sends `... <client-ip> <edge-ip>
<src-port> 25` and all inbound defaults apply unchanged, with the real client IP.

## Non-default settings (set via JMAP during setup)

```json
NetworkListener x6 as in the table above (bind {"127.0.0.1:<port>": true})
MtaRoute: {"@type":"Local","name":"local"},
          {"@type":"Relay","name":"vps-relay","host":"127.0.0.1","port":12599,"protocol":"smtp"}
MtaOutboundStrategy.route: if is_local_domain(rcpt_domain) then 'local' else 'vps-relay'
MtaStageAuth.saslMechanisms: if local_port != 25 then [plain, login, oauthbearer, xoauth2] else false
MtaStageAuth.require: local_port != 25          (default)
Imap.allowPlainTextAuth: true
SystemSettings.defaultHostname: mail.almaorb.com ; default domain learnvibe.ai
```

**Outbound is held**: `vps-relay` points at 127.0.0.1:12599 where nothing listens, so every
non-local message stays in the queue and retries (verified: `delivery.connect-error ...
remotePort = 12599`, `queue.rescheduled`). Nothing is delivered from the residential IP.
Held mail DSNs after 1 day and expires after 3 days. Note: an unknown route name falls back to
direct MX delivery in Stalwart (`get_route_or_default`), so keep the route name exact.

## How it was set up (for a rebuild from scratch)

1. Start with a missing config.json → bootstrap mode, recovery HTTP on `[::]:$STALWART_RECOVERY_MODE_PORT`
   (used 18080) with `STALWART_RECOVERY_ADMIN=admin:<temp>`; call `x:Bootstrap/set` on id
   `singleton` (defaultHostname, defaultDomain=learnvibe.ai, requestTlsCertificate=false,
   generateDkimKeys=true, RocksDb path, Stdout tracer). It writes config.json, creates the
   domain, schedules DKIM generation and returns the permanent admin's username + password.
   Caveat: the recovery listener binds all interfaces for those minutes.
2. Restart with `STALWART_RECOVERY_MODE=1` (same temp admin) and create the listeners/routes/
   settings above. Creating listeners **before** the first normal start matters: on a normal
   start Stalwart inserts default listeners on `[::]` 25/465/993/995/4190/443/8080 if none exist.
3. Load the launchd agent (normal mode; the remaining safe defaults — roles, queues, spam rules —
   are inserted on this first normal start). Then create accounts with `x:Account/set`
   (`{"@type":"User","name":"info","domainId":<id>,"roles":{"@type":"User"},
   "credentials":{"0":{"@type":"Password","secret":"..."}}}`). Lists/expression matches are
   JSON objects keyed by index (`{"0": {...}}`), maps are `{"key": true}`.

## Accounts and Keychain items (passwords never in files)

| Keychain service | Account | What |
|------------------|---------|------|
| `stalwart-admin` | `admin` | Admin password. Login name is **`admin@learnvibe.ai`** (in the item's comment). Web admin: http://127.0.0.1:18080/admin |
| `stalwart-info@learnvibe.ai` | `info@learnvibe.ai` | Mailbox |
| `stalwart-appreview@learnvibe.ai` | `appreview@learnvibe.ai` | Mailbox |

Read one: `security find-generic-password -s stalwart-admin -w`.

DKIM: Stalwart generated `v1-ed25519-20261027` and `v1-rsa-20261027` for learnvibe.ai (automatic
DKIM management, it rotates them). The full zone (`x:Domain/get` property `dnsZoneFile`) is in
`phase-2-vps-edge.md`.

## Local proof (2026-10-26)

info@ → appreview@ via submission 127.0.0.1:10587 (STARTTLS+AUTH and plaintext AUTH), read back
via IMAP 10143 (STARTTLS and plaintext), IMAPS 10993 and JMAP `Email/query`+`Email/get` on 18080.
Message arrived DKIM-signed (ed25519). 12525 accepted a PROXY v1 session for
appreview@learnvibe.ai, refused relaying to gmail.com (`550 5.7.1 Relay not allowed`) and dropped a
connection without PROXY header. Re-checked after `launchctl kickstart -k`.

Note: the JMAP session advertises `apiUrl: https://mail.almaorb.com/jmap/` (the hostname); local
JMAP clients must use http://127.0.0.1:18080/jmap until phase 2 publishes the HTTPS endpoint.

## Alma Hub

Hub (`~/code/alma-hub/crates/overlook-provider`) speaks IMAP + SMTP (and POP3); no JMAP. Its TLS
uses webpki roots only (no self-signed), but it allows `Security::None` for localhost. Settings:

- Incoming: IMAP, host `127.0.0.1`, port `10143`, security `None`, user `info@learnvibe.ai`
- Outgoing: SMTP, host `127.0.0.1`, port `10587`, security `None`, user `info@learnvibe.ai`
- Password: Keychain `stalwart-info@learnvibe.ai`.
After phase 2 (public cert on mail.almaorb.com): IMAP `mail.almaorb.com:993` TLS and SMTP `:465`
TLS or `:587` STARTTLS.
