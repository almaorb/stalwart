#!/usr/bin/env python3
"""Copy mailboxes from the VPS Stalwart (almaorb.dev, 0.16) to the Mac Stalwart (1.0), IMAP to IMAP.

Every folder, every message, its flags and its internal date. Idempotent and resumable: what was
copied is remembered per mailbox in ~/srv/stalwart/migration/<address>.json (folder, UIDVALIDITY,
source UIDs), and a folder without a state is first matched against the Mac by Message-ID +
internal date + size, so a lost state file never makes duplicates. Run it again after the
inbound switch to copy the delta.

Access (no user password is read or changed):
  - VPS: Stalwart's master-user login `<address>%admin` with the VPS admin password
    (Keychain `stalwart-vps-admin`, account `admin`), IMAPS mail.almaorb.com:993. Supported in
    0.16 by `UsernameParts` (`%` separates the account from the master user) and the fallback
    admin / Impersonate permission (crates/common/src/auth/authentication.rs).
  - Mac: the mailbox's own password (Keychain `stalwart-<address>`) on 127.0.0.1:10143, else the
    same master login with the Mac admin (Keychain `stalwart-admin`).

Usage:
  migrate-mailboxes.py --dry-run --all            # counts per mailbox and folder, writes nothing
  migrate-mailboxes.py --dry-run info@actionagent.ai
  migrate-mailboxes.py info@actionagent.ai marco@actionagent.ai
  migrate-mailboxes.py --verify info@actionagent.ai   # counts source vs Mac per folder

  migrate-mailboxes.py --prepare dishorb.com          # Mac domain + accounts + postmaster@ + DKIM TXT
  migrate-mailboxes.py --prepare --dry-run dishorb.com # what --prepare would do

--prepare (per domain, idempotent): creates the domain on the Mac (DKIM automatic), every VPS user
account of that domain with a NEW password (Keychain stalwart-<address>; the VPS password is masked by
the server and is never read or changed), the VPS aliases, postmaster@ on info@ (else the first
mailbox), and ADDS the Mac's DKIM selectors to Cloudflare (existing records are never changed).
The inbound switch is separate: scripts/vps-route-to-mac.py + a VPS restart (runbook).
Secrets are never printed.
"""
import argparse
import base64
import imaplib
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.request

VPS_HOST = os.environ.get("VPS_IMAP_HOST", "mail.almaorb.com")
VPS_JMAP = os.environ.get("VPS_JMAP", "https://mail.almaorb.com/jmap")
MAC_HOST, MAC_PORT = "127.0.0.1", int(os.environ.get("MAC_IMAP_PORT", "10143"))
STATE_DIR = os.path.expanduser(os.environ.get("MIGRATION_STATE", "~/srv/stalwart/migration"))
SKIP_DOMAINS = {"almaorb.com", "myhoma.com", "regulusys.com"}  # Google Workspace: never ours
SPECIAL = ("\\Sent", "\\Drafts", "\\Junk", "\\Trash", "\\Archive")

imaplib._MAXLINE = 50_000_000


def keychain(service, account=None, comment=False):
    cmd = ["security", "find-generic-password", "-s", service]
    if account:
        cmd += ["-a", account]
    if not comment:
        cmd.append("-w")
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None
    return p.stdout.strip() if not comment else p.stdout


def mac_admin():
    listing = keychain("stalwart-admin", comment=True) or ""
    m = re.search(r'login=([^"\s;]+)', listing)
    return (m.group(1) if m else "admin"), keychain("stalwart-admin", "admin")


