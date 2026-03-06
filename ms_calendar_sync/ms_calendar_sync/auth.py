import frappe, requests
from urllib.parse import urlencode
from datetime import datetime, timedelta

SCOPES = "offline_access Calendars.ReadWrite User.Read"

def _settings():
    s = frappe.get_single("Microsoft Calendar Settings")
    if not s.enabled:
        frappe.throw("Microsoft Calendar Settings is disabled")
    for k in ("tenant_id", "client_id", "client_secret", "redirect_uri"):
        if not getattr(s, k, None):
            frappe.throw(f"Missing setting: {k}")
    return s

@frappe.whitelist()
def get_login_url(user=None):
    s = _settings()
    user = user or frappe.session.user

    params = {
        "client_id": s.client_id,
        "response_type": "code",
        "redirect_uri": s.redirect_uri,
        "response_mode": "query",
        "scope": SCOPES,
        "state": user,
    }

    from urllib.parse import urlencode
    return f"https://login.microsoftonline.com/{s.tenant_id}/oauth2/v2.0/authorize?{urlencode(params)}"



@frappe.whitelist(allow_guest=True)
def callback():
    """Azure redirect comes here. Stores tokens in Microsoft OAuth Token for the user in state."""
    code = frappe.form_dict.get("code")
    user = frappe.form_dict.get("state")

    if not code or not user:
        return "Missing code/state"

    s = _settings()
    token_url = f"https://login.microsoftonline.com/{s.tenant_id}/oauth2/v2.0/token"

    payload = {
        "client_id": s.client_id,
        "client_secret": s.get_password("client_secret"),
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": s.redirect_uri,
        "scope": SCOPES,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    r = requests.post(token_url, data=payload, headers=headers, timeout=30)
    if r.status_code >= 400:
        frappe.log_error(
            f"Status: {r.status_code}\nURL: {token_url}\nBody: {r.text}",
            "MS OAuth Token Error",
        )
        frappe.throw("Token exchange failed. Open Error Log: MS OAuth Token Error")

    j = r.json()

    frappe.log_error(f"Saving Microsoft token for ERPNext user: {user}", "MS OAuth Save User")

    name = frappe.db.get_value("Microsoft OAuth Token", {"user": user}, "name")

    if name:
        doc = frappe.get_doc("Microsoft OAuth Token", name)
        doc.access_token = j.get("access_token")
        doc.refresh_token = j.get("refresh_token")
        doc.expires_on = datetime.utcnow() + timedelta(seconds=int(j.get("expires_in", 3600)) - 60)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": "Microsoft OAuth Token",
            "user": user,
            "access_token": j.get("access_token"),
            "refresh_token": j.get("refresh_token"),
            "expires_on": datetime.utcnow() + timedelta(seconds=int(j.get("expires_in", 3600)) - 60),
        })
        doc.insert(ignore_permissions=True)

    frappe.db.commit()

    frappe.log_error(f"Saved token row: {doc.name} for user: {user}", "MS OAuth Save Success")

    return {"message": "Microsoft connected successfully. You can close this window."}