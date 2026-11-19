/* =====================================================================
   ui.js - small helpers shared by all pages (badges, dates, header, notifications)
   ===================================================================== */

const COMPLAINT_STATUSES = ["Open", "In Progress", "Need More Info", "Resolved", "Closed", "Escalated"];
const PRIORITY_LEVELS = ["Low", "Medium", "High", "Critical"];
const CATEGORIES = [
    "Network/Wi-Fi", "Projector", "Lab Computer", "Printer",
    "Classroom Equipment", "Electrical", "General Maintenance", "Other",
];

// Same rules as STAFF_ALLOWED_TRANSITIONS in the backend (the backend still checks them)
const STAFF_ALLOWED_TRANSITIONS = {
    "Open": ["In Progress", "Need More Info"],
    "In Progress": ["Resolved", "Need More Info"],
    "Need More Info": ["In Progress"],
    "Escalated": ["In Progress", "Resolved", "Need More Info"],
};

const HISTORY_ACTION_LABELS = {
    created: "Complaint created",
    status_changed: "Status changed",
    priority_changed: "Priority changed",
    info_requested: "More information requested",
    student_replied: "Student replied",
    confirmed: "Student confirmed the fix",
    reopened: "Complaint reopened",
    sla_reminder: "SLA reminder sent",
    escalated: "Escalated (SLA breached)",
    grouped: "Grouped into common incident",
};

