"""JMAP to the VPS Stalwart (https://mail.almaorb.com/jmap) as admin from Keychain stalwart-vps-admin. Never prints secrets."""
import base64, json, subprocess, sys, urllib.request
URL = "https://mail.almaorb.com/jmap"
def call(method_calls):
    pw = subprocess.run(["security","find-generic-password","-s","stalwart-vps-admin","-a","admin","-w"],capture_output=True,text=True,check=True).stdout.strip()
    body = json.dumps({"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":method_calls}).encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={"Content-Type":"application/json","Authorization":"Basic "+base64.b64encode(f"admin:{pw}".encode()).decode()})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: return {"httpError": e.code, "body": e.read().decode()[:2000]}
SECRET_KEYS={"secret","privateKey","password","authSecret","value"}
def scrub(o):
    if isinstance(o,dict): return {k:("<secret>" if k in SECRET_KEYS and v not in (None,{}) else scrub(v)) for k,v in o.items()}
    if isinstance(o,list): return [scrub(x) for x in o]
    return o
if __name__=="__main__":
    calls=json.load(open(sys.argv[1])) if len(sys.argv)>1 else json.load(sys.stdin)
    print(json.dumps(scrub(call(calls)),indent=1))
