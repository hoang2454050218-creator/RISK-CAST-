"""Fix router root paths from "/" to "" to avoid 307 redirects."""
import re

files = [
    "riskcast/api/routers/orders.py",
    "riskcast/api/routers/payments.py",
    "riskcast/api/routers/customers.py",
    "riskcast/api/routers/routes_api.py",
    "riskcast/api/routers/audit_trail.py",
    "riskcast/api/routers/incidents.py",
    "riskcast/api/routers/signals.py",
]

for f in files:
    with open(f, "r", encoding="utf-8") as fh:
        content = fh.read()
    # @router.get("/", ...) → @router.get("", ...)
    # @router.post("/", ...) → @router.post("", ...)
    new = content.replace('@router.get("/",', '@router.get("",')
    new = new.replace('@router.post("/",', '@router.post("",')
    new = new.replace('@router.get("/")', '@router.get("")')
    new = new.replace('@router.post("/")', '@router.post("")')
    if new != content:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new)
        print(f"Fixed: {f}")
    else:
        print(f"No change: {f}")
