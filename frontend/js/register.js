/* register.js - create a student account, then log in automatically */

/** Check the form in the browser first (the backend checks again with Pydantic). */
function validateRegistrationForm(fullName, email, password, confirmPassword) {
    if (fullName.length < 2) {
        return "Please enter your full name.";
    }
    if (!email.includes("@")) {
        return "Please enter a valid email address.";
    }
    if (password.length < 8) {
        return "Password must be at least 8 characters.";
    }
    if (password !== confirmPassword) {
        return "The two passwords do not match.";
    }
    return null;
}

/** Register, then log in with the same details and open the student dashboard. */
async function handleRegisterSubmit(event) {
    event.preventDefault();
    const fullName = document.getElementById("full-name").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirm-password").value;

    const validationError = validateRegistrationForm(fullName, email, password, confirmPassword);
    if (validationError) {
        showMessage("register-message", validationError, "error");
        return;
    }

    try {
        await runWithButtonDisabled(document.getElementById("register-button"), async () => {
            await apiRequest("/auth/register", "POST",
                { full_name: fullName, email: email, password: password }, { sendToken: false });
            const loginResult = await apiRequest("/auth/login", "POST",
                { email: email, password: password }, { sendToken: false });
            saveLoginSession(loginResult.access_token, loginResult.user);
        });
        goToDashboardForRole("student");
    } catch (error) {
        showMessage("register-message", error.message, "error");
    }
}

document.getElementById("register-form").addEventListener("submit", handleRegisterSubmit);
