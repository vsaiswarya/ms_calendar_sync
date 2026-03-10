import frappe
from ms_calendar_sync.ms_calendar_sync import graph

TZ = "Asia/Dubai"


def _map_attendees(doc):
    attendees = []

    for row in (doc.event_participants or []):
        email = getattr(row, "email", None)
        if not email or "@" not in email:
            continue

        attendees.append({
            "emailAddress": {
                "address": email,
                "name": email
            },
            "type": "required"
        })

    return attendees


def _payload(doc):
    return {
        "subject": doc.subject or "No Subject",
        "body": {
            "contentType": "HTML",
            "content": doc.description or ""
        },
        "start": {
            "dateTime": str(doc.starts_on),
            "timeZone": TZ
        },
        "end": {
            "dateTime": str(doc.ends_on),
            "timeZone": TZ
        },
        "location": {
            "displayName": doc.location or ""
        },
        "attendees": _map_attendees(doc)
    }


def _event_user(doc):
    return doc.owner or frappe.session.user


def after_insert(doc, method=None):
    try:
        if getattr(doc, "ms_skip_push", 0):
            return

        user = _event_user(doc)

        if getattr(doc, "ms_event_id", None):
            return

        res = graph.post(user, "/me/events", _payload(doc))
        doc.db_set("ms_event_id", res.get("id"))
        doc.db_set("ms_ical_uid", res.get("iCalUId"))
        doc.db_set("ms_source", "ERPNext")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "MS Event Push Error")


def on_update(doc, method=None):
    try:
        if getattr(doc, "ms_skip_push", 0):
            return

        user = _event_user(doc)
        ms_event_id = getattr(doc, "ms_event_id", None)

        if not ms_event_id:
            return

        graph.patch(user, f"/me/events/{ms_event_id}", _payload(doc))

    except Exception:
        frappe.log_error(frappe.get_traceback(), "MS Event Update Error")


def on_trash(doc, method=None):
    try:
        if getattr(doc, "ms_skip_push", 0):
            return

        user = _event_user(doc)
        ms_event_id = getattr(doc, "ms_event_id", None)

        if not ms_event_id:
            return

        graph.delete(user, f"/me/events/{ms_event_id}")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "MS Event Delete Error")