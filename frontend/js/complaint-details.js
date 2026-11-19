/* complaint-details.js - one complaint: info, timeline, messages and role-based actions */

const currentUser = requireLogin(["student", "staff", "admin"]);
const complaintId = Number(new URLSearchParams(window.location.search).get("id"));
const isStaffOrAdmin = currentUser && ["staff", "admin"].includes(currentUser.role);

/* ---------------- Rendering ---------------- */

function renderComplaintSummary(complaint) {
    const groupText = complaint.incident_group_id ? `Complaint #${complaint.incident_group_id}` : "-";
    document.title = `#${complaint.id} ${complaint.title} - CampusFix`;
    document.getElementById("complaint-summary").innerHTML = `
        <div class="badge-row">
            ${createStatusBadge(complaint.status)}
            ${createPriorityBadge(complaint.priority)}
            ${createCommonIncidentTag(complaint)}
        </div>
        <h1 style="margin-top: 10px;">#${complaint.id} ${escapeHtml(complaint.title)}</h1>
        <div class="detail-grid">
            <div class="detail-item"><small>Category</small><span>${escapeHtml(complaint.category)}</span></div>
            <div class="detail-item"><small>Location</small><span>${escapeHtml(complaint.location)}</span></div>
            <div class="detail-item"><small>Assigned team</small><span>${escapeHtml(complaint.assigned_team)}</span></div>
            <div class="detail-item"><small>Reported by</small><span>${escapeHtml(complaint.student_name)}</span></div>
            <div class="detail-item"><small>Reported on</small><span>${formatDateTime(complaint.created_at)}</span></div>
            <div class="detail-item"><small>SLA deadline</small><span>${formatDateTime(complaint.sla_due_at)} (${formatSlaRemaining(complaint)})</span></div>
            <div class="detail-item"><small>Suggested priority</small><span>${escapeHtml(complaint.suggested_priority)}</span></div>
            <div class="detail-item"><small>Incident group</small><span>${groupText}</span></div>
        </div>
        <h3>Description</h3>
        <div class="description-box">${escapeHtml(complaint.description)}</div>`;
}

function describeHistoryEntry(entry) {
    const title = HISTORY_ACTION_LABELS[entry.action] || entry.action;
    const change = entry.old_value || entry.new_value
        ? `: ${escapeHtml(entry.old_value || "-")} &rarr; ${escapeHtml(entry.new_value || "-")}`
        : "";
    return `${escapeHtml(title)}${change}`;
}

function renderTimeline(historyEntries) {
    const timelineElement = document.getElementById("history-timeline");
    if (historyEntries.length === 0) {
        timelineElement.innerHTML = '<li class="muted">No history yet.</li>';
        return;
    }
    timelineElement.innerHTML = historyEntries.map((entry) => `
        <li class="${entry.changed_by ? "" : "timeline-system"}">
            <div class="timeline-title">${describeHistoryEntry(entry)}</div>
            <div class="timeline-meta">${escapeHtml(entry.changed_by_name || "System (SLA job)")} &middot; ${formatDateTime(entry.created_at)}</div>
            ${entry.note ? `<div class="timeline-note">${escapeHtml(entry.note)}</div>` : ""}
        </li>`).join("");
}

const COMMENT_TYPE_LABELS = {
    info_request: "Asked for more information",
    info_reply: "Reply",
    staff_note: "Internal staff note",
    reopen_reason: "Reopen reason",
};

function renderComments(comments) {
    const commentListElement = document.getElementById("comment-list");
    if (comments.length === 0) {
        commentListElement.innerHTML = '<p class="muted">No messages yet.</p>';
        return;
    }
    commentListElement.innerHTML = comments.map((comment) => {
        const cssClass = comment.is_internal ? "comment-internal" : (comment.author_role === "student" ? "comment-student" : "");
        return `
            <div class="comment ${cssClass}">
                <div class="comment-header">
                    <strong>${escapeHtml(comment.author_name)}</strong> (${escapeHtml(comment.author_role)})
                    &middot; ${escapeHtml(COMMENT_TYPE_LABELS[comment.comment_type] || comment.comment_type)}
                    &middot; ${formatDateTime(comment.created_at)}
                </div>
                <div>${escapeHtml(comment.message)}</div>
            </div>`;
    }).join("");
}

/* ---------------- Action panel ---------------- */

