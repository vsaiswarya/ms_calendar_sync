import frappe
import requests
from datetime import datetime, timedelta

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = "offline_access Calendars.ReadWrite User.Read"

def _settings():
    return frappe.get_single("Microsoft Calendar Settings")

def _token_doc(user):
    name = frappe.db.get_value("Microsoft OAuth Token", {"user": user}, "name")
    if not name:
        frappe.throw("No Microsoft token found for this user. Connect Microsoft first.")
    return frappe.get_doc("Microsoft OAuth Token", name)

def _expired(token_doc):
    if not token_doc.expires_on:
        return True
    return datetime.utcnow() >= token_doc.expires_on

def refresh_access_token(user):
    s = _settings()
    t = _token_doc(user)

    refresh_token = t.get_password("refresh_token")
    if not refresh_token:
        frappe.throw("No refresh token found for this user.")

    url = f"https://login.microsoftonline.com/{s.tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": s.client_id,
        "client_secret": s.get_password("client_secret"),
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": s.redirect_uri,
        "scope": SCOPES,
    }

    r = requests.post(url, data=data, timeout=30)
    if r.status_code >= 400:
        frappe.log_error(
            f"Status: {r.status_code}\nURL: {url}\nBody: {r.text}",
            "MS Refresh Token Error"
        )
        r.raise_for_status()

    j = r.json()

    t.access_token = j.get("access_token")
    if j.get("refresh_token"):
        t.refresh_token = j.get("refresh_token")
    t.expires_on = datetime.utcnow() + timedelta(seconds=int(j.get("expires_in", 3600)) - 60)
    t.save(ignore_permissions=True)
    frappe.db.commit()

    return t.get_password("access_token")

def access_token(user):
    t = _token_doc(user)
    if _expired(t):
        return refresh_access_token(user)

    token = t.get_password("access_token")
    if not token:
        return refresh_access_token(user)

    return token

def _headers(user):
    return {
        "Authorization": f"Bearer {access_token(user)}",
        "Content-Type": "application/json"
    }

def get(user, path, params=None):
    r = requests.get(f"{GRAPH}{path}", headers=_headers(user), params=params, timeout=30)
    if r.status_code >= 400:
        frappe.log_error(
            f"Status: {r.status_code}\nURL: {GRAPH}{path}\nBody: {r.text}",
            "MS Graph GET Error"
        )
        r.raise_for_status()
    return r.json()

def post(user, path, payload):
    r = requests.post(f"{GRAPH}{path}", headers=_headers(user), json=payload, timeout=30)
    if r.status_code >= 400:
        frappe.log_error(
            f"Status: {r.status_code}\nURL: {GRAPH}{path}\nBody: {r.text}",
            "MS Graph POST Error"
        )
        r.raise_for_status()
    return r.json()

def patch(user, path, payload):
    r = requests.patch(f"{GRAPH}{path}", headers=_headers(user), json=payload, timeout=30)
    if r.status_code >= 400:
        frappe.log_error(
            f"Status: {r.status_code}\nURL: {GRAPH}{path}\nBody: {r.text}",
            "MS Graph PATCH Error"
        )
        r.raise_for_status()
    return True

def delete(user, path):
    r = requests.delete(f"{GRAPH}{path}", headers=_headers(user), timeout=30)
    if r.status_code not in (200, 204):
        frappe.log_error(
            f"Status: {r.status_code}\nURL: {GRAPH}{path}\nBody: {r.text}",
            "MS Graph DELETE Error"
        )
        r.raise_for_status()
    return True