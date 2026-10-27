# Runbook: move ALL mail to the Mac, the VPS becomes a pure edge (NOT executed)

Goal (Marco, 2026-10-26): "mail.almaorb.com working on this server [the Mac]". Every mailbox lives in
the Mac's Stalwart 1.0; almaorb.dev (72.60.169.136, mail.almaorb.com) only forwards TCP and sends.

**Needs Marco's OK before running:** the whole cutover (phase C), each domain's inbound switch, the
app SMTP credential change (C6), and anything about almaorb.com. **almaorb.com, myhoma.com and
regulusys.com mail is Google Workspace: never touch their MX/SPF/DKIM, never add them to the Mac.**

## Where things stand (2026-10-26)

| Domain | Mailboxes | Lives on | Inbound path |
|---|---|---|---|
| learnvibe.ai | marco, info (+postmaster), support, appreview | Mac | VPS :25 → route `to-mac` → tunnel → Mac 12526 |
| actionagent.ai | info (+postmaster), marco | Mac (moved, `moved-domains.md`) | same; VPS keeps its accounts for app SMTP AUTH |
| hotelnative.com | info (+postmaster), marco | Mac (moved) | same |
| dishorb.com | info, marco | VPS | VPS local |
| luxura.ai | marco | VPS | VPS local |
| almaorb.com | admin@ (the VPS admin login) | VPS (stray local domain; real mail = Google) | Google MX; the VPS should not claim it |

Dry run of what is left to copy (`scripts/migrate-mailboxes.py --dry-run --all`, 2026-10-26):

| Mailbox | Folders (messages) | To copy |
|---|---|---|
| info@dishorb.com | INBOX 1 | 1 |
| marco@dishorb.com | Drafts 4 | 4 |
| marco@luxura.ai | INBOX 2, Junk Mail 2 | 4 (0.08 MB) |
| info@/marco@actionagent.ai, info@/marco@hotelnative.com | 109 / 450 / 34 / 5 | 0 (already moved) |

`--prepare --dry-run dishorb.com luxura.ai`: create both domains, info@ (+postmaster@) and
marco@dishorb.com, marco@luxura.ai (+postmaster@), new Mac DKIM selectors to Cloudflare.

## Design (simplest robust)

```
internet ──25/465/587/993/4190──▶ VPS haproxy (TCP, send-proxy-v2) ──ssh -R tunnel──▶ Mac Stalwart listeners (PROXY required, real TLS cert)
internet ◀── VPS Stalwart (outbound-only smarthost on 127.0.0.1:12527) ◀── ssh -L 12599 ◀── Mac route vps-relay
HTTPS mail.almaorb.com (Caddy on the VPS) ──▶ tunnel ──▶ Mac 18080 (JMAP, admin, autoconfig); Bulwark → same JMAP
```

- **haproxy** from Ubuntu's archive (`apt install haproxy`, 3.2.x, native, no Docker). It adds the
  PROXY v2 header (systemd-socket-proxyd cannot), so the Mac sees real client IPs and applies its
  port-25 rules (SPF/DKIM/DMARC/RBL on the Mac).
- **Tunnel**: the existing `com.almaorb.mac.stalwart-edge` SSH (autossh-style launchd KeepAlive), with
  more `-R` forwards. Remote ports on VPS loopback: 22525→Mac 12525 (MX, exists), 22465→10465,
  22587→10588, 22993→10994, 24190→14191, 18081→18080. One SSH connection = one failure domain; launchd
  restarts it in ≤10 s and the VPS queues nothing in that time (senders retry SMTP; IMAP clients
  reconnect). WireGuard is the upgrade path if the SSH link proves flaky.
