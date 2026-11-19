/* login.js - log in and go to the right dashboard */

/** If the user is already logged in with a valid token, skip the login form. */
function redirectIfAlreadyLoggedIn() {
    const token = getToken();
    const user = getLoggedInUser();
    if (token && user && !isTokenExpired(token)) {
        goToDashboardForRole(user.role);
    }
}

/** Show a message left by another page (e.g. "session expired"). */
function showSavedLoginMessage() {
    const savedMessage = sessionStorage.getItem(LOGIN_MESSAGE_KEY);
    if (savedMessage) {
        showMessage("login-message", savedMessage, "info");
        sessionStorage.removeItem(LOGIN_MESSAGE_KEY);
    }
}

/** Send email + password to the API and save the returned token. */
async function handleLoginSubmit(event) {
    event.preventDefault();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!email || !password) {
        showMessage("login-message", "Please enter your email and password.", "error");
        return;
    }

    try {
        const loginResult = await runWithButtonDisabled(document.getElementById("login-button"), () =>
            apiRequest("/auth/login", "POST", { email: email, password: password }, { sendToken: false })
        );
        saveLoginSession(loginResult.access_token, loginResult.user);
        goToDashboardForRole(loginResult.user.role);
    } catch (error) {
        showMessage("login-message", error.message, "error");
    }
}

/** Fill the form with a test account when its link is clicked. */
function fillTestAccount(event) {
    const accountButton = event.target.closest("[data-email]");
    if (!accountButton) {
        return;
    }
    document.getElementById("email").value = accountButton.dataset.email;
    document.getElementById("password").value = accountButton.dataset.password;
}

redirectIfAlreadyLoggedIn();
showSavedLoginMessage();
document.getElementById("login-form").addEventListener("submit", handleLoginSubmit);
document.querySelector(".test-accounts").addEventListener("click", fillTestAccount);