/** Make text safe to put inside innerHTML (stops HTML/script injection). */
function escapeHtml(text) {
    if (text === null || text === undefined) {
        return "";
    }
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

/** "In Progress" -> "in-progress" (used for CSS class names). */
function toCssClassName(text) {
    return String(text).toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

/** Format an ISO date like "12 Mar 2026, 10:30". */
function formatDateTime(isoDate) {
    if (!isoDate) {
        return "-";
    }
    return new Date(isoDate).toLocaleString(undefined, {
        day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
}

/** Show how much SLA time is left, e.g. "in 3h" or "overdue by 2h". */
function formatSlaRemaining(complaint) {
    if (["Resolved", "Closed"].includes(complaint.status)) {
        return '<span class="muted">Done</span>';
    }
    const millisecondsLeft = new Date(complaint.sla_due_at) - new Date();
    const hoursLeft = Math.round(Math.abs(millisecondsLeft) / 3600000);
    const readableTime = hoursLeft >= 48 ? `${Math.round(hoursLeft / 24)}d` : `${hoursLeft}h`;
    if (millisecondsLeft < 0) {
        return `<span class="overdue-text">Overdue ${readableTime}</span>`;
    }
    return `in ${readableTime}`;
}

/** True when an active complaint is past its SLA deadline. */
function isComplaintOverdue(complaint) {
    return !["Resolved", "Closed"].includes(complaint.status) && new Date(complaint.sla_due_at) < new Date();
}

function createStatusBadge(status) {
    return `<span class="badge status-${toCssClassName(status)}">${escapeHtml(status)}</span>`;
}

function createPriorityBadge(priority) {
    return `<span class="badge priority-${toCssClassName(priority)}">${escapeHtml(priority)}</span>`;
}

function createCommonIncidentTag(complaint) {
    if (complaint.incident_group_id) {
        return `<span class="badge tag-common-incident" title="Verified by staff">Incident group #${complaint.incident_group_id}</span>`;
    }
    if (complaint.is_possible_common_incident) {
        return '<span class="badge tag-common-incident" title="Same category and location as other open complaints">Possible Common Incident</span>';
    }
    return "";
}

/** Build <option> tags for a select box. */
function createOptions(values, placeholderText) {
    const placeholder = placeholderText ? `<option value="">${escapeHtml(placeholderText)}</option>` : "";
    return placeholder + values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
}

/** Show a coloured message inside an element. type = "success" | "error" | "info". */
function showMessage(elementId, text, type = "info") {
    const messageElement = document.getElementById(elementId);
    if (!messageElement) {
        return;
    }
    messageElement.className = `message-box message-${type}`;
    messageElement.textContent = text;
    messageElement.classList.remove("hidden");
}

function hideMessage(elementId) {
    const messageElement = document.getElementById(elementId);
    if (messageElement) {
        messageElement.classList.add("hidden");
    }
}

/** Disable a button while a request runs, so it cannot be clicked twice. */
async function runWithButtonDisabled(button, task) {
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = "Please wait...";
    try {
        return await task();
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}

/* ---------------- Complaint table (staff + admin) ---------------- */

/** Build the small "change status" control for one table row. */
function createQuickStatusControl(complaint) {
    const allowedStatuses = STAFF_ALLOWED_TRANSITIONS[complaint.status] || [];
    if (allowedStatuses.length === 0) {
        return '<span class="muted">Waiting for student</span>';
    }
    return `
        <div class="quick-update">
            <select data-quick-status-for="${complaint.id}" aria-label="New status for complaint ${complaint.id}">
                ${createOptions(allowedStatuses, "Change to...")}
            </select>
            <button class="button button-primary button-small" data-quick-save="${complaint.id}">Save</button>
        </div>`;
}

/** Render a list of complaints as a responsive table. */
function renderComplaintTable(containerElement, complaints, showQuickUpdate) {
    if (complaints.length === 0) {
        containerElement.innerHTML = '<div class="empty-state">No complaints match these filters.</div>';
        return;
    }
    const tableRows = complaints.map((complaint) => `
        <tr>
            <td data-label="#">${complaint.id}</td>
            <td data-label="Title">
                <a href="complaint-details.html?id=${complaint.id}">${escapeHtml(complaint.title)}</a>
                <div class="badge-row">${createCommonIncidentTag(complaint)}</div>
            </td>
            <td data-label="Location">${escapeHtml(complaint.location)}</td>
            <td data-label="Category">${escapeHtml(complaint.category)}</td>
            <td data-label="Team">${escapeHtml(complaint.assigned_team)}</td>
            <td data-label="Priority">${createPriorityBadge(complaint.priority)}</td>
            <td data-label="Status">${createStatusBadge(complaint.status)}</td>
            <td data-label="SLA">${formatSlaRemaining(complaint)}</td>
            ${showQuickUpdate ? `<td data-label="Update">${createQuickStatusControl(complaint)}</td>` : ""}
        </tr>`).join("");

    containerElement.innerHTML = `
        <div class="table-wrapper">
            <table class="data-table responsive-table">
                <thead>
                    <tr>
                        <th>#</th><th>Title</th><th>Location</th><th>Category</th><th>Team</th>
                        <th>Priority</th><th>Status</th><th>SLA</th>
                        ${showQuickUpdate ? "<th>Update</th>" : ""}
                    </tr>
                </thead>
                <tbody>${tableRows}</tbody>
            </table>
        </div>`;
}

/**
 * Listen for "Save" clicks in a complaint table and update the status.
 * "Need More Info" needs a question, so it opens the details page instead.
 */
function enableQuickStatusUpdates(containerElement, messageElementId, onUpdated) {
    containerElement.addEventListener("click", async (event) => {
        const saveButton = event.target.closest("[data-quick-save]");
        if (!saveButton) {
            return;
        }
        const complaintId = saveButton.dataset.quickSave;
        const statusSelect = containerElement.querySelector(`[data-quick-status-for="${complaintId}"]`);
        const newStatus = statusSelect.value;

        if (!newStatus) {
            showMessage(messageElementId, "Choose a new status first.", "error");
            return;
        }
        if (newStatus === "Need More Info") {
            window.location.href = `complaint-details.html?id=${complaintId}#request-info`;
            return;
        }
        try {
            await runWithButtonDisabled(saveButton, () =>
                apiRequest(`/complaints/${complaintId}/status`, "PATCH", { new_status: newStatus })
            );
            showMessage(messageElementId, `Complaint #${complaintId} moved to "${newStatus}".`, "success");
            onUpdated();
        } catch (error) {
            showMessage(messageElementId, error.message, "error");
        }
    });
}

/* ---------------- Header + notifications ---------------- */

/** Draw the top bar: logo, user name, notifications bell, logout. */
function renderAppHeader(user) {
    const headerElement = document.getElementById("app-header");
    const teamText = user.team ? ` - ${user.team} team` : "";
    headerElement.className = "app-header";
    headerElement.innerHTML = `
        <div class="app-header-inner">
            <a class="brand" href="${DASHBOARD_PAGE_BY_ROLE[user.role]}">
                <span class="brand-logo">CF</span>
                <span class="brand-name">Campus<span>Fix</span></span>
            </a>
            <div class="header-actions">
                <div class="user-chip">
                    <strong>${escapeHtml(user.full_name)}</strong>
                    <span class="muted">${escapeHtml(user.role)}${escapeHtml(teamText)}</span>
                </div>
                <div class="notification-wrapper">
                    <button class="notification-button" id="notification-button" aria-label="Notifications">
                        &#128276;<span class="notification-count hidden" id="notification-count"></span>
                    </button>
                    <div class="notification-panel hidden" id="notification-panel"></div>
                </div>
                <button class="button button-secondary button-small" id="logout-button">Log out</button>
            </div>
        </div>`;

    document.getElementById("logout-button").addEventListener("click", logout);
    document.getElementById("notification-button").addEventListener("click", toggleNotificationPanel);
    document.addEventListener("click", (event) => {
        if (!event.target.closest(".notification-wrapper")) {
            document.getElementById("notification-panel").classList.add("hidden");
        }
    });
    loadNotifications();
}

function toggleNotificationPanel() {
    document.getElementById("notification-panel").classList.toggle("hidden");
}

/** Fetch the user's notifications and show them in the bell dropdown. */
async function loadNotifications() {
    const panelElement = document.getElementById("notification-panel");
    const countElement = document.getElementById("notification-count");
    try {
        const notifications = await apiRequest("/notifications");
        const unreadCount = notifications.filter((notification) => !notification.is_read).length;

        countElement.textContent = unreadCount;
        countElement.classList.toggle("hidden", unreadCount === 0);

        const notificationItems = notifications.length === 0
            ? '<div class="notification-empty">No notifications yet.</div>'
            : notifications.map((notification) => `
                <button class="notification-item ${notification.is_read ? "" : "unread"}"
                        data-notification-id="${notification.id}"
                        data-complaint-id="${notification.complaint_id || ""}">
                    ${escapeHtml(notification.message)}
                    <small>${formatDateTime(notification.created_at)}</small>
                </button>`).join("");

        panelElement.innerHTML = `
            <div class="notification-panel-header">
                <strong>Notifications</strong>
                <button class="link-button" id="mark-all-read-button">Mark all read</button>
            </div>
            ${notificationItems}`;

        document.getElementById("mark-all-read-button").addEventListener("click", async () => {
            await apiRequest("/notifications/read-all", "PATCH");
            loadNotifications();
        });
        panelElement.querySelectorAll("[data-notification-id]").forEach((item) => {
            item.addEventListener("click", () => openNotification(item.dataset.notificationId, item.dataset.complaintId));
        });
    } catch (error) {
        panelElement.innerHTML = `<div class="notification-empty">${escapeHtml(error.message)}</div>`;
    }
}

/** Mark a notification as read and open its complaint. */
async function openNotification(notificationId, complaintId) {
    try {
        await apiRequest(`/notifications/${notificationId}/read`, "PATCH");
    } catch (error) {
        // Not important if this fails; still open the complaint
    }
    if (complaintId) {
        window.location.href = `complaint-details.html?id=${complaintId}`;
    } else {
        loadNotifications();
    }
}
