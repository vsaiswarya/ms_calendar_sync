import frappe
from . import graph

TZ = "Asia/Dubai"

def _payload(doc):
    return {
        "subject": doc.subject or "No Subject",
        "body": {"contentType": "HTML", "content": doc.description or ""},
        "start": {"dateTime": str(doc.starts_on), "timeZone": TZ},
        "end": {"dateTime": str(doc.ends_on), "timeZone": TZ},
        "location": {"displayName": doc.location or ""},
    }

def after_insert(doc, method=None):
    if doc.ms_skip_push:
        return
    user = frappe.session.user
    if doc.ms_event_id:
        return

    res = graph.post(user, "/me/events", _payload(doc))
    doc.db_set("ms_event_id", res.get("id"))
    doc.db_set("ms_ical_uid", res.get("iCalUId"))
    doc.db_set("ms_source", "ERPNext")

def on_update(doc, method=None):
    if doc.ms_skip_push:
        return
    user = frappe.session.user
    if not doc.ms_event_id:
        return
    graph.patch(user, f"/me/events/{doc.ms_event_id}", _payload(doc))

def on_trash(doc, method=None):
    if doc.ms_skip_push:
        return
    user = frappe.session.user
    if not doc.ms_event_id:
        return
    graph.delete(user, f"/me/events/{doc.ms_event_id}")