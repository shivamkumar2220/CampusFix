/* admin-dashboard.js - stats, all complaints, escalated list and user management */

const currentAdmin = requireLogin(["admin"]);
const ROLES = ["student", "staff", "admin"];
const TEAMS = ["IT", "Maintenance"];

/* ---------------- Tabs ---------------- */

function switchTab(tabId) {
    document.querySelectorAll(".tab-button").forEach((button) =>
        button.classList.toggle("active", button.dataset.tab === tabId));
    document.querySelectorAll(".tab-panel").forEach((panel) =>
        panel.classList.toggle("hidden", panel.id !== tabId));
}

/* ---------------- Overview ---------------- */

function renderAdminStats(stats) {
    const averageText = stats.average_resolution_hours === null ? "-" : `${stats.average_resolution_hours}h`;
    const statCards = [
        { label: "Total complaints", value: stats.total_complaints, style: "" },
        { label: "Open", value: stats.open_complaints, style: "stat-warning" },
        { label: "Escalated", value: stats.escalated_complaints, style: "stat-danger" },
        { label: "Resolved / closed", value: stats.resolved_or_closed_complaints, style: "stat-success" },
        { label: "Avg. resolution", value: averageText, style: "" },
        { label: "Users", value: stats.total_users, style: "" },
    ];
    document.getElementById("admin-stats").innerHTML = statCards.map((card) => `
        <div class="stat-card ${card.style}">
            <div class="stat-label">${card.label}</div>
            <div class="stat-value">${card.value}</div>
        </div>`).join("");
}

/** Draw a simple horizontal bar list, e.g. {"Electrical": 4, "Printer": 1}. */
function renderBreakdownBars(elementId, countsByName) {
    const entries = Object.entries(countsByName);
    const container = document.getElementById(elementId);
    if (entries.length === 0) {
        container.innerHTML = '<p class="muted">No data yet.</p>';
        return;
    }
    const largestCount = Math.max(...entries.map(([, count]) => count));
    container.innerHTML = entries.map(([name, count]) => `
        <div class="bar-row" title="${escapeHtml(name)}: ${count} complaint(s)">
            <span>${escapeHtml(name)}</span>
            <div class="bar-track"><div class="bar-fill" style="width: ${(count / largestCount) * 100}%"></div></div>
            <span class="bar-value">${count}</span>
        </div>`).join("");
}

async function loadDashboardStats() {
    const stats = await apiRequest("/dashboard/stats");
    renderAdminStats(stats);
    renderBreakdownBars("breakdown-category", stats.complaints_by_category);
    renderBreakdownBars("breakdown-status", stats.complaints_by_status);
    renderBreakdownBars("breakdown-priority", stats.complaints_by_priority);
    renderBreakdownBars("breakdown-team", stats.complaints_by_team);
}

/* ---------------- Complaints ---------------- */

async function loadAllComplaints() {
    const filterFields = {
        status: "admin-status-filter",
        priority: "admin-priority-filter",
        category: "admin-category-filter",
        team: "admin-team-filter",
    };
    const queryParameters = new URLSearchParams();
    Object.entries(filterFields).forEach(([parameterName, elementId]) => {
        const selectedValue = document.getElementById(elementId).value;
        if (selectedValue) {
            queryParameters.set(parameterName, selectedValue);
        }
    });
    const queryText = queryParameters.toString();
    const complaints = await apiRequest(`/complaints${queryText ? `?${queryText}` : ""}`);
    renderComplaintTable(document.getElementById("all-complaints-table"), complaints, true);
}

async function loadEscalatedComplaints() {
    const escalatedComplaints = await apiRequest("/complaints/escalated");
    document.getElementById("escalated-tab-count").textContent = escalatedComplaints.length ? `(${escalatedComplaints.length})` : "";
    renderComplaintTable(document.getElementById("escalated-complaints-table"), escalatedComplaints, true);
}

/* ---------------- Users ---------------- */

function createSelectedOptions(values, selectedValue, placeholderText) {
    const placeholder = placeholderText !== undefined
        ? `<option value="" ${selectedValue ? "" : "selected"}>${escapeHtml(placeholderText)}</option>` : "";
    return placeholder + values.map((value) =>
        `<option value="${escapeHtml(value)}" ${value === selectedValue ? "selected" : ""}>${escapeHtml(value)}</option>`
    ).join("");
}

function renderUsersTable(users) {
    const userRows = users.map((user) => {
        const isMe = user.id === currentAdmin.id;
        return `
            <tr>
                <td data-label="Name">${escapeHtml(user.full_name)}${isMe ? ' <span class="muted">(you)</span>' : ""}</td>
                <td data-label="Email">${escapeHtml(user.email)}</td>
                <td data-label="Role">
                    <select data-role-for="${user.id}" ${isMe ? "disabled" : ""} aria-label="Role">${createSelectedOptions(ROLES, user.role)}</select>
                </td>
                <td data-label="Team">
                    <select data-team-for="${user.id}" ${isMe ? "disabled" : ""} aria-label="Team">${createSelectedOptions(TEAMS, user.team, "No team")}</select>
                </td>
                <td data-label="Status">${user.is_active ? '<span class="badge status-resolved">Active</span>' : '<span class="badge status-closed">Inactive</span>'}</td>
                <td data-label="Actions">
                    ${isMe ? "" : `
                    <button class="button button-primary button-small" data-save-role="${user.id}">Save role</button>
                    <button class="button ${user.is_active ? "button-danger" : "button-secondary"} button-small"
                            data-toggle-active="${user.id}" data-active="${user.is_active}">
                        ${user.is_active ? "Deactivate" : "Activate"}
                    </button>`}
                </td>
            </tr>`;
    }).join("");

    document.getElementById("users-table").innerHTML = `
        <div class="table-wrapper">
            <table class="data-table responsive-table">
                <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Team</th><th>Status</th><th>Actions</th></tr></thead>
                <tbody>${userRows}</tbody>
            </table>
        </div>`;
}

