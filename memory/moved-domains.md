# Domains moved from the VPS to the Mac (2026-10-26)

Marco, 2026-10-26: "migrate info and marco from the VPS to here on actionagent.ai", then
"hotelnative.com also needs emails". Both domains now live on the Mac Stalwart; the VPS
(almaorb.dev, 0.16.16) is their edge, exactly like learnvibe.ai (`phase-2-vps-edge.md`).

Still on the VPS: dishorb.com, luxura.ai (and the stray local `almaorb.com`, whose real mail is
Google Workspace — never touch almaorb.com / myhoma.com / regulusys.com mail DNS). Full move:
`move-all-mail-to-the-mac.md`.

## What was done

1. **Backup** of the VPS config (JMAP x:* objects, secrets masked by the server):
   `~/srv/stalwart/backups/vps-config-202610262124.json`.
2. **Mac**: `x:Domain/set` actionagent.ai (id c) and hotelnative.com (id d), DKIM Automatic;
   accounts `info@` and `marco@` on each (role User), alias `postmaster@` on `info@`. New
   passwords → Keychain `stalwart-<address>` (the VPS passwords were not read or changed).
3. **DKIM**: the VPS's private keys cannot be exported over JMAP (0.16 masks every secret as
   `****`), and the selectors in DNS did not match the VPS keys anyway (actionagent.ai DNS had
   `default._domainkey`, hotelnative.com `v1-ed25519-20260731`). So the Mac's new selectors
   `v1-ed25519-20261027` and `v1-rsa-20261027` were **added** in Cloudflare for both domains; every
   old record was kept (the VPS still signs what apps send through it).
4. **Mail copied** with `scripts/migrate-mailboxes.py` (IMAP→IMAP; VPS master login
   `<address>%admin`, Mac the mailbox's own login; flags and internal dates kept, checked: same
   \Seen counts and identical date lists in INBOX and Deleted Items). State in
   `~/srv/stalwart/migration/<address>.json`.

   | Mailbox | INBOX | Junk Mail | Sent Items | Deleted Items | Drafts | Total |
   |---|---|---|---|---|---|---|
   | info@actionagent.ai | 74 | 32 | 3 | 0 | 0 | 109 |
   | marco@actionagent.ai | 246 | 65 | 7 | 132 | 0 | 450 |
   | info@hotelnative.com | 12 | 22 | 0 | 0 | 0 | 34 |
   | marco@hotelnative.com | 5 | 0 | 0 | 0 | 0 | 5 |

   Mac counts after = source counts in every folder; the delta run after the switch copied 0.
   Only mail (IMAP) moved: contacts/calendars/Sieve on the VPS accounts were not copied
   (info@actionagent.ai's VPS quota use, 80 MB, is larger than its 4.6 MB of mail).
5. **Inbound switch** on the VPS (`scripts/vps-route-to-mac.py learnvibe.ai actionagent.ai
   hotelnative.com`, then `sudo systemctl restart stalwart`):
   - `MtaOutboundStrategy.route` match 0: `rcpt_domain == 'learnvibe.ai' || rcpt_domain ==
     'actionagent.ai' || rcpt_domain == 'hotelnative.com'` → `'to-mac'` (before `is_local_domain`).
   - `MtaStageRcpt.allowRelaying`: `!is_empty(authenticated_as) || local_port == 12527 || <same>`.
   The domains stay **local domains on the VPS with their accounts**, so RCPT checks still use the
   VPS's account list: a new address made only on the Mac (e.g. `postmaster@`) is refused at the
   VPS until the VPS domain is removed or the address added there too.
6. **Hub**: the four mailboxes added to Marco's Alma Hub (`POST /accounts/almaorb-mail`).

## How apps still send

actionagent's backend/voice `mail.rs` and alma-mobile-server `mail.rs` log in to the VPS
submission (465) as `marco@actionagent.ai` (`almaorb:smtp`). The VPS account and its password are
untouched, so that keeps working (AUTH 235 checked after the switch). What they send to a moved
domain is routed to the Mac. Anything that **reads** these mailboxes on the VPS (IMAP) no longer
sees new mail: point it at the Mac.

## Proof (2026-10-26)

- VPS port 25 → info@/marco@ of both domains: delivered on the Mac (`vps-relay-in` 12526), nothing
  on the VPS. (The first actionagent test landed in Junk because the test itself was spammy:
  no Date, no SPF for almaorb.dev; the hotelnative one with a Date header landed in INBOX.)
- Mac 10587 → marcona@gmail.com from marco@actionagent.ai and marco@hotelnative.com: relayed via
  127.0.0.1:12599 → VPS 12527 → gmail-smtp-in 250. Gmail: `dkim=pass s=v1-rsa-20261027`,
  `spf=pass` (72.60.169.136), `dmarc=pass`; ed25519 shows "neutral (no key)" (Gmail does not do
  ed25519). The VPS adds no DKIM signature of its own on this path.
- dishorb.com / luxura.ai still accepted locally on the VPS (RCPT 250).

## Rollback

Per domain, in this order:
1. `scripts/vps-route-to-mac.py learnvibe.ai [other domains still moved]` then
   `ssh almaorb.dev sudo systemctl restart stalwart` — new mail lands on the VPS again (its
   accounts were never removed).
2. Mail that arrived on the Mac meanwhile: copy it back (the same script with source/destination
   swapped, or forward from Hub).
3. Optional: remove the Mac domain/accounts and the added DKIM TXT records (old records were never
   changed).
