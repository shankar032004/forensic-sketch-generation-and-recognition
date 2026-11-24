/**
 * Recognition Page — Frontend logic for face comparison / similarity scoring.
 */

const API_BASE = '';

// ── DOM Elements ─────────────────────────────────────────────────────
const fileInput1 = document.getElementById('file-input-1');
const fileInput2 = document.getElementById('file-input-2');
const preview1 = document.getElementById('preview-1');
const preview2 = document.getElementById('preview-2');
const uploadLabel1 = document.getElementById('upload-label-1');
const uploadLabel2 = document.getElementById('upload-label-2');
const uploadZone1 = document.getElementById('upload-zone-1');
const uploadZone2 = document.getElementById('upload-zone-2');
const compareBtn = document.getElementById('compare-btn');
const gaugeSection = document.getElementById('gauge-section');
const gaugeArc = document.getElementById('gauge-arc');
const simNumber = document.getElementById('similarity-number');
const matchVerdict = document.getElementById('match-verdict');
const placeholder = document.getElementById('compare-placeholder');
const loadingSpinner = document.getElementById('loading-spinner');

const searchDbBtn = document.getElementById('search-db-btn');
const placeholderText = document.getElementById('placeholder-text');
const spinnerText = document.getElementById('spinner-text');

let image1Base64 = null;
let image2Base64 = null;

// ── File Uploads ─────────────────────────────────────────────────────
fileInput1.addEventListener('change', (e) => handleUpload(e, 1));
fileInput2.addEventListener('change', (e) => handleUpload(e, 2));

// Drag & drop for both zones
[uploadZone1, uploadZone2].forEach((zone, idx) => {
    const num = idx + 1;
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            loadFileAsBase64(file, num);
        }
    });
});

function handleUpload(e, num) {
    const file = e.target.files[0];
    if (!file) return;
    loadFileAsBase64(file, num);
}

function loadFileAsBase64(file, num) {
    const reader = new FileReader();
    reader.onload = (evt) => {
        const dataUrl = evt.target.result;
        const b64 = dataUrl.split(',')[1];

        if (num === 1) {
            image1Base64 = b64;
            preview1.src = dataUrl;
            preview1.style.display = 'block';
            uploadLabel1.style.display = 'none';
            uploadZone1.classList.add('has-image');
            searchDbBtn.disabled = false;
        } else {
            image2Base64 = b64;
            preview2.src = dataUrl;
            preview2.style.display = 'block';
            uploadLabel2.style.display = 'none';
            uploadZone2.classList.add('has-image');
        }

        // Enable compare button when both images are loaded
        compareBtn.disabled = !(image1Base64 && image2Base64);
    };
    reader.readAsDataURL(file);
}

// ── Search Database ───────────────────────────────────────────────────
searchDbBtn.addEventListener('click', async () => {
    if (!image1Base64) {
        showToast('Please upload a sketch first.', 'error');
        return;
    }

    searchDbBtn.disabled = true;
    searchDbBtn.textContent = '⏳ Searching…';
    spinnerText.textContent = 'Searching database…';
    loadingSpinner.classList.add('active');
    placeholder.style.display = 'none';
    gaugeSection.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: image1Base64 }),
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Update UI with search results
        const similarity = data.similarity;
        const percent = Math.round(similarity * 100);

        // Use the match status from the backend
        const isMatch = data.match || false;
        animateGauge(percent, isMatch);

        if (data.filename) {
            preview2.src = data.image_url;
            preview2.style.display = 'block';
            uploadLabel2.style.display = 'none';
            uploadZone2.classList.add('has-image');
        } else {
            preview2.style.display = 'none';
            uploadLabel2.style.display = 'block';
            uploadZone2.classList.remove('has-image');
        }

        matchVerdict.textContent = data.message;
        matchVerdict.className = `match-verdict ${isMatch ? 'match' : 'no-match'}`;

        gaugeSection.style.display = 'flex';
        showToast('Search complete!', 'success');

    } catch (error) {
        showToast(error.message, 'error');
        placeholder.style.display = '';
    } finally {
        searchDbBtn.disabled = false;
        searchDbBtn.textContent = '📂 Search Database';
        loadingSpinner.classList.remove('active');
    }
});

// ── Compare ──────────────────────────────────────────────────────────
compareBtn.addEventListener('click', async () => {
    if (!image1Base64 || !image2Base64) {
        showToast('Please upload both images.', 'error');
        return;
    }

    compareBtn.disabled = true;
    compareBtn.textContent = '⏳ Comparing…';
    spinnerText.textContent = 'Comparing faces…';
    loadingSpinner.classList.add('active');
    placeholder.style.display = 'none';
    gaugeSection.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/api/recognize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image1: image1Base64,
                image2: image2Base64,
            }),
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Animate gauge
        const similarity = data.similarity;
        const percent = Math.round(similarity * 100);
        animateGauge(percent, data.match);

        // Show verdict
        matchVerdict.textContent = data.message;
        matchVerdict.className = `match-verdict ${data.match ? 'match' : 'no-match'}`;

        gaugeSection.style.display = 'flex';
        showToast(data.message, data.match ? 'success' : 'info');

    } catch (error) {
        showToast(`Comparison failed: ${error.message}`, 'error');
        placeholder.style.display = '';
    } finally {
        compareBtn.disabled = false;
        compareBtn.textContent = '🔎 Manual Compare';
        loadingSpinner.classList.remove('active');
    }
});

// ── Gauge Animation ──────────────────────────────────────────────────
function animateGauge(percent, isMatch) {
    const circumference = 2 * Math.PI * 70; // r=70
    const offset = circumference - (percent / 100) * circumference;

    // Color based on score
    let color;
    if (percent >= 70) color = 'var(--accent-green)';
    else if (percent >= 40) color = 'var(--accent-amber)';
    else color = 'var(--accent-red)';

    gaugeArc.style.stroke = color;
    gaugeArc.style.strokeDasharray = circumference;

    // Animate after a short delay
    requestAnimationFrame(() => {
        gaugeArc.style.strokeDashoffset = offset;
    });

    // Animate number
    animateNumber(simNumber, percent, color);
}

function animateNumber(element, target, color) {
    element.style.color = color;
    let current = 0;
    const step = Math.max(1, Math.floor(target / 60));
    const interval = setInterval(() => {
        current += step;
        if (current >= target) {
            current = target;
            clearInterval(interval);
        }
        element.textContent = `${current}%`;
    }, 20);
}

// ── Toast ────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

// ── Load user info & setup logout ────────────────────────────────────
(async function loadUser() {
    try {
        const res = await fetch(`${API_BASE}/api/auth/me`);
        const data = await res.json();
        if (data.authenticated) {
            const el = document.getElementById('nav-username');
            if (el) el.textContent = `👤 ${data.user.username}`;
        }
    } catch (e) { /* ignore */ }
})();

document.getElementById('logout-btn')?.addEventListener('click', async () => {
    try {
        await fetch(`${API_BASE}/api/auth/logout`, { method: 'POST' });
        window.location.href = '/login.html';
    } catch (e) {
        window.location.href = '/login.html';
    }
});
