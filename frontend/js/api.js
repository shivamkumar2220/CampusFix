/* =====================================================================
   api.js - every call to the backend goes through apiRequest()
   ===================================================================== */

// When the page is served by the backend itself (local uvicorn or the deployed site),
// the API is on the same address, so a relative "/api" works everywhere.
// When the page is opened as a file or from a separate dev server (e.g. port 5500),
// fall back to the local backend on port 8000.
const API_BASE_URL =
    window.location.protocol === "file:" || window.location.port === "5500"
        ? "http://localhost:8000/api"
        : "/api";

/**
 * Turn an error response from FastAPI into one readable sentence.
 * FastAPI sends {"detail": "text"} for HTTPException and
 * {"detail": [{loc, msg}, ...]} for Pydantic validation errors (422).
 */
function extractErrorMessage(responseData, statusCode) {
    if (responseData && typeof responseData.detail === "string") {
        return responseData.detail;
    }
    if (responseData && Array.isArray(responseData.detail)) {
        return responseData.detail
            .map((validationError) => {
                const fieldName = validationError.loc ? validationError.loc[validationError.loc.length - 1] : "field";
                return `${fieldName}: ${validationError.msg}`;
            })
            .join(" | ");
    }
    return `Request failed (status ${statusCode}).`;
}

/**
 * Send a request to the API.
 *   path:   e.g. "/complaints/my"
 *   method: "GET", "POST", "PATCH" ...
 *   body:   a JavaScript object that will be sent as JSON (optional)
 *   options.sendToken: false for login/register
 * Returns the JSON response, or throws an Error with a readable message.
 */
async function apiRequest(path, method = "GET", body = null, options = {}) {
    const sendToken = options.sendToken !== false;
    const headers = { "Content-Type": "application/json" };

    if (sendToken) {
        const token = getToken();
        if (!token || isTokenExpired(token)) {
            redirectToLogin("Your session has expired. Please log in again.");
            throw new Error("Not logged in.");
        }
        headers["Authorization"] = `Bearer ${token}`;
    }

    let response;
    try {
        response = await fetch(API_BASE_URL + path, {
            method: method,
            headers: headers,
            body: body ? JSON.stringify(body) : null,
        });
    } catch (networkError) {
        throw new Error("Cannot reach the server. Please check that the backend is running.");
    }

    // 204 No Content has no JSON body
    const responseData = response.status === 204 ? null : await response.json().catch(() => null);

    if (response.status === 401 && sendToken) {
        redirectToLogin("Your session has expired. Please log in again.");
        throw new Error("Session expired.");
    }
    if (!response.ok) {
        throw new Error(extractErrorMessage(responseData, response.status));
    }
    return responseData;
}