async function loadUsers() {
    renderUsersTable(await apiRequest("/users"));
}

async function handleUserTableClick(event) {
    const saveRoleButton = event.target.closest("[data-save-role]");
    const toggleActiveButton = event.target.closest("[data-toggle-active]");

    try {
        if (saveRoleButton) {
            const userId = saveRoleButton.dataset.saveRole;
            const role = document.querySelector(`[data-role-for="${userId}"]`).value;
            const team = document.querySelector(`[data-team-for="${userId}"]`).value || null;
            await runWithButtonDisabled(saveRoleButton, () =>
                apiRequest(`/users/${userId}/role`, "PATCH", { role: role, team: team }));
            showMessage("admin-message", "User role updated.", "success");
            loadUsers();
        }
        if (toggleActiveButton) {
            const userId = toggleActiveButton.dataset.toggleActive;
            const makeActive = toggleActiveButton.dataset.active !== "true";
            await runWithButtonDisabled(toggleActiveButton, () =>
                apiRequest(`/users/${userId}/active`, "PATCH", { is_active: makeActive }));
            showMessage("admin-message", makeActive ? "User activated." : "User deactivated.", "success");
            loadUsers();
        }
    } catch (error) {
        showMessage("admin-message", error.message, "error");
    }
}

async function handleCreateUserSubmit(event) {
    event.preventDefault();
    const newUser = {
        full_name: document.getElementById("new-user-name").value.trim(),
        email: document.getElementById("new-user-email").value.trim(),
        password: document.getElementById("new-user-password").value,
        role: document.getElementById("new-user-role").value,
        team: document.getElementById("new-user-team").value || null,
    };
    if (newUser.role === "staff" && !newUser.team) {
        showMessage("admin-message", "Staff users need a team (IT or Maintenance).", "error");
        return;
    }
    try {
        await runWithButtonDisabled(document.getElementById("create-user-button"), () =>
            apiRequest("/users", "POST", newUser));
        showMessage("admin-message", `User ${newUser.email} created.`, "success");
        document.getElementById("create-user-form").reset();
        loadUsers();
    } catch (error) {
        showMessage("admin-message", error.message, "error");
    }
}

/* ---------------- SLA ---------------- */

async function runSlaCheckNow() {
    try {
        const result = await runWithButtonDisabled(document.getElementById("run-sla-button"), () =>
            apiRequest("/dashboard/run-sla-check", "POST"));
        showMessage("admin-message",
            `SLA check done: ${result.complaints_checked} overdue checked, ` +
            `${result.reminders_sent} reminder(s) sent, ${result.complaints_escalated} escalated.`, "info");
        refreshAllAdminData();
        loadNotifications();
    } catch (error) {
        showMessage("admin-message", error.message, "error");
    }
}

/* ---------------- Start ---------------- */

async function refreshAllAdminData() {
    try {
        await Promise.all([loadDashboardStats(), loadAllComplaints(), loadEscalatedComplaints(), loadUsers()]);
    } catch (error) {
        showMessage("admin-message", error.message, "error");
    }
}

function setUpAdminControls() {
    document.querySelectorAll(".tab-button").forEach((button) =>
        button.addEventListener("click", () => switchTab(button.dataset.tab)));

    document.getElementById("admin-status-filter").innerHTML = createOptions(COMPLAINT_STATUSES, "All statuses");
    document.getElementById("admin-priority-filter").innerHTML = createOptions(PRIORITY_LEVELS, "All priorities");
    document.getElementById("admin-category-filter").innerHTML = createOptions(CATEGORIES, "All categories");
    document.getElementById("admin-team-filter").innerHTML = createOptions(TEAMS, "All teams");
    ["admin-status-filter", "admin-priority-filter", "admin-category-filter", "admin-team-filter"].forEach((elementId) =>
        document.getElementById(elementId).addEventListener("change", () =>
            loadAllComplaints().catch((error) => showMessage("admin-message", error.message, "error"))));

    document.getElementById("new-user-role").innerHTML = createOptions(ROLES);
    document.getElementById("new-user-team").innerHTML = createOptions(TEAMS, "No team");
    document.getElementById("create-user-form").addEventListener("submit", handleCreateUserSubmit);
    document.getElementById("users-table").addEventListener("click", handleUserTableClick);
    document.getElementById("run-sla-button").addEventListener("click", runSlaCheckNow);

    const refreshAfterStatusChange = () => refreshAllAdminData();
    enableQuickStatusUpdates(document.getElementById("all-complaints-table"), "admin-message", refreshAfterStatusChange);
    enableQuickStatusUpdates(document.getElementById("escalated-complaints-table"), "admin-message", refreshAfterStatusChange);
}

if (currentAdmin) {
    renderAppHeader(currentAdmin);
    setUpAdminControls();
    refreshAllAdminData();
}
