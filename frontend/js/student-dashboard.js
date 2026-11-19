/* student-dashboard.js - list my complaints and create new ones */

const currentStudent = requireLogin(["student"]);
let myComplaints = [];

/** Statuses where the student has something to do. */
function isWaitingForStudent(complaint) {
    return complaint.status === "Need More Info" || complaint.status === "Resolved";
}

/** Draw the four summary cards. */
function renderStudentStats() {
    const countWithStatus = (statuses) => myComplaints.filter((complaint) => statuses.includes(complaint.status)).length;
    const statCards = [
        { label: "Total", value: myComplaints.length, style: "" },
        { label: "Open / In progress", value: countWithStatus(["Open", "In Progress", "Escalated"]), style: "stat-warning" },
        { label: "Needs my action", value: myComplaints.filter(isWaitingForStudent).length, style: "stat-danger" },
        { label: "Closed", value: countWithStatus(["Closed"]), style: "stat-success" },
    ];
    document.getElementById("student-stats").innerHTML = statCards.map((card) => `
        <div class="stat-card ${card.style}">
            <div class="stat-label">${card.label}</div>
            <div class="stat-value">${card.value}</div>
        </div>`).join("");
}

/** Draw the complaint cards, applying the status filter. */
function renderMyComplaints() {
    const selectedStatus = document.getElementById("status-filter").value;
    const visibleComplaints = selectedStatus
        ? myComplaints.filter((complaint) => complaint.status === selectedStatus)
        : myComplaints;
    const listElement = document.getElementById("my-complaints-list");

    if (visibleComplaints.length === 0) {
        listElement.innerHTML = '<div class="empty-state">No complaints here yet. Use the form to report a problem.</div>';
        return;
    }

    listElement.innerHTML = visibleComplaints.map((complaint) => `
        <a class="complaint-card" href="complaint-details.html?id=${complaint.id}">
            <div class="badge-row">
                ${createStatusBadge(complaint.status)}
                ${createPriorityBadge(complaint.priority)}
                ${isWaitingForStudent(complaint) ? '<span class="badge tag-action-needed">Action needed</span>' : ""}
            </div>
            <h3>#${complaint.id} ${escapeHtml(complaint.title)}</h3>
            <div class="complaint-card-meta">
                ${escapeHtml(complaint.category)} &middot; ${escapeHtml(complaint.location)}<br>
                Reported ${formatDateTime(complaint.created_at)} &middot; ${escapeHtml(complaint.assigned_team)} team
            </div>
        </a>`).join("");
}

/** Load my complaints from the API. */
async function loadMyComplaints() {
    try {
        myComplaints = await apiRequest("/complaints/my");
        renderStudentStats();
        renderMyComplaints();
    } catch (error) {
        showMessage("my-complaints-message", error.message, "error");
    }
}

/** Submit the new complaint form and show what the system detected. */
async function handleNewComplaintSubmit(event) {
    event.preventDefault();
    const newComplaint = {
        title: document.getElementById("complaint-title").value.trim(),
        location: document.getElementById("complaint-location").value.trim(),
        description: document.getElementById("complaint-description").value.trim(),
    };

    if (newComplaint.title.length < 5 || newComplaint.location.length < 2 || newComplaint.description.length < 10) {
        showMessage("new-complaint-message",
            "Please fill in all fields (title 5+ characters, description 10+ characters).", "error");
        return;
    }

    try {
        const creationResult = await runWithButtonDisabled(document.getElementById("submit-complaint-button"), () =>
            apiRequest("/complaints", "POST", newComplaint)
        );
        const savedComplaint = creationResult.complaint;
        showMessage(
            "new-complaint-message",
            `Complaint #${savedComplaint.id} submitted. Category: ${savedComplaint.category}, ` +
            `priority: ${savedComplaint.priority}. ${creationResult.message}`,
            "success"
        );
        document.getElementById("new-complaint-form").reset();
        loadMyComplaints();
        loadNotifications();
    } catch (error) {
        showMessage("new-complaint-message", error.message, "error");
    }
}

if (currentStudent) {
    renderAppHeader(currentStudent);
    document.getElementById("status-filter").innerHTML = createOptions(COMPLAINT_STATUSES, "All statuses");
    document.getElementById("status-filter").addEventListener("change", renderMyComplaints);
    document.getElementById("new-complaint-form").addEventListener("submit", handleNewComplaintSubmit);
    loadMyComplaints();
}