- **Outbound stays as proven today**: Mac → 127.0.0.1:12599 → VPS Stalwart listener 12527 → internet
  from 72.60.169.136 (Gmail: SPF pass, DKIM pass with the Mac's RSA selector, DMARC pass). The VPS
  Stalwart keeps only that listener (+ its HTTP admin on 127.0.0.1:8080); its queue and retries are
  reused. No Postfix needed.
- **TLS on the Mac**: a real certificate for mail.almaorb.com via ACME DNS-01 with the Cloudflare token.
  Use `lego` (Homebrew, native) in a launchd job (twice a day `lego renew`), writing
  `~/srv/stalwart/certs/mail.almaorb.com.{crt,key}`; a Stalwart `x:Certificate` object reads those
  files and `x:Action ReloadTlsCertificates` after renewal. The token only needs DNS edit on the
  almaorb.com zone for the `_acme-challenge.mail` TXT — lego adds and removes only that record (it is
  not a mail record; almaorb.com's Google MX/SPF/DKIM are untouched). Do NOT use Stalwart's own
  automatic DNS management for this: it would manage almaorb.com's mail records.
- **Webmail**: Bulwark's `JMAP_SERVER_URL` stays `https://mail.almaorb.com`; Caddy's `mail.almaorb.com`
  block switches its upstream from the VPS Stalwart (8080) to 127.0.0.1:18081 (the tunnel). The Mac's
  JMAP session already advertises `https://mail.almaorb.com/jmap/`. Keep the branded `/admin`
  `/account` handlers (they serve files, then proxy).

## Phase A — prepare (no user impact; can run any time)

1. Backups: VPS config JSON (`scripts/vps_jmap.py`-style dump of every `x:` object, as
   `~/srv/stalwart/backups/vps-config-*.json`), `sudo cp -a /etc/caddy/Caddyfile
   /etc/caddy/Caddyfile.bak-$(date +%F)-mail-edge`, and a stopped-copy of the VPS data
   (`sudo systemctl stop stalwart; sudo tar -C /opt/workspaces/mail -czf ~/stalwart-db-$(date +%F).tgz db;
   sudo systemctl start stalwart` — 10 s outage, inbound mail is retried by senders) and a Kopia
   snapshot of `~/srv/stalwart` on the Mac.
2. `scripts/migrate-mailboxes.py --prepare dishorb.com luxura.ai` (domains, accounts with new
   passwords in the Keychain, postmaster@, Mac DKIM selectors ADDED in Cloudflare).
3. `scripts/migrate-mailboxes.py info@dishorb.com marco@dishorb.com marco@luxura.ai` (copy;
   `--verify` after). Re-runnable.
4. Mac listeners (JMAP `x:NetworkListener/set`), all `127.0.0.1`, all PROXY required
   (`overrideProxyTrustedNetworks: {"127.0.0.1": true}`): 10465 SMTP implicit TLS (submissions),
   10588 SMTP STARTTLS (submission), 10994 IMAP implicit TLS, 14191 ManageSieve. Keep the current
   10587/10143/10993/14190/12526 for local clients and the current relay.
5. Certificate: `brew install lego`; `CLOUDFLARE_DNS_API_TOKEN=$(security find-generic-password -s
   cloudflare-api-token -w) lego --dns cloudflare -d mail.almaorb.com -m postmaster@learnvibe.ai
   --path ~/srv/stalwart/acme run`; `x:Certificate/set` from those files; launchd
   `com.almaorb.mac.stalwart-cert` for `lego renew` + reload. Check: `openssl s_client -connect
   127.0.0.1:10994 -servername mail.almaorb.com` shows the Let's Encrypt chain.
6. Tunnel: add the `-R` forwards above to `com.almaorb.mac.stalwart-edge.plist`, `launchctl bootout` +
   `bootstrap` it. On the VPS: `ss -ltn | grep -E '2(2525|2465|2587|2993)|24190|18081'`.
7. `sudo apt install haproxy`, write `/etc/haproxy/haproxy.cfg` but keep it **stopped** (ports 25/465/
   587/993/4190 are still Stalwart's):

   ```
   global
     log /dev/log local0
   defaults
     mode tcp
     log global
     option tcplog
     timeout connect 10s
     timeout client 30m
     timeout server 30m
   frontend smtp      bind :25   ; default_backend mac_smtp
   frontend smtps     bind :465  ; default_backend mac_smtps
   frontend submission bind :587 ; default_backend mac_submission
   frontend imaps     bind :993  ; default_backend mac_imaps
   frontend sieve     bind :4190 ; default_backend mac_sieve
   backend mac_smtp       server mac 127.0.0.1:22525 send-proxy-v2
   backend mac_smtps      server mac 127.0.0.1:22465 send-proxy-v2
   backend mac_submission server mac 127.0.0.1:22587 send-proxy-v2
   backend mac_imaps      server mac 127.0.0.1:22993 send-proxy-v2
   backend mac_sieve      server mac 127.0.0.1:24190 send-proxy-v2
   ```
   (one `frontend`/`backend` per line pair in the real file; `haproxy -c -f` must pass.)

   PROXY v2 carries the destination port, so the Mac sees `local_port` 25/465/587/993/4190 and all
   Stalwart defaults keyed on port 25 apply unchanged.

## Phase B — DNS (additive, can precede the cutover)

Via the Cloudflare token (Control ▸ Mail ▸ Fix DNS does exactly this, creates only):

| Domain | MX | SPF | DKIM | DMARC |
|---|---|---|---|---|
| learnvibe.ai | mail.almaorb.com ✓ | `ip4:72.60.169.136` ✓ | Mac selectors ✓ | p=none ✓ |
| actionagent.ai | ✓ | `v=spf1 mx a:mail.almaorb.com ~all` ✓ (allows the edge) | Mac v1-*-20261027 ✓ added | ✓ |
| hotelnative.com | ✓ | `v=spf1 mx -all` ✓ | Mac v1-*-20261027 ✓ added | ✓ |
| dishorb.com | ✓ | `v=spf1 mx a:mail.almaorb.com ~all` ✓ | **add** Mac selectors (prepare) | ✓ (rua dmarc@dishorb.com does not exist: add an alias or change to postmaster@) |
| luxura.ai | ✓ | `v=spf1 mx ~all` ✓ | **add** Mac selectors; **fix**: `v1-ed25519-20260909._domainkey.luxura.ai` holds a DMARC value by mistake (only after OK) | ✓ |
| almaorb.com | **Google — untouched** | untouched | untouched | untouched |

No MX changes at all: every moved domain's MX is already mail.almaorb.com, and that name keeps its IP.
Finding: the VPS's own DKIM selectors (`v1-*-2026…`) are **not published** for actionagent.ai,
hotelnative.com, dishorb.com (DNS has `default._domainkey`) — mail apps send through the VPS today
passes DMARC by SPF only. Optional (OK needed): publish the VPS public keys (readable as `publicKey`
via `x:DkimSignature/get`) as additional TXT records.

## Phase C — cutover (a quiet hour; ~15 minutes; Marco's OK)

1. Final delta: `scripts/migrate-mailboxes.py --all` (copies only what is new).
2. Route the last two domains to the Mac (inbound keeps working through the old path meanwhile):
   `scripts/vps-route-to-mac.py learnvibe.ai actionagent.ai hotelnative.com dishorb.com luxura.ai`,
   `ssh almaorb.dev sudo systemctl restart stalwart`; send a test to each address; delta copy again.
3. Free the public ports on the VPS Stalwart: `x:NetworkListener/set` destroy `smtp` (25),
   `submissions` (465), `imaps` (993), `pop3s` (995), `sieve` (4190); keep `mac-relay-out` (12527) and
   change `http` 8080 to `127.0.0.1:8080`. Then, in one command so the gap is seconds:
   `sudo systemctl restart stalwart && sudo systemctl enable --now haproxy`.
4. Caddy: `mail.almaorb.com` upstream → `127.0.0.1:18081`; `sudo caddy validate --config
   /etc/caddy/Caddyfile && sudo systemctl reload caddy`.
5. VPS local domains: remove almaorb.com, dishorb.com, luxura.ai, actionagent.ai, hotelnative.com
   (accounts first). **Before** removing almaorb.com (it holds `admin@almaorb.com`, the VPS admin
   login), confirm the recovery admin in `/etc/stalwart/recovery-admin.env` logs in to
   `127.0.0.1:8080`, and update Keychain `stalwart-vps-admin` if the login changes. Keep the VPS
   accounts' mail as an archive in the stopped-copy backup (phase A1) — do not delete their data dirs.
   With no local domains left, the `to-mac` route and relaying expressions are no longer needed for
   inbound (haproxy bypasses the VPS Stalwart); leave them, they are harmless.
6. Apps (`almaorb:smtp` integration: actionagent backend/voice `mail.rs`, alma-mobile-server
   `mail.rs`) authenticate as marco@actionagent.ai on 465. After step 3 that reaches the **Mac**, so
   their secret must become the Mac password (Keychain `stalwart-marco@actionagent.ai`). Update their
   secret store in the same window (Marco's OK), then send one test mail from each app.
7. Hub: `almaorb_mail_config` → `{"imap_host":"mail.almaorb.com","imap_port":993,"imap_security":"tls",
   "smtp_host":"mail.almaorb.com","smtp_port":465,"smtp_security":"tls"}` only if Hub should go through
   the edge (loopback keeps working on this Mac and is faster; leave it).

### Checks after the cutover

- From outside (e.g. Gmail) to one address per domain → Mac INBOX; headers show the real sender IP
  (PROXY works) and `spf=pass dkim=pass` from the Mac's Authentication-Results.
- `openssl s_client -connect mail.almaorb.com:993` → Let's Encrypt cert for mail.almaorb.com; log in
  with an IMAP client; `:465` and `:587 -starttls smtp` AUTH works with the Mac password.
- Outbound to Gmail: `dkim=pass` (Mac selector), `spf=pass` (72.60.169.136), `dmarc=pass`.
- https://webmail.almaorb.com logs in to a Mac mailbox; https://mail.almaorb.com/admin is the Mac's.
- `ssh almaorb.dev 'journalctl -u haproxy --since -10m'` shows sessions to `mac`.

## Rollback

- Phase C step 3–4 (edge): `sudo systemctl disable --now haproxy`; restore the VPS listeners from the
  phase A1 config backup (`x:NetworkListener/set` create with the saved values) and `sudo systemctl
  restart stalwart`; restore the Caddyfile backup and reload Caddy. The VPS is then exactly as before:
  routing to the Mac for the moved domains still works through 12526.
- Phase C step 2 (a domain's inbound): `scripts/vps-route-to-mac.py <the domains to keep>` + restart;
  mail that arrived on the Mac meanwhile is copied back with the same script in the other direction or
  forwarded.
- Phase C step 5 (VPS domains removed): recreate from the config backup; restore the data tarball only
  if mail on the VPS is needed again (stop Stalwart, untar over `db`, start).
- Phase C step 6 (apps): put the old secret back (kept in the apps' secret store history / the VPS
  account still exists until step 5 is done — do step 5 last, a day later).
- Certificate/tunnel changes on the Mac are additive and can stay.

## Risks

- **The Mac is now the mail server**: sleep, reboot, network loss or the SSH tunnel dropping = no
  inbound (senders retry for days) and no IMAP for phones. Keep the Mac awake (`pmset`), launchd
  KeepAlive on Stalwart and the tunnel; consider a VPS-side fallback MX (VPS Stalwart as a
  queue-only relay with `to-mac` route) as a later improvement.
- Residential IP never sends: outbound always via the VPS (keep `vps-relay` exact; an unknown route
  name falls back to direct MX delivery).
- Spam/abuse checks happen on the Mac after cutover (real IPs via PROXY); before it, the VPS filters
  and the Mac filters again (double scoring: first test landed in Junk).
- Apps that READ VPS mailboxes over IMAP stop seeing new mail at each domain's inbound switch.
- Contacts/calendars/Sieve scripts on VPS accounts are not copied by the IMAP script
  (info@actionagent.ai used 80 MB on the VPS but has 4.6 MB of mail): export via JMAP/CardDAV/CalDAV
  if they matter.
- DKIM private keys cannot be exported from 0.16 over JMAP (masked `****`); new Mac selectors are
  published instead (old records kept). Exporting them would need the stopped-copy DB read with
  `stalwart --export`.
