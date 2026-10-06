#!/usr/bin/env python3
"""End-to-end smoke test for the running stack.

Talks to the app exactly as a browser does, so it checks the whole
chain: website -> API -> database. Standard library only.

    python3 scripts/smoke_test.py                      # http://localhost:8000
    python3 scripts/smoke_test.py --base http://localhost:8000 --wait 300

Exit code 0 = every check passed.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PASSED = []


def call(base, method, path, token=None, json_body=None, form=None, timeout=30):
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def check(name, condition, detail=""):
    if not condition:
        print(f"FAIL  {name}  {detail}")
        sys.exit(1)
    PASSED.append(name)
    print(f"ok    {name}")


def wait_until_ready(base, seconds):
    deadline = time.time() + seconds
    last = ""
    while time.time() < deadline:
        try:
            status, body = call(base, "GET", "/api/health", timeout=5)
            if status == 200 and json.loads(body).get("status") == "ok":
                return
            last = f"{status} {body[:120]}"
        except Exception as e:  # connection refused while containers start
            last = repr(e)
        time.sleep(3)
    print(f"FAIL  stack did not become ready within {seconds}s (last: {last})")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--wait", type=int, default=300, help="seconds to wait for start-up")
    a = ap.parse_args()
    base = a.base.rstrip("/")

    print(f"Waiting up to {a.wait}s for {base} ...")
    wait_until_ready(base, a.wait)
    check("API health (website -> API -> database)", True)

    status, body = call(base, "GET", "/")
    check("website home page served", status == 200 and '<div id="root">' in body, f"{status}")
    status, body = call(base, "GET", "/dashboard")
    check("deep link served by the single-page app", status == 200 and '<div id="root">' in body, f"{status}")

    tokens = {}
    for email, password, role in [
        ("rahul@example.com", "customer123", "customer"),
        ("agent@abcfin.com", "agent123", "agent"),
        ("manager@abcfin.com", "manager123", "manager"),
        ("exec@abcfin.com", "exec123", "executive"),
        ("admin@abcfin.com", "admin123", "admin"),
    ]:
        status, body = call(base, "POST", "/api/auth/login", form={"username": email, "password": password})
        ok = status == 200 and json.loads(body)["user"]["role"] == role
        check(f"login as {role} ({email})", ok, f"{status} {body[:200]}")
        tokens[role] = json.loads(body)["access_token"]

    status, _ = call(base, "POST", "/api/auth/login", form={"username": "admin@abcfin.com", "password": "wrong"})
    check("wrong password rejected", status == 401, f"{status}")

    cu, ag, mg, ex, ad = (tokens[r] for r in ["customer", "agent", "manager", "executive", "admin"])

    status, body = call(base, "POST", "/api/tickets", cu,
                        json_body={"subject": "Charged twice", "body": "I was charged twice and I'm upset"})
    t = json.loads(body) if status == 201 else {}
    check("customer raises a ticket (auto-classified)", status == 201 and t.get("category") and t.get("sentiment"),
          f"{status} {body[:200]}")
    tid = t["ticket_id"]
    print(f"      -> category={t['category']} priority={t['priority']} sentiment={t['sentiment']}")

    status, body = call(base, "GET", "/api/tickets/mine", cu)
    check("customer sees own tickets", status == 200 and any(x["ticket_id"] == tid for x in json.loads(body)))

    status, body = call(base, "POST", "/api/assistant/ask", cu, json_body={"query": "how do I block a lost card"})
    check("AI assistant answers from the knowledge base", status == 200 and json.loads(body).get("answer"),
          f"{status} {body[:200]}")

    status, body = call(base, "GET", "/api/tickets/queue", ag)
    check("agent sees the ticket queue", status == 200 and any(x["ticket_id"] == tid for x in json.loads(body)))
    status, body = call(base, "POST", f"/api/tickets/{tid}/messages", ag, json_body={"body": "We have reversed the duplicate charge."})
    check("agent replies (ticket moves to in progress)", status == 200 and json.loads(body)["status"] == "in_progress",
          f"{status} {body[:200]}")
    status, body = call(base, "PATCH", f"/api/tickets/{tid}/status?status=closed", ag)
    check("agent closes the ticket", status == 200 and json.loads(body)["status"] == "closed", f"{status} {body[:200]}")

    for role, tok in [("manager", mg), ("executive", ex)]:
        for path in ["/api/analytics/kpis", "/api/analytics/tickets-by-category",
                     "/api/analytics/sentiment-trend", "/api/analytics/churn-risk"]:
            status, body = call(base, "GET", path, tok)
            check(f"{role} dashboard data {path.rsplit('/', 1)[-1]}", status == 200, f"{status} {body[:200]}")

    status, body = call(base, "GET", "/api/admin/users", ad)
    check("admin lists users", status == 200 and len(json.loads(body)) >= 4)
    email = f"smoke{int(time.time())}@abcfin.com"
    status, body = call(base, "POST", "/api/admin/users", ad,
                        json_body={"name": "Smoke Test", "email": email, "password": "smoke-pass-123", "role": "agent"})
    check("admin creates a user", status == 201, f"{status} {body[:200]}")
    status, body = call(base, "PATCH", f"/api/admin/users/{json.loads(body)['agent_id']}/toggle", ad)
    check("admin disables a user", status == 200 and json.loads(body)["is_active"] is False)

    status, _ = call(base, "GET", "/api/analytics/kpis", cu)
    check("role check: customer blocked from analytics", status == 403, f"{status}")
    status, _ = call(base, "GET", "/api/admin/users", ag)
    check("role check: agent blocked from admin", status == 403, f"{status}")
    status, _ = call(base, "GET", "/api/tickets/queue", ex)
    check("role check: executive blocked from agent queue", status == 403, f"{status}")

    print(f"\nALL {len(PASSED)} CHECKS PASSED")


if __name__ == "__main__":
    main()
