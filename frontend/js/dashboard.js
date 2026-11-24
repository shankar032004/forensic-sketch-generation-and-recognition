/**
 * Dashboard Page — Display user history with filtering, modals, and delete.
 */

const API_BASE = '';

// ── DOM Elements ─────────────────────────────────────────────────────
const historyGrid = document.getElementById('history-grid');
const emptyState = document.getElementById('empty-state');
const loadMoreContainer = document.getElementById('load-more-container');
const loadMoreBtn = document.getElementById('load-more-btn');
const imageModal = document.getElementById('image-modal');
const modalImage = document.getElementById('modal-image');
const modalInfo = document.getElementById('modal-info');
const modalClose = document.getElementById('modal-close');
const logoutBtn = document.getElementById('logout-btn');

let currentFilter = 'all';
let currentPage = 1;
let totalPages = 1;

// ── Action type labels & icons ───────────────────────────────────────
const TYPE_META = {
    generate: { icon: '🎨', label: 'Generated', color: 'var(--accent-cyan)' },
    edit: { icon: '✏️', label: 'Edited', color: 'var(--accent-amber)' },
    recognize: { icon: '🔎', label: 'Recognized', color: 'var(--accent-purple)' },
};

// ══════════════════════════════════════════════════════════════════════
// LOAD USER INFO
// ══════════════════════════════════════════════════════════════════════

(async function loadUser() {
    try {
        const res = await fetch(`${API_BASE}/api/auth/me`);
        const data = await res.json();
        if (!data.authenticated) {
            window.location.href = '/login.html';
            return;
        }
        document.getElementById('nav-username').textContent = `👤 ${data.user.username}`;
    } catch (e) {
        window.location.href = '/login.html';
    }
})();

// ══════════════════════════════════════════════════════════════════════
// FETCH & RENDER HISTORY
// ══════════════════════════════════════════════════════════════════════

async function fetchHistory(page = 1, append = false) {
    try {
        let url = `${API_BASE}/api/history?page=${page}&limit=12`;
        if (currentFilter !== 'all') {
            url += `&type=${currentFilter}`;
        }

        const res = await fetch(url);
        const data = await res.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load history');
        }

        totalPages = data.pages;
        currentPage = data.page;

        if (!append) {
            historyGrid.innerHTML = '';
        }

        if (data.items.length === 0 && !append) {
            emptyState.style.display = 'flex';
            historyGrid.style.display = 'none';
            loadMoreContainer.style.display = 'none';
        } else {
            emptyState.style.display = 'none';
            historyGrid.style.display = '';

            data.items.forEach(item => {
                historyGrid.appendChild(createHistoryCard(item));
            });

            // Show/hide load more
            if (currentPage < totalPages) {
                loadMoreContainer.style.display = 'flex';
            } else {
                loadMoreContainer.style.display = 'none';
            }
        }

        // Update stats
        updateStats();

    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ── Create a history card ────────────────────────────────────────────
function createHistoryCard(item) {
    const card = document.createElement('div');
    card.className = 'history-card fade-in';
    card.dataset.id = item.id;

    const meta = TYPE_META[item.action_type] || { icon: '📄', label: item.action_type, color: 'var(--text-muted)' };

    const date = new Date(item.created_at);
    const timeStr = date.toLocaleDateString('en-IN', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });

    const thumbnailSrc = item.thumbnail
        ? `data:image/png;base64,${item.thumbnail}`
        : '';

    const promptText = item.prompt ? (item.prompt.length > 80 ? item.prompt.substring(0, 80) + '…' : item.prompt) : 'No description';

    card.innerHTML = `
        <div class="history-card-image" ${thumbnailSrc ? `style="cursor:pointer"` : ''}>
            ${thumbnailSrc
            ? `<img src="${thumbnailSrc}" alt="Thumbnail">`
            : `<div class="history-card-no-image">${meta.icon}</div>`
        }
            <div class="history-card-badge" style="background: ${meta.color}">${meta.icon} ${meta.label}</div>
        </div>
        <div class="history-card-body">
            <p class="history-card-prompt">${promptText}</p>
            <div class="history-card-footer">
                <span class="history-card-time">🕐 ${timeStr}</span>
                <button class="history-card-delete" title="Delete" data-id="${item.id}">🗑️</button>
            </div>
        </div>
    `;

    // Click image to view full size
    const imgArea = card.querySelector('.history-card-image');
    if (thumbnailSrc) {
        imgArea.addEventListener('click', () => openModal(item));
    }

    // Delete button
    card.querySelector('.history-card-delete').addEventListener('click', (e) => {
        e.stopPropagation();
        deleteEntry(item.id, card);
    });

    return card;
}

