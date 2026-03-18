import frappe
from ms_calendar_sync.ms_calendar_sync import graph

TZ = "Asia/Dubai"


def _map_attendees(doc):
    attendees = []

    for row in (doc.event_participants or []):
        email = None

        if row.reference_doctype == "User":
            email = frappe.db.get_value("User", row.reference_docname, "email")

        elif row.reference_doctype == "Employee":
            user_id = frappe.db.get_value("Employee", row.reference_docname, "user_id")
            if user_id:
                email = frappe.db.get_value("User", user_id, "email")

        elif row.email:
            email = row.email

        if not email:
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
        if getattr(doc, "custom_ms_skip_push", 0):
            return

        user = _event_user(doc)

        if getattr(doc, "custom_ms_event_id", None):
            return

        res = graph.post(user, "/me/events", _payload(doc))
        doc.db_set("custom_ms_event_id", res.get("id"))
        doc.db_set("custom_ms_ical_uid", res.get("iCalUId"))
        doc.db_set("custom_ms_source", "ERPNext")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "MS Event Push Error")


def on_update(doc, method=None):
    try:
        if getattr(doc, "custom_ms_skip_push", 0):
            return

        user = _event_user(doc)
        ms_event_id = getattr(doc, "custom_ms_event_id", None)

        if not ms_event_id:
            return

        graph.patch(user, f"/me/events/{ms_event_id}", _payload(doc))

    except Exception:
        frappe.log_error(frappe.get_traceback(), "MS Event Update Error")


def on_trash(doc, method=None):
    try:
        if getattr(doc, "custom_ms_skip_push", 0):
            return

        user = _event_user(doc)
        ms_event_id = getattr(doc, "custom_ms_event_id", None)

        if not ms_event_id:
            return

        graph.delete(user, f"/me/events/{ms_event_id}")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "MS Event Delete Error")