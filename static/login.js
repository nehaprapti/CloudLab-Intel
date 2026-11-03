/**
 * CloudLab Intelligence - Mobile OTP Authentication Controller
 * Manages phone number validation, OTP requests, cooldown countdown,
 * verification submission, and redirection to the main dashboard.
 */

let activePhoneNumber = "";
let cooldownSeconds = 60;
let cooldownInterval = null;

document.addEventListener("DOMContentLoaded", () => {
    // Check if user is already authenticated
    checkExistingAuth();

    setupLoginEventHandlers();
});

async function checkExistingAuth() {
    try {
        const res = await fetch("/api/auth/me");
        if (res.ok) {
            const data = await res.json();
            if (data.authenticated) {
                // Already authenticated, redirect to dashboard
                window.location.href = "/";
            }
        }
    } catch (e) {
        // Continue to login
    }
}

function setupLoginEventHandlers() {
    const sendBtn = document.getElementById("btn-send-otp");
    const verifyBtn = document.getElementById("btn-verify-otp");
    const resendBtn = document.getElementById("btn-resend-otp");
    const changePhoneBtn = document.getElementById("btn-change-phone");
    const toggleRegBtn = document.getElementById("toggle-reg-details");
    const phoneInput = document.getElementById("phone-input");
    const otpInput = document.getElementById("otp-input");

    if (sendBtn) sendBtn.addEventListener("click", handleSendOTP);
    if (verifyBtn) verifyBtn.addEventListener("click", handleVerifyOTP);
    if (resendBtn) resendBtn.addEventListener("click", handleResendOTP);
    if (changePhoneBtn) changePhoneBtn.addEventListener("click", showPhoneStep);

    // Toggle optional registration details
    if (toggleRegBtn) {
        toggleRegBtn.addEventListener("click", () => {
            const box = document.getElementById("optional-reg-box");
            const icon = document.getElementById("reg-toggle-icon");
            if (box) {
                const isHidden = box.classList.contains("hidden");
                box.classList.toggle("hidden", !isHidden);
                if (icon) {
                    icon.style.transform = isHidden ? "rotate(90deg)" : "rotate(0deg)";
                }
            }
        });
    }

    // Enter key handling on phone input
    if (phoneInput) {
        phoneInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                handleSendOTP();
            }
        });

        // Numeric filtering on typing
        phoneInput.addEventListener("input", (e) => {
            e.target.value = e.target.value.replace(/[^\d]/g, "");
            hideAlert();
        });
    }

    // Enter key & auto-submit on OTP input
    if (otpInput) {
        otpInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                handleVerifyOTP();
            }
        });

        otpInput.addEventListener("input", (e) => {
            e.target.value = e.target.value.replace(/[^\d]/g, "");
            hideAlert();
            if (e.target.value.length === 6) {
                // Auto trigger verification when 6 digits are typed
                handleVerifyOTP();
            }
        });
    }
}

function validatePhoneNumber() {
    const cc = document.getElementById("country-code-select").value;
    const rawNumber = document.getElementById("phone-input").value.trim();

    if (!rawNumber) {
        showAlert("Please enter your mobile number.", "error");
        return null;
    }

    if (cc === "+91") {
        let digits = rawNumber.replace(/\D/g, "");
        if (digits.startsWith("0")) digits = digits.substring(1);
        if (digits.length === 12 && digits.startsWith("91")) digits = digits.substring(2);

        if (digits.length !== 10) {
            showAlert("Indian mobile number must be exactly 10 digits.", "error");
            return null;
        }
        if (!"6789".includes(digits[0])) {
            showAlert("Indian mobile number must start with 6, 7, 8, or 9.", "error");
            return null;
        }
        return { countryCode: cc, phoneNumber: digits, fullPhone: `+91${digits}` };
    }

    // General international validation
    const digits = rawNumber.replace(/\D/g, "");
    if (digits.length < 7 || digits.length > 15) {
        showAlert("Please enter a valid mobile number (7-15 digits).", "error");
        return null;
    }
    return { countryCode: cc, phoneNumber: digits, fullPhone: `${cc}${digits}` };
}