def vps_accounts():
    """Every user mailbox on the VPS, by address (JMAP x:Account, admin login)."""
    pw = keychain("stalwart-vps-admin", "admin")
    body = json.dumps({"using": ["urn:ietf:params:jmap:core", "urn:stalwart:jmap"], "methodCalls": [
        ["x:Account/get", {"properties": ["@type", "emailAddress", "roles"]}, "a"]]}).encode()
    req = urllib.request.Request(VPS_JMAP, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": "Basic " + base64.b64encode(f"admin:{pw}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=30) as r:
        answer = json.loads(r.read())
    out = []
    for a in answer["methodResponses"][0][1]["list"]:
        addr = (a.get("emailAddress") or "").lower()
        if a.get("@type") == "User" and addr and addr.split("@")[1] not in SKIP_DOMAINS:
            out.append(addr)
    return sorted(out)


def q(name):
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_list(lines):
    """[(flags, delimiter, name)] from LIST responses."""
    out = []
    for raw in lines:
        if raw is None:
            continue
        if isinstance(raw, tuple):  # literal name
            head, name = raw
            m = re.match(rb'\((.*?)\) (NIL|"(.*?)") \{\d+\}', head)
            out.append((m.group(1).decode(), (m.group(3) or b"").decode(), name.decode()))
            continue
        m = re.match(rb'\((.*?)\) (NIL|"(.*?)") (.*)$', raw)
        name = m.group(4).decode()
        if name.startswith('"'):
            name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        out.append((m.group(1).decode(), (m.group(3) or b"").decode(), name))
    return out


def special_of(flags):
    for s in SPECIAL:
        if s.lower() in flags.lower():
            return s
    return None


def connect_vps(address):
    m = imaplib.IMAP4_SSL(VPS_HOST, 993, ssl_context=ssl.create_default_context())
    m.login(f"{address}%admin", keychain("stalwart-vps-admin", "admin"))
    return m


def connect_mac(address):
    m = imaplib.IMAP4(MAC_HOST, MAC_PORT)
    own = keychain(f"stalwart-{address}", address)
    if own:
        m.login(address, own)
    else:
        login, pw = mac_admin()
        m.login(f"{address}%{login}", pw)
    return m


FETCH_RE = re.compile(rb'UID (\d+)|FLAGS \((.*?)\)|INTERNALDATE "(.*?)"|RFC822\.SIZE (\d+)')


def fetch_meta(m, uids, want_msgid=False):
    """{uid: (flags, internaldate, size, message_id)} for the selected folder."""
    out = {}
    items = "(UID FLAGS INTERNALDATE RFC822.SIZE" + (" BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])" if want_msgid else ")")
    for i in range(0, len(uids), 500):
        chunk = b",".join(uids[i:i + 500]).decode()
        typ, data = m.uid("FETCH", chunk, items)
        if typ != "OK":
            raise RuntimeError(f"FETCH failed: {data}")
        for part in data:
            head, body = (part[0], part[1]) if isinstance(part, tuple) else (part, b"")
            if not head or b"UID" not in head:
                continue
            uid = flags = date = size = None
            for g in FETCH_RE.finditer(head):
                uid = int(g.group(1)) if g.group(1) else uid
                flags = g.group(2).decode() if g.group(2) is not None else flags
                date = g.group(3).decode() if g.group(3) else date
                size = int(g.group(4)) if g.group(4) else size
            msgid = ""
            if body:
                mm = re.search(rb"(?im)^message-id:\s*(<[^>]*>)", body)
                msgid = mm.group(1).decode(errors="replace") if mm else ""
            out[uid] = (flags or "", date, size or 0, msgid)
    return out


def all_uids(m):
    typ, data = m.uid("SEARCH", None, "ALL")
    return data[0].split() if data and data[0] else []


def load_state(address):
    path = os.path.join(STATE_DIR, f"{address}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(address, state):
    os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{address}.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, path)


def keep_flags(flags):
    return " ".join(f for f in flags.split() if f.lower() != "\\recent")


def folder_map(src_list, dst_list):
    """Source folder name -> Mac folder name (special-use folders by role, the rest by name)."""
    by_role = {special_of(f): n for f, _, n in dst_list if special_of(f)}
    out = {}
    for flags, _, name in src_list:
        if "\\noselect" in flags.lower():
            continue
        role = special_of(flags)
        out[name] = by_role.get(role, name) if role else ("INBOX" if name.upper() == "INBOX" else name)
    return out


