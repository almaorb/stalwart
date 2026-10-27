"""Set the VPS (almaorb.dev 0.16) list of domains relayed to the Mac: to-mac domain list in MtaOutboundStrategy.route and MtaStageRcpt.allowRelaying. Usage: vps_route.py dom1 dom2 ..."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vps_jmap as vps
doms = sys.argv[1:]
cond = " || ".join(f"rcpt_domain == '{d}'" for d in doms)
cur = vps.call([["x:MtaOutboundStrategy/get",{"ids":["singleton"]},"1"],["x:MtaStageRcpt/get",{"ids":["singleton"]},"2"]])["methodResponses"]
route = cur[0][1]["list"][0]["route"]; relay = cur[1][1]["list"][0]["allowRelaying"]
assert route["match"]["0"]["then"] == "'to-mac'", route
route["match"]["0"]["if"] = cond
base = "!is_empty(authenticated_as) || local_port == 12527"
assert relay["else"].startswith(base), relay
relay["else"] = base + " || " + cond
r = vps.call([["x:MtaOutboundStrategy/set",{"update":{"singleton":{"route":route}}},"1"],["x:MtaStageRcpt/set",{"update":{"singleton":{"allowRelaying":relay}}},"2"]])
print(json.dumps(r["methodResponses"]))
after = vps.call([["x:MtaOutboundStrategy/get",{"ids":["singleton"],"properties":["route"]},"1"],["x:MtaStageRcpt/get",{"ids":["singleton"],"properties":["allowRelaying"]},"2"]])["methodResponses"]
print(json.dumps(after[0][1]["list"][0]["route"])); print(json.dumps(after[1][1]["list"][0]["allowRelaying"]))
print("Now apply it: ssh almaorb.dev sudo systemctl restart stalwart  (0.16 reads this config at start)")
