/**
 * Login Page — Handle user authentication.
 */

const API_BASE = '';

const loginForm = document.getElementById('login-form');
const loginBtn = document.getElementById('login-btn');

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showToast('Please fill in all fields.', 'error');
        return;
    }

    loginBtn.disabled = true;
    loginBtn.textContent = '⏳ Signing in…';

    try {
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        showToast('Login successful! Redirecting…', 'success');
        setTimeout(() => {
            window.location.href = '/dashboard.html';
        }, 500);

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        loginBtn.disabled = false;
        loginBtn.textContent = '🚀 Sign In';
    }
});

// ── Check if already logged in ───────────────────────────────────────
(async function checkAuth() {
    try {
        const res = await fetch(`${API_BASE}/api/auth/me`);
        const data = await res.json();
        if (data.authenticated) {
            window.location.href = '/dashboard.html';
        }
    } catch (e) { /* not logged in */ }
})();

// ── Toast ────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}
