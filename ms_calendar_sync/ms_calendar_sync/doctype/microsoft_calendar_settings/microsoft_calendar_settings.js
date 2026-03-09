frappe.ui.form.on("Microsoft Calendar Settings", {
    refresh(frm) {

        frm.add_custom_button("Connect Microsoft", function () {

            frappe.call({
                method: "ms_calendar_sync.ms_calendar_sync.auth.get_login_url",
                args: {
                    user: frappe.session.user
                },
                callback: function (r) {

                    if (r.message) {
                        window.open(r.message, "_blank");
                    } else {
                        frappe.msgprint("Unable to generate Microsoft login URL.");
                    }

                }
            });

        });

        const params = new URLSearchParams(window.location.search);

        if (params.get("connected") === "1") {
            frappe.show_alert({
                message: "Microsoft Calendar connected successfully",
                indicator: "green"
            });
        }

    }
});