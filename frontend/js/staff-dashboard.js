/* staff-dashboard.js - complaints assigned to my team, with filters and quick status updates */

const currentStaff = requireLogin(["staff", "admin"]);
let assignedComplaints = [];

/** Draw the summary cards for the whole team (ignores filters). */
function renderStaffStats(allTeamComplaints) {
    const countWithStatus = (status) => allTeamComplaints.filter((complaint) => complaint.status === status).length;
    const statCards = [
        { label: "Open", value: countWithStatus("Open"), style: "" },
        { label: "In progress", value: countWithStatus("In Progress"), style: "" },
        { label: "Need more info", value: countWithStatus("Need More Info"), style: "stat-warning" },
        { label: "Escalated", value: countWithStatus("Escalated"), style: "stat-danger" },
        { label: "Overdue (SLA)", value: allTeamComplaints.filter(isComplaintOverdue).length, style: "stat-danger" },
        { label: "Resolved", value: countWithStatus("Resolved") + countWithStatus("Closed"), style: "stat-success" },
    ];
    document.getElementById("staff-stats").innerHTML = statCards.map((card) => `
        <div class="stat-card ${card.style}">
            <div class="stat-label">${card.label}</div>
            <div class="stat-value">${card.value}</div>
        </div>`).join("");
}

/** Apply the text search (status/priority/category filters are done by the API). */
function renderAssignedTable() {
    const searchText = document.getElementById("search-box").value.trim().toLowerCase();
    const visibleComplaints = assignedComplaints.filter((complaint) =>
        !searchText ||
        complaint.title.toLowerCase().includes(searchText) ||
        complaint.location.toLowerCase().includes(searchText)
    );
    renderComplaintTable(document.getElementById("assigned-complaints-table"), visibleComplaints, true);
}

/** Build "?status=Open&priority=High" from the filter boxes. */
function buildFilterQuery() {
    const queryParameters = new URLSearchParams();
    const filterFields = { status: "status-filter", priority: "priority-filter", category: "category-filter" };
    Object.entries(filterFields).forEach(([parameterName, elementId]) => {
        const selectedValue = document.getElementById(elementId).value;
        if (selectedValue) {
            queryParameters.set(parameterName, selectedValue);
        }
    });
    const queryText = queryParameters.toString();
    return queryText ? `?${queryText}` : "";
}

/** Load the team's complaints (filtered) plus unfiltered numbers for the stat cards. */
async function loadAssignedComplaints() {
    try {
        const filterQuery = buildFilterQuery();
        const [filteredComplaints, allTeamComplaints] = await Promise.all([
            apiRequest(`/complaints/assigned${filterQuery}`),
            filterQuery ? apiRequest("/complaints/assigned") : null,
        ]);
        assignedComplaints = filteredComplaints;
        renderStaffStats(allTeamComplaints || filteredComplaints);
        renderAssignedTable();
    } catch (error) {
        showMessage("staff-message", error.message, "error");
    }
}

function setUpFilters() {
    document.getElementById("status-filter").innerHTML = createOptions(COMPLAINT_STATUSES, "All statuses");
    document.getElementById("priority-filter").innerHTML = createOptions(PRIORITY_LEVELS, "All priorities");
    document.getElementById("category-filter").innerHTML = createOptions(CATEGORIES, "All categories");
    ["status-filter", "priority-filter", "category-filter"].forEach((elementId) =>
        document.getElementById(elementId).addEventListener("change", loadAssignedComplaints)
    );
    document.getElementById("search-box").addEventListener("input", renderAssignedTable);
}

if (currentStaff) {
    renderAppHeader(currentStaff);
    document.getElementById("staff-heading").textContent = currentStaff.team
        ? `${currentStaff.team} Team - Assigned Complaints`
        : "All Complaints";
    setUpFilters();
    document.getElementById("refresh-button").addEventListener("click", () => {
        loadAssignedComplaints();
        loadNotifications();
    });
    enableQuickStatusUpdates(document.getElementById("assigned-complaints-table"), "staff-message", loadAssignedComplaints);
    loadAssignedComplaints();
}