function buildStudentActions(complaint) {
    if (complaint.status === "Need More Info") {
        return `
            <div class="action-section">
                <p>Staff need more information from you. Please read their message and reply.</p>
                <form id="reply-form">
                    <div class="form-group">
                        <label for="reply-message">Your reply</label>
                        <textarea id="reply-message" required></textarea>
                    </div>
                    <button class="button button-primary button-full" type="submit">Send reply</button>
                </form>
            </div>`;
    }
    if (complaint.status === "Resolved") {
        return `
            <div class="action-section">
                <p>Staff marked this as fixed. Is the problem really solved?</p>
                <button class="button button-success button-full" id="confirm-button">Yes, it is fixed - close it</button>
            </div>
            <div class="action-section">
                <form id="reopen-form">
                    <div class="form-group">
                        <label for="reopen-reason">Still not working? Tell us why</label>
                        <textarea id="reopen-reason" required></textarea>
                    </div>
                    <button class="button button-danger button-full" type="submit">Reopen complaint</button>
                </form>
            </div>`;
    }
    if (complaint.status === "Closed") {
        return '<p class="muted">This complaint is closed. Thank you for confirming!</p>';
    }
    return '<p class="muted">No action needed from you right now. Staff are working on it - you will get a notification when something changes.</p>';
}

function buildSimilarComplaintsSection(similarComplaints) {
    if (similarComplaints.length === 0) {
        return `
            <div class="action-section">
                <h3>Similar open complaints</h3>
                <p class="muted">None found (same category + location).</p>
            </div>`;
    }
    const similarItems = similarComplaints.map((similar) => `
        <div class="similar-item">
            <span><a href="complaint-details.html?id=${similar.id}">#${similar.id}</a> ${escapeHtml(similar.title)}
                ${createStatusBadge(similar.status)}</span>
            <button class="button button-secondary button-small" data-group-under="${similar.id}">Group under #${similar.id}</button>
        </div>`).join("");
    return `
        <div class="action-section">
            <h3>Similar open complaints</h3>
            <p class="form-hint">Same category and location. Verify they are the same problem before grouping.</p>
            ${similarItems}
        </div>`;
}

function buildStaffActions(complaint, similarComplaints) {
    const allowedStatuses = (STAFF_ALLOWED_TRANSITIONS[complaint.status] || []).filter((status) => status !== "Need More Info");
    const canRequestInfo = (STAFF_ALLOWED_TRANSITIONS[complaint.status] || []).includes("Need More Info");
    const otherPriorities = PRIORITY_LEVELS.filter((priority) => priority !== complaint.priority);

    const statusSection = allowedStatuses.length > 0 ? `
        <div class="action-section">
            <form id="status-form">
                <div class="form-group">
                    <label for="new-status">Change status</label>
                    <select id="new-status" required>${createOptions(allowedStatuses)}</select>
                </div>
                <div class="form-group">
                    <label for="status-note">Note (optional)</label>
                    <input type="text" id="status-note" maxlength="1000" placeholder="e.g. Router restarted">
                </div>
                <button class="button button-primary button-full" type="submit">Update status</button>
            </form>
        </div>` : `
        <div class="action-section"><p class="muted">Status is "${escapeHtml(complaint.status)}" - waiting for the student.</p></div>`;

    const requestInfoSection = canRequestInfo ? `
        <div class="action-section" id="request-info">
            <form id="request-info-form">
                <div class="form-group">
                    <label for="info-question">Ask the student for more information</label>
                    <textarea id="info-question" required placeholder="e.g. Which computer number is affected?"></textarea>
                </div>
                <button class="button button-secondary button-full" type="submit">Request info</button>
            </form>
        </div>` : "";

    return `
        ${statusSection}
        ${requestInfoSection}
        <div class="action-section">
            <form id="priority-form">
                <div class="form-row">
                    <div class="form-group">
                        <label for="new-priority">Override priority</label>
                        <select id="new-priority">${createOptions(otherPriorities)}</select>
                    </div>
                    <div class="form-group">
                        <label for="priority-reason">Reason</label>
                        <input type="text" id="priority-reason" required maxlength="500">
                    </div>
                </div>
                <button class="button button-secondary button-full" type="submit">Save priority</button>
            </form>
        </div>
        <div class="action-section">
            <form id="note-form">
                <div class="form-group">
                    <label for="staff-note">Internal note (hidden from student)</label>
                    <textarea id="staff-note" required></textarea>
                </div>
                <button class="button button-secondary button-full" type="submit">Add note</button>
            </form>
        </div>
        ${buildSimilarComplaintsSection(similarComplaints)}`;
}

/* ---------------- Action handlers ---------------- */

/** Run an API action, show the result, and reload the page data. */
async function performAction(button, successText, apiCall) {
    try {
        await runWithButtonDisabled(button, apiCall);
        await loadComplaintPage();
        showMessage("action-message", successText, "success");
        loadNotifications();
    } catch (error) {
        showMessage("action-message", error.message, "error");
    }
}

