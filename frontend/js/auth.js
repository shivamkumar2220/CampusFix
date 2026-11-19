/* =====================================================================
   auth.js - login session helpers (token saved in localStorage)
   ===================================================================== */

const TOKEN_STORAGE_KEY = "campusfix_token";
const USER_STORAGE_KEY = "campusfix_user";
const LOGIN_MESSAGE_KEY = "campusfix_login_message";

const DASHBOARD_PAGE_BY_ROLE = {
    student: "student-dashboard.html",
    staff: "staff-dashboard.html",
    admin: "admin-dashboard.html",
};

/** Save the JWT and the user details after a successful login. */
function saveLoginSession(accessToken, user) {
    localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

/** Return the saved JWT, or null. */
function getToken() {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
}

/** Return the saved user object, or null. */
function getLoggedInUser() {
    const savedUser = localStorage.getItem(USER_STORAGE_KEY);
    return savedUser ? JSON.parse(savedUser) : null;
}

/** Remove the token and user from the browser. */
function clearLoginSession() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
}

/**
 * Read the payload (middle part) of a JWT.
 * A JWT looks like header.payload.signature, each part base64url encoded.
 * We only READ it here; the server is the one that verifies the signature.
 */
function decodeTokenPayload(token) {
    try {
        const payloadPart = token.split(".")[1];
        const base64Text = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
        return JSON.parse(atob(base64Text));
    } catch (error) {
        return null;
    }
}

/** True when the token is missing, unreadable, or its "exp" time has passed. */
function isTokenExpired(token) {
    const payload = token ? decodeTokenPayload(token) : null;
    if (!payload || !payload.exp) {
        return true;
    }
    const currentTimeInSeconds = Date.now() / 1000;
    return payload.exp < currentTimeInSeconds;
}

/** Clear the session and go to the login page, optionally showing a message there. */
function redirectToLogin(message) {
    clearLoginSession();
    if (message) {
        sessionStorage.setItem(LOGIN_MESSAGE_KEY, message);
    }
    window.location.href = "login.html";
}

/** Log out button handler. */
function logout() {
    redirectToLogin("You have been logged out.");
}

/** Open the correct dashboard page for a role. */
function goToDashboardForRole(role) {
    window.location.href = DASHBOARD_PAGE_BY_ROLE[role] || "login.html";
}

/**
 * Call at the top of every protected page.
 * - no token or expired token -> back to login
 * - wrong role for this page  -> to the user's own dashboard
 * Returns the logged-in user when everything is fine.
 * (This is only for user experience - the BACKEND enforces the real security.)
 */
function requireLogin(allowedRoles) {
    const token = getToken();
    const user = getLoggedInUser();

    if (!token || !user) {
        redirectToLogin("Please log in first.");
        return null;
    }
    if (isTokenExpired(token)) {
        redirectToLogin("Your session has expired. Please log in again.");
        return null;
    }
    if (allowedRoles && !allowedRoles.includes(user.role)) {
        goToDashboardForRole(user.role);
        return null;
    }
    return user;
}