def mac_jmap(calls):
    login, pw = mac_admin()
    body = json.dumps({"using": ["urn:ietf:params:jmap:core", "urn:stalwart:jmap"], "methodCalls": calls}).encode()
    req = urllib.request.Request(os.environ.get("MAC_JMAP", "http://127.0.0.1:18080/jmap"), data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": "Basic " + base64.b64encode(f"{login}:{pw}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=60) as r:
        return {t: a for _, a, t in json.loads(r.read())["methodResponses"]}


def vps_jmap(calls):
    pw = keychain("stalwart-vps-admin", "admin")
    body = json.dumps({"using": ["urn:ietf:params:jmap:core", "urn:stalwart:jmap"], "methodCalls": calls}).encode()
    req = urllib.request.Request(VPS_JMAP, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": "Basic " + base64.b64encode(f"admin:{pw}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=60) as r:
        return {t: a for _, a, t in json.loads(r.read())["methodResponses"]}


def query_get(obj, props):
    return [[f"{obj}/query", {}, "q"], [f"{obj}/get", {"#ids": {"resultOf": "q", "name": f"{obj}/query", "path": "/ids"}, "properties": props}, "g"]]


def new_password():
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits + "-_.!"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(24))
        if any(c.isupper() for c in pw) and any(c.islower() for c in pw) and any(c.isdigit() for c in pw):
            return pw


