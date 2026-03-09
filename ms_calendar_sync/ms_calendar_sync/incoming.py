import frappe
from ms_calendar_sync.ms_calendar_sync import graph


@frappe.whitelist()
def pull_latest(top=50):
    """Pull latest Microsoft calendar events into ERPNext Event."""
    settings = frappe.get_single("Microsoft Calendar Settings")
    user = settings.sync_user or frappe.session.user

    data = graph.get(
        user,
        f"/me/events?$top={int(top)}&$orderby=lastModifiedDateTime desc"
    )

    created = 0
    updated = 0

    for ev in data.get("value", []):
        ms_id = ev.get("id")
        subject = ev.get("subject") or "No Subject"
        start = (ev.get("start") or {}).get("dateTime")
        end = (ev.get("end") or {}).get("dateTime")
        body_preview = ev.get("bodyPreview") or ""
        ical_uid = ev.get("iCalUId")

        if not ms_id:
            continue

        name = frappe.db.get_value("Event", {"ms_event_id": ms_id}, "name")

        if name:
            doc = frappe.get_doc("Event", name)
            doc.ms_skip_push = 1
            doc.subject = subject
            doc.description = body_preview
            doc.status = "Open"
            doc.event_type = "Public"
            doc.owner = user
            doc.ms_source = "M365"

            if start:
                doc.starts_on = start
            if end:
                doc.ends_on = end
            if ical_uid:
                doc.ms_ical_uid = ical_uid

            doc.save(ignore_permissions=True)
            updated += 1

        else:
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
            doc.insert(ignore_permissions=True)
            created += 1

    frappe.db.commit()
    return {"created": created, "updated": updated}