async function handleSendOTP() {
    const validated = validatePhoneNumber();
    if (!validated) return;

    const sendBtn = document.getElementById("btn-send-otp");
    setButtonLoading(sendBtn, true, "Sending OTP...");
    hideAlert();

    try {
        const res = await fetch("/api/auth/send-otp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                country_code: validated.countryCode,
                phone_number: validated.phoneNumber
            })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            activePhoneNumber = data.phone_number || validated.fullPhone;
            showOTPStep(data.masked_phone || activePhoneNumber, data.cooldown_seconds || 60);
            showToast(data.message || "OTP sent successfully to your mobile number!", "success");
        } else {
            showAlert(data.error || "Failed to send OTP. Please try again.", "error");
        }
    } catch (e) {
        showAlert("Network error connecting to authentication server. Please check your connection.", "error");
    } finally {
        setButtonLoading(sendBtn, false, "Send Verification OTP");
    }
}

async function handleResendOTP() {
    if (!activePhoneNumber) {
        showPhoneStep();
        return;
    }

    const resendBtn = document.getElementById("btn-resend-otp");
    if (resendBtn) resendBtn.disabled = true;
    hideAlert();

    try {
        const res = await fetch("/api/auth/send-otp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                phone_number: activePhoneNumber
            })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            startCooldownTimer(data.cooldown_seconds || 60);
            showToast(data.message || "New OTP dispatched to your mobile number!", "success");
            const otpInput = document.getElementById("otp-input");
            if (otpInput) {
                otpInput.value = "";
                otpInput.focus();
            }
        } else {
            showAlert(data.error || "Failed to resend OTP. Please try again.", "error");
            if (data.cooldown_remaining) {
                startCooldownTimer(data.cooldown_remaining);
            }
        }
    } catch (e) {
        showAlert("Network error requesting OTP resend.", "error");
    } finally {
        if (resendBtn) resendBtn.disabled = false;
    }
}

async function handleVerifyOTP() {
    const otpInput = document.getElementById("otp-input");
    const submittedOtp = (otpInput ? otpInput.value : "").trim();

    if (!submittedOtp || submittedOtp.length !== 6) {
        showAlert("Please enter the complete 6-digit OTP code.", "error");
        if (otpInput) otpInput.focus();
        return;
    }

    const verifyBtn = document.getElementById("btn-verify-otp");
    setButtonLoading(verifyBtn, true, "Verifying OTP...");
    hideAlert();

    // Optional user registration data if filled
    const nameInput = document.getElementById("user-name-input");
    const regInput = document.getElementById("user-reg-input");
    const userName = nameInput ? nameInput.value.trim() : "";
    const regNo = regInput ? regInput.value.trim() : "";

    try {
        const res = await fetch("/api/auth/verify-otp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                phone_number: activePhoneNumber,
                otp: submittedOtp,
                name: userName,
                reg_no: regNo
            })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            showAlert("Authentication verified! Redirecting to CloudLab...", "success");
            showToast("Welcome to CloudLab Intelligence! Access granted.", "success");
            
            // Redirect after brief visual confirmation
            setTimeout(() => {
                window.location.href = data.redirect_url || "/";
            }, 600);
        } else {
            showAlert(data.error || "Invalid OTP. Please try again.", "error");
            if (otpInput) {
                otpInput.select();
                otpInput.focus();
            }
        }
    } catch (e) {
        showAlert("Network error during verification. Please try again.", "error");
    } finally {
        setButtonLoading(verifyBtn, false, "Verify OTP & Enter CloudLab");
    }
}

function showOTPStep(maskedPhone, cooldownSec) {
    document.getElementById("step-phone").classList.add("hidden");
    const stepOtp = document.getElementById("step-otp");
    stepOtp.classList.remove("hidden");

    document.getElementById("display-masked-phone").innerText = maskedPhone;
    const otpInput = document.getElementById("otp-input");
    if (otpInput) {
        otpInput.value = "";
        otpInput.focus();
    }

    startCooldownTimer(cooldownSec || 60);
    if (window.lucide) lucide.createIcons();
}

