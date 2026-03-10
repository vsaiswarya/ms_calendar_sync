import frappe
from ms_calendar_sync.ms_calendar_sync import graph


def _map_attending_status(attendee):
    status = ((attendee.get("status") or {}).get("response") or "").lower()

    if status == "accepted":
        return "Yes"
    elif status == "declined":
        return "No"
    elif status in ("tentativelyaccepted", "tentative"):
        return "Maybe"

    return ""


def _append_participants(doc, attendees):
    doc.set("event_participants", [])

    for attendee in attendees or []:
        email_obj = attendee.get("emailAddress") or {}
        email = email_obj.get("address")
        if not email:
            continue

        attending = _map_attending_status(attendee)

        # Try to link to ERPNext User first
        user_name = frappe.db.get_value("User", {"email": email}, "name")
        if user_name:
            reference_doctype = "User"
            reference_docname = user_name
        else:
            # Optional: try Contact by email_id if your site uses Contact records
            contact_name = frappe.db.get_value("Contact Email", {"email_id": email}, "parent")
            if contact_name:
                reference_doctype = "Contact"
                reference_docname = contact_name
            else:
                reference_doctype = ""
                reference_docname = ""

        doc.append("event_participants", {
            "reference_doctype": reference_doctype,
            "reference_docname": reference_docname,
            "email": email,
            "attending": attending
        })


def _upsert_event(user, ev):
    ms_id = ev.get("id")
    subject = ev.get("subject") or "No Subject"
    start = (ev.get("start") or {}).get("dateTime")
    end = (ev.get("end") or {}).get("dateTime")
    body_preview = ev.get("bodyPreview") or ""
    ical_uid = ev.get("iCalUId")
    attendees = ev.get("attendees", [])

    if not ms_id:
        return {"created": 0, "updated": 0}

    name = frappe.db.get_value("Event", {"ms_event_id": ms_id}, "name")

    if name:
        doc = frappe.get_doc("Event", name)
        doc.ms_skip_push = 1
        doc.subject = subject
        doc.description = body_preview
        doc.status = "Open"
        doc.event_type = "Public"
        doc.ms_source = "M365"

        if start:
            doc.starts_on = start
        if end:
            doc.ends_on = end
        if ical_uid:
            doc.ms_ical_uid = ical_uid

        _append_participants(doc, attendees)

        doc.save(ignore_permissions=True)
        return {"created": 0, "updated": 1}

    doc = frappe.get_doc({
        "doctype": "Event",
        "subject": subject,
        "description": body_preview,
        "starts_on": start,
        "ends_on": end,
        "status": "Open",
        "event_type": "Public",
        "owner": user,
        "ms_event_id": ms_id,
        "ms_ical_uid": ical_uid,
        "ms_source": "M365",
        "ms_skip_push": 1,
    })

    _append_participants(doc, attendees)

    doc.insert(ignore_permissions=True)
    return {"created": 1, "updated": 0}


@frappe.whitelist()
def pull_latest_for_user(user, top=50):
    data = graph.get(
        user,
        f"/me/events?$top={int(top)}&$orderby=lastModifiedDateTime desc"
    )

    created = 0
    updated = 0

    for ev in data.get("value", []):
        result = _upsert_event(user, ev)
        created += result["created"]
        updated += result["updated"]

    frappe.db.commit()
    return {"created": created, "updated": updated, "user": user}


@frappe.whitelist()
def sync_all_users(top=50):
    users = frappe.get_all("Microsoft OAuth Token", pluck="user")

    total_created = 0
    total_updated = 0
    failed = []

    for user in users:
        try:
            result = pull_latest_for_user(user=user, top=top)
            total_created += result["created"]
            total_updated += result["updated"]
        except Exception:
            failed.append(user)
            frappe.log_error(frappe.get_traceback(), f"MS Calendar Sync Failed - {user}")

    return {
        "created": total_created,
        "updated": total_updated,
        "failed_users": failed,
    }