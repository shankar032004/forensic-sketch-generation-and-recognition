/**
 * Signup Page — Handle user registration.
 */

const API_BASE = '';

const signupForm = document.getElementById('signup-form');
const signupBtn = document.getElementById('signup-btn');

signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    // ── Client-side validation ───────────────────────────────────────
    if (!username || !email || !password || !confirmPassword) {
        showToast('Please fill in all fields.', 'error');
        return;
    }

    if (username.length < 3) {
        showToast('Username must be at least 3 characters.', 'error');
        return;
    }

    if (password.length < 6) {
        showToast('Password must be at least 6 characters.', 'error');
        return;
    }

    if (password !== confirmPassword) {
        showToast('Passwords do not match.', 'error');
        return;
    }

    signupBtn.disabled = true;
    signupBtn.textContent = '⏳ Creating account…';

    try {
        const response = await fetch(`${API_BASE}/api/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password }),
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        showToast('Account created! Redirecting to login…', 'success');
        setTimeout(() => {
            window.location.href = '/login.html';
        }, 1000);

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        signupBtn.disabled = false;
        signupBtn.textContent = '✨ Create Account';
    }
});

// ── Toast ────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}