function showPhoneStep() {
    if (cooldownInterval) clearInterval(cooldownInterval);
    document.getElementById("step-otp").classList.add("hidden");
    document.getElementById("step-phone").classList.remove("hidden");
    hideAlert();
    const phoneInput = document.getElementById("phone-input");
    if (phoneInput) phoneInput.focus();
}

function startCooldownTimer(seconds) {
    if (cooldownInterval) clearInterval(cooldownInterval);
    cooldownSeconds = seconds;

    const container = document.getElementById("cooldown-container");
    const timerSpan = document.getElementById("cooldown-timer");
    const resendBtn = document.getElementById("btn-resend-otp");

    if (!container || !timerSpan || !resendBtn) return;

    container.classList.remove("hidden");
    resendBtn.classList.add("hidden");
    timerSpan.innerText = cooldownSeconds;

    cooldownInterval = setInterval(() => {
        cooldownSeconds--;
        if (cooldownSeconds <= 0) {
            clearInterval(cooldownInterval);
            container.classList.add("hidden");
            resendBtn.classList.remove("hidden");
        } else {
            timerSpan.innerText = cooldownSeconds;
        }
    }, 1000);
}

function showAlert(message, type = "error") {
    const alertBox = document.getElementById("auth-alert");
    const alertMsg = document.getElementById("auth-alert-msg");
    const alertIcon = document.getElementById("auth-alert-icon");

    if (!alertBox || !alertMsg) return;

    alertMsg.innerText = message;

    if (type === "success") {
        alertBox.className = "mx-6 mt-4 p-3.5 rounded-xl border border-emerald-300 bg-emerald-50 text-emerald-900 text-xs flex items-start gap-2.5 animate-fade-in";
        if (alertIcon) alertIcon.className = "h-4 w-4 flex-shrink-0 mt-0.5 text-emerald-600";
    } else {
        alertBox.className = "mx-6 mt-4 p-3.5 rounded-xl border border-red-300 bg-red-50 text-red-900 text-xs flex items-start gap-2.5 animate-fade-in";
        if (alertIcon) alertIcon.className = "h-4 w-4 flex-shrink-0 mt-0.5 text-red-600";
    }

    if (window.lucide) lucide.createIcons();
    alertBox.classList.remove("hidden");
}

function hideAlert() {
    const alertBox = document.getElementById("auth-alert");
    if (alertBox) alertBox.classList.add("hidden");
}

function setButtonLoading(button, isLoading, text) {
    if (!button) return;
    button.disabled = isLoading;
    if (isLoading) {
        button.innerHTML = `
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>${text}</span>
        `;
    } else {
        const iconName = button.id === "btn-send-otp" ? "send" : "check-circle";
        button.innerHTML = `
            <i data-lucide="${iconName}" class="h-4 w-4"></i>
            <span>${text}</span>
        `;
        if (window.lucide) lucide.createIcons();
    }
}

function showToast(message, type = "success") {
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toast-message");
    const toastIcon = document.getElementById("toast-icon");

    if (!toast || !toastMsg) return;

    toastMsg.innerText = message;

    if (type === "error") {
        toast.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-white border border-red-300 text-red-900 text-xs shadow-xl flex items-center gap-3 animate-fade-in font-semibold";
        if (toastIcon) {
            toastIcon.setAttribute("data-lucide", "alert-circle");
            toastIcon.className = "h-5 w-5 text-red-600";
        }
    } else {
        toast.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-white border border-emerald-300 text-emerald-900 text-xs shadow-xl flex items-center gap-3 animate-fade-in font-semibold";
        if (toastIcon) {
            toastIcon.setAttribute("data-lucide", "check-circle");
            toastIcon.className = "h-5 w-5 text-emerald-600";
        }
    }

    if (window.lucide) lucide.createIcons();
    toast.classList.remove("hidden");

    if (window.loginToastTimeout) clearTimeout(window.loginToastTimeout);
    window.loginToastTimeout = setTimeout(() => {
        toast.classList.add("hidden");
    }, 4000);
}