function attachFormHandler(formId, buildRequest) {
    const formElement = document.getElementById(formId);
    if (!formElement) {
        return;
    }
    formElement.addEventListener("submit", (event) => {
        event.preventDefault();
        const submitButton = formElement.querySelector("button[type=submit]");
        const { successText, apiCall, validationError } = buildRequest();
        if (validationError) {
            showMessage("action-message", validationError, "error");
            return;
        }
        performAction(submitButton, successText, apiCall);
    });
}

function readField(fieldId) {
    return document.getElementById(fieldId).value.trim();
}

function attachActionHandlers() {
    attachFormHandler("reply-form", () => {
        const message = readField("reply-message");
        return {
            validationError: message.length < 2 ? "Please write a reply." : null,
            successText: "Reply sent. The complaint is back with staff.",
            apiCall: () => apiRequest(`/complaints/${complaintId}/reply`, "POST", { message: message }),
        };
    });

    attachFormHandler("reopen-form", () => {
        const reason = readField("reopen-reason");
        return {
            validationError: reason.length < 3 ? "Please explain why you are reopening it." : null,
            successText: "Complaint reopened.",
            apiCall: () => apiRequest(`/complaints/${complaintId}/reopen`, "POST", { reason: reason }),
        };
    });

    attachFormHandler("status-form", () => {
        const note = readField("status-note");
        const newStatus = document.getElementById("new-status").value;
        return {
            successText: `Status changed to "${newStatus}".`,
            apiCall: () => apiRequest(`/complaints/${complaintId}/status`, "PATCH",
                { new_status: newStatus, note: note || null }),
        };
    });

    attachFormHandler("request-info-form", () => {
        const question = readField("info-question");
        return {
            validationError: question.length < 2 ? "Please write your question." : null,
            successText: "Question sent to the student.",
            apiCall: () => apiRequest(`/complaints/${complaintId}/request-info`, "POST", { message: question }),
        };
    });

    attachFormHandler("priority-form", () => {
        const reason = readField("priority-reason");
        const newPriority = document.getElementById("new-priority").value;
        return {
            validationError: reason.length < 3 ? "Please give a reason for the new priority." : null,
            successText: `Priority changed to ${newPriority}.`,
            apiCall: () => apiRequest(`/complaints/${complaintId}/priority`, "PATCH",
                { priority: newPriority, reason: reason }),
        };
    });

    attachFormHandler("note-form", () => {
        const note = readField("staff-note");
        return {
            validationError: note.length < 2 ? "Please write a note." : null,
            successText: "Internal note added.",
            apiCall: () => apiRequest(`/complaints/${complaintId}/notes`, "POST", { message: note }),
        };
    });

    const confirmButton = document.getElementById("confirm-button");
    if (confirmButton) {
        confirmButton.addEventListener("click", () =>
            performAction(confirmButton, "Thank you! The complaint is now closed.",
                () => apiRequest(`/complaints/${complaintId}/confirm`, "POST"))
        );
    }

    document.querySelectorAll("[data-group-under]").forEach((groupButton) => {
        groupButton.addEventListener("click", () => {
            const parentComplaintId = Number(groupButton.dataset.groupUnder);
            performAction(groupButton, `Grouped with complaint #${parentComplaintId}.`,
                () => apiRequest(`/complaints/${complaintId}/group`, "POST", { parent_complaint_id: parentComplaintId }));
        });
    });
}

/* ---------------- Loading ---------------- */

async function loadComplaintPage() {
    const [complaint, historyEntries, comments] = await Promise.all([
        apiRequest(`/complaints/${complaintId}`),
        apiRequest(`/complaints/${complaintId}/history`),
        apiRequest(`/complaints/${complaintId}/comments`),
    ]);
    const similarComplaints = isStaffOrAdmin ? await apiRequest(`/complaints/${complaintId}/similar`) : [];

    renderComplaintSummary(complaint);
    renderTimeline(historyEntries);
    renderComments(comments);
    document.getElementById("action-content").innerHTML = isStaffOrAdmin
        ? buildStaffActions(complaint, similarComplaints)
        : buildStudentActions(complaint);
    hideMessage("action-message");
    attachActionHandlers();
}

async function startComplaintDetailsPage() {
    renderAppHeader(currentUser);
    document.getElementById("back-link").href = DASHBOARD_PAGE_BY_ROLE[currentUser.role];

    if (!Number.isInteger(complaintId) || complaintId <= 0) {
        document.getElementById("complaint-summary").innerHTML = '<p class="muted">No complaint selected.</p>';
        return;
    }
    try {
        await loadComplaintPage();
        if (window.location.hash === "#request-info" && document.getElementById("request-info")) {
            document.getElementById("info-question").focus();
        }
    } catch (error) {
        document.getElementById("complaint-summary").innerHTML = "";
        showMessage("page-message", error.message, "error");
    }
}

if (currentUser) {
    startComplaintDetailsPage();
}
