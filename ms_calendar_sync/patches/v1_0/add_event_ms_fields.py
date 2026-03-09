import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    fields = {
        "Event": [
            {
                "fieldname": "ms_event_id",
                "label": "MS Event ID",
                "fieldtype": "Small Text",
                "insert_after": "subject",
                "read_only": 1,
            },
            {
                "fieldname": "ms_ical_uid",
                "label": "MS iCal UID",
                "fieldtype": "Small Text",
                "insert_after": "ms_event_id",
                "read_only": 1,
            },
            {
                "fieldname": "ms_source",
                "label": "MS Source",
                "fieldtype": "Select",
                "options": "ERPNext\nM365",
                "insert_after": "ms_ical_uid",
                "read_only": 1,
            },
            {
                "fieldname": "ms_skip_push",
                "label": "MS Skip Push",
                "fieldtype": "Check",
                "insert_after": "ms_source",
                "hidden": 1,
            },
            {
                "fieldname": "ms_last_synced_on",
                "label": "MS Last Synced On",
                "fieldtype": "Datetime",
                "insert_after": "ms_skip_push",
                "read_only": 1,
            },
        ]
    }

    create_custom_fields(fields, ignore_validate=True)
    frappe.db.commit()