// ── Update stat counts ───────────────────────────────────────────────
async function updateStats() {
    try {
        const types = ['generate', 'edit', 'recognize'];
        for (const type of types) {
            const res = await fetch(`${API_BASE}/api/history?type=${type}&limit=1`);
            const data = await res.json();
            document.getElementById(`stat-${type}`).textContent = data.total || 0;
        }
    } catch (e) { /* ignore */ }
}

// ══════════════════════════════════════════════════════════════════════
// FILTER TABS
// ══════════════════════════════════════════════════════════════════════

document.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentFilter = tab.dataset.type;
        currentPage = 1;
        fetchHistory(1);
    });
});

// ══════════════════════════════════════════════════════════════════════
// LOAD MORE
// ══════════════════════════════════════════════════════════════════════

loadMoreBtn.addEventListener('click', () => {
    fetchHistory(currentPage + 1, true);
});

// ══════════════════════════════════════════════════════════════════════
// IMAGE MODAL
// ══════════════════════════════════════════════════════════════════════

function openModal(item) {
    const src = item.thumbnail
        ? `data:image/png;base64,${item.thumbnail}`
        : '';

    // Try to load full image from outputs
    if (item.image_filename) {
        modalImage.src = `${API_BASE}/api/outputs/${item.image_filename}`;
    } else {
        modalImage.src = src;
    }

    const meta = TYPE_META[item.action_type] || {};
    const date = new Date(item.created_at);
    modalInfo.innerHTML = `
        <strong>${meta.icon || ''} ${meta.label || item.action_type}</strong>
        <span style="color: var(--text-muted); margin-left: 1rem;">${date.toLocaleString('en-IN')}</span>
        <p style="margin-top: 0.5rem; color: var(--text-secondary); font-size: 0.85rem;">${item.prompt || ''}</p>
    `;

    imageModal.classList.add('active');
}

modalClose.addEventListener('click', () => {
    imageModal.classList.remove('active');
});

imageModal.addEventListener('click', (e) => {
    if (e.target === imageModal) {
        imageModal.classList.remove('active');
    }
});

// ══════════════════════════════════════════════════════════════════════
// DELETE
// ══════════════════════════════════════════════════════════════════════

async function deleteEntry(id, cardElement) {
    if (!confirm('Delete this entry?')) return;

    try {
        const res = await fetch(`${API_BASE}/api/history/${id}`, { method: 'DELETE' });
        const data = await res.json();

        if (!data.success) throw new Error(data.error);

        cardElement.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => {
            cardElement.remove();
            updateStats();
            // Check if grid is empty
            if (historyGrid.children.length === 0) {
                emptyState.style.display = 'flex';
                historyGrid.style.display = 'none';
            }
        }, 300);

        showToast('Entry deleted.', 'success');
    } catch (error) {
        showToast(`Delete failed: ${error.message}`, 'error');
    }
}

// ══════════════════════════════════════════════════════════════════════
// LOGOUT
// ══════════════════════════════════════════════════════════════════════

logoutBtn.addEventListener('click', async () => {
    try {
        await fetch(`${API_BASE}/api/auth/logout`, { method: 'POST' });
        showToast('Logged out successfully!', 'success');
        setTimeout(() => { window.location.href = '/login.html'; }, 500);
    } catch (e) {
        window.location.href = '/login.html';
    }
});

// ══════════════════════════════════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════════════════════════════════

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

// ── Initial load ─────────────────────────────────────────────────────
fetchHistory(1);