def cloudflare(method, path, body=None):
    token = keychain("cloudflare-api-token")
    req = urllib.request.Request("https://api.cloudflare.com/client/v4" + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")


def prepare(domain, dry_run=False):
    """Mac domain + accounts + aliases + postmaster@ + DKIM TXT in Cloudflare. Idempotent."""
    if domain in SKIP_DOMAINS:
        raise SystemExit(f"{domain} is Google Workspace: never moved")
    out = {"domain": domain, "actions": []}
    act = out["actions"].append
    v = vps_jmap(query_get("x:Domain", ["name"]) + [["x:Account/get", {"properties": ["@type", "name", "domainId", "emailAddress", "aliases"]}, "a"]])
    vdom = {d["id"]: d["name"] for d in v["g"]["list"]}
    users = [a for a in v["a"]["list"] if a.get("@type") == "User" and (a.get("emailAddress") or "").endswith("@" + domain)]
    m = mac_jmap(query_get("x:Domain", ["name"]))
    mac_dom = {d["name"]: d["id"] for d in m["g"]["list"]}
    if domain not in mac_dom:
        act(f"create domain {domain} on the Mac (DKIM automatic)")
        if not dry_run:
            r = mac_jmap([["x:Domain/set", {"create": {"d": {"name": domain, "enable": True, "reportAddressUri": "mailto:postmaster",
                "dkimManagement": {"@type": "Automatic", "algorithms": {"Dkim1Ed25519Sha256": True, "Dkim1RsaSha256": True},
                                   "selectorTemplate": "v{version}-{algorithm}-{date-%Y%m%d}", "rotateAfter": 7776000000,
                                   "retireAfter": 604800000, "deleteAfter": 2592000000}}}}, "d"]])
            mac_dom[domain] = r["d"]["created"]["d"]["id"]
    did = mac_dom.get(domain, "<new>")
    mac_accounts = mac_jmap(query_get("x:Account", ["emailAddress", "aliases"]))["g"]["list"]
    have = {a["emailAddress"].lower() for a in mac_accounts if a.get("emailAddress")}
    has_postmaster = any(al.get("name") == "postmaster" and al.get("domainId") == did for a in mac_accounts for al in (a.get("aliases") or {}).values())
    postmaster_on = None if has_postmaster else ("info@" + domain if any(u["emailAddress"].lower() == "info@" + domain for u in users) else (users[0]["emailAddress"].lower() if users else None))
    for u in users:
        addr = u["emailAddress"].lower()
        aliases = [(al["name"], vdom.get(al["domainId"])) for al in (u.get("aliases") or {}).values()]
        aliases = [(n, d) for n, d in aliases if d == domain]
        if addr == postmaster_on:
            aliases.append(("postmaster", domain))
        if addr in have:
            act(f"{addr}: already on the Mac")
            continue
        act(f"create {addr} (new password → Keychain stalwart-{addr})" + (f", aliases {', '.join(n + '@' + d for n, d in aliases)}" if aliases else ""))
        if dry_run:
            continue
        svc = f"stalwart-{addr}"
        if keychain(svc, addr) is None:
            subprocess.run(["security", "add-generic-password", "-s", svc, "-a", addr, "-j", f"Mac Stalwart mailbox ({domain} moved from the VPS)", "-w", new_password()], check=True)
        pw = keychain(svc, addr)
        acct = {"@type": "User", "name": addr.split("@")[0], "domainId": did, "roles": {"@type": "User"}, "description": addr,
                "credentials": {"0": {"@type": "Password", "secret": pw}},
                "aliases": {str(i): {"enable": True, "name": n, "domainId": did, "description": None} for i, (n, _) in enumerate(aliases)}}
        r = mac_jmap([["x:Account/set", {"create": {"a": acct}}, "a"]])
        if "created" not in r["a"] or "a" not in r["a"]["created"]:
            raise RuntimeError(f"creating {addr} failed: {r['a'].get('notCreated')}")
    # DKIM: add the Mac's selectors (never touch existing records).
    zone = mac_jmap([["x:Domain/get", {"ids": [did], "properties": ["dnsZoneFile"]}, "z"]])["z"]["list"] if did != "<new>" else []
    zone_file = zone[0]["dnsZoneFile"] if zone else ""
    recs = re.findall(r"^(\S+_domainkey\." + re.escape(domain) + r")\. IN TXT (\(.*?\)|\"[^\"]*\")", zone_file, re.S | re.M)
    z = cloudflare("GET", f"/zones?name={domain}")["result"]
    if not z:
        act(f"no Cloudflare zone for {domain}: add the DKIM records by hand")
        return out
    zid = z[0]["id"]
    existing = {r["name"] for r in cloudflare("GET", f"/zones/{zid}/dns_records?per_page=5000")["result"] if r["type"] == "TXT"}
    if did == "<new>":
        act("add the Mac's DKIM selectors to Cloudflare (known after the domain exists)")
    for name, val in recs:
        if name in existing:
            act(f"DKIM {name}: already in Cloudflare")
            continue
        act(f"add TXT {name} to Cloudflare")
        if not dry_run:
            content = "".join(re.findall(r'"([^"]*)"', val))
            r = cloudflare("POST", f"/zones/{zid}/dns_records", {"type": "TXT", "name": name, "content": content, "ttl": 1, "comment": f"Mac Stalwart DKIM ({domain})"})
            if not r.get("success"):
                raise RuntimeError(f"Cloudflare refused {name}: {r.get('errors')}")
    return out


def migrate(address, dry_run=False, verify=False):
    src = connect_vps(address)
    src_list = parse_list(src.list()[1])
    dst = None if dry_run else connect_mac(address)
    dst_list = parse_list(dst.list()[1]) if dst else []
    if dry_run:
        try:
            d = connect_mac(address)
            dst_list = parse_list(d.list()[1])
            d.logout()
        except Exception:
            dst_list = []
    mapping = folder_map(src_list, dst_list)
    state = load_state(address)
    report = []
    for name, target in mapping.items():
        typ, data = src.select(q(name), readonly=True)
        if typ != "OK":
            report.append({"folder": name, "error": "select failed"})
            continue
        uidvalidity = src.response("UIDVALIDITY")[1][0].decode()
        uids = all_uids(src)
        fs = state.get(name, {})
        if fs.get("uidvalidity") not in (None, uidvalidity):
            fs = {}  # the folder was recreated on the VPS: match by content again
        done = set(fs.get("uids", []))
        todo = [u for u in uids if int(u) not in done]
        row = {"folder": name, "to": target, "source": len(uids), "copied_before": len(uids) - len(todo)}
        if dry_run or verify:
            size = sum(v[2] for v in fetch_meta(src, todo).values()) if todo and dry_run else 0
            row.update({"to_copy": len(todo), "bytes_to_copy": size})
            if verify:
                try:
                    d = connect_mac(address)
                    typ, _ = d.select(q(target), readonly=True)
                    row["mac"] = len(all_uids(d)) if typ == "OK" else 0
                    d.logout()
                except Exception as e:
                    row["mac"] = f"error: {e}"
            report.append(row)
            continue
        # Make the Mac folder when it is missing.
        if target not in {n for _, _, n in dst_list}:
            typ, data = dst.create(q(target))
            if typ != "OK":
                raise RuntimeError(f"create {target} failed: {data}")
            dst_list.append(("", "/", target))
        dst.select(q(target))
        # No state yet: skip what is already on the Mac (same Message-ID, date and size).
        present = set()
        if not fs and todo:
            have = fetch_meta(dst, all_uids(dst), want_msgid=True) if all_uids(dst) else {}
            present = {(v[3], v[1], v[2]) for v in have.values()}
        meta = fetch_meta(src, todo, want_msgid=bool(present))
        copied = skipped = 0
        for u in todo:
            uid = int(u)
            flags, date, size, msgid = meta.get(uid, ("", None, 0, ""))
            if present and (msgid, date, size) in present and msgid:
                skipped += 1
            else:
                typ, data = src.uid("FETCH", u.decode(), "(BODY.PEEK[])")
                body = next((p[1] for p in data if isinstance(p, tuple)), None)
                if body is None:
                    report.append({"folder": name, "uid": uid, "error": "message vanished"})
                    continue
                flag_arg = f"({keep_flags(flags)})" if keep_flags(flags) else None
                typ, resp = dst.append(q(target), flag_arg, f'"{date}"' if date else None, body)
                if typ != "OK":
                    raise RuntimeError(f"APPEND to {target} failed: {resp}")
                copied += 1
            done.add(uid)
            if (copied + skipped) % 50 == 0:
                state[name] = {"uidvalidity": uidvalidity, "uids": sorted(done)}
                save_state(address, state)
        state[name] = {"uidvalidity": uidvalidity, "uids": sorted(done)}
        save_state(address, state)
        typ, _ = dst.select(q(target), readonly=True)
        row.update({"copied_now": copied, "skipped_present": skipped, "mac_after": len(all_uids(dst))})
        report.append(row)
    src.logout()
    if dst:
        dst.logout()
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("addresses", nargs="*")
    ap.add_argument("--all", action="store_true", help="every user mailbox on the VPS (Google Workspace domains left out)")
    ap.add_argument("--dry-run", action="store_true", help="count only; write nothing")
    ap.add_argument("--verify", action="store_true", help="source vs Mac counts per folder")
    ap.add_argument("--prepare", action="store_true", help="arguments are domains: make them ready on the Mac")
    args = ap.parse_args()
    if args.prepare:
        for d in args.addresses:
            print(json.dumps(prepare(d.lower(), dry_run=args.dry_run)))
        return
    addresses = [a.lower() for a in args.addresses] or (vps_accounts() if args.all else [])
    if not addresses:
        ap.error("name addresses or --all")
    total = {}
    for a in addresses:
        try:
            rows = migrate(a, dry_run=args.dry_run, verify=args.verify)
        except Exception as e:
            print(json.dumps({"mailbox": a, "error": str(e)[:300]}))
            continue
        print(json.dumps({"mailbox": a, "folders": rows}))
        total[a] = sum(r.get("source", 0) for r in rows)
    print(json.dumps({"total_messages_by_mailbox": total}))


if __name__ == "__main__":
    main()
