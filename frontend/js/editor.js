/**
 * Editor Page — Frontend logic for face region editing via inpainting.
 */

const API_BASE = '';

// ── DOM Elements ─────────────────────────────────────────────────────
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const uploadLabel = document.getElementById('upload-label');
const inputPreview = document.getElementById('input-preview');
const regionSelect = document.getElementById('region-select');
const modificationInput = document.getElementById('modification-input');
const languageSelect = document.getElementById('language-select');
const editBtn = document.getElementById('edit-btn');
const resultContainer = document.getElementById('result-container');
const resultImage = document.getElementById('result-image');
const resultPlaceholder = document.getElementById('result-placeholder');
const maskImage = document.getElementById('mask-image');
const maskPlaceholder = document.getElementById('mask-placeholder');
const loadingSpinner = document.getElementById('loading-spinner');
const promptInfo = document.getElementById('prompt-info');
const downloadBtn = document.getElementById('download-btn');
const useAsInputBtn = document.getElementById('use-as-input-btn');

let currentInputBase64 = null;
let currentResultBase64 = null;

// ── Check for image from generate page ───────────────────────────────
(function loadFromSession() {
    const stored = sessionStorage.getItem('sketch_image');
    if (stored) {
        currentInputBase64 = stored;
        inputPreview.src = `data:image/png;base64,${stored}`;
        inputPreview.style.display = 'block';
        uploadLabel.style.display = 'none';
        uploadZone.classList.add('has-image');
        sessionStorage.removeItem('sketch_image');
    }
})();

// ── File Upload ──────────────────────────────────────────────────────
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    handleFile(file);
});

// Drag & drop
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        handleFile(file);
    }
});

function handleFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const dataUrl = e.target.result;
        currentInputBase64 = dataUrl.split(',')[1];
        inputPreview.src = dataUrl;
        inputPreview.style.display = 'block';
        uploadLabel.style.display = 'none';
        uploadZone.classList.add('has-image');
    };
    reader.readAsDataURL(file);
}

// ── Auto-detect region from modification text ───────────────────────
const REGION_KEYWORDS = {
    hair: ['hair', 'hairs', 'hairstyle', 'bald', 'curly hair', 'straight hair',
        'long hair', 'short hair', 'afro', 'ponytail', 'bangs',
        'curly', 'wavy', 'frizzy', 'braided', 'spiky', 'messy',
        'slicked', 'mohawk', 'bob cut', 'buzz cut', 'dreadlocks',
        'receding', 'thinning', 'thick hair', 'parted'],
    eyes: ['eyes', 'eyelash', 'eyelid', 'pupils'],
    left_eye: ['left eye'],
    right_eye: ['right eye'],
    nose: ['nose', 'nostril', 'nostrils'],
    mouth: ['mouth', 'lips', 'lip', 'teeth', 'smile'],
    jaw: ['jaw', 'jawline', 'chin'],
    forehead: ['forehead', 'wrinkles on forehead'],
};

modificationInput.addEventListener('input', () => {
    const text = modificationInput.value.toLowerCase().trim();
    if (!text) return;

    let matches = new Set();

    for (const [region, keywords] of Object.entries(REGION_KEYWORDS)) {
        for (const kw of keywords) {
            if (text.includes(kw)) {
                matches.add(region);
            }
        }
    }

    if (matches.size > 0) {
        // Sort matches for consistency
        const regions = Array.from(matches).sort();
        
        // Update the select value if it's a single match, 
        // otherwise we will handle combined regions during submission
        if (regions.length === 1) {
            regionSelect.value = regions[0];
        } else {
            // If multiple, use the first as primary in dropdown but keep track
            regionSelect.value = regions[0];
            console.log(`[Editor] Multiple regions detected: ${regions.join(', ')}`);
        }
        
        // Store current detected regions on the element for retrieval during submit
        modificationInput.dataset.detectedRegions = regions.join(',');
    } else {
        modificationInput.dataset.detectedRegions = '';
    }
});

// ── Apply Edit ───────────────────────────────────────────────────────
editBtn.addEventListener('click', async () => {
    if (!currentInputBase64) {
        showToast('Please upload an image first.', 'error');
        return;
    }

    const modification = modificationInput.value.trim();
    if (!modification) {
        showToast('Please describe the modification.', 'error');
        return;
    }

    const region = regionSelect.value;

    // Show loading
    editBtn.disabled = true;
    editBtn.textContent = '⏳ Applying…';
    loadingSpinner.classList.add('active');
    resultPlaceholder.style.display = 'none';

    try {
        const language = languageSelect ? languageSelect.value : 'en';
        
        // Use detected multiple regions if available, else use dropdown
        const regionToSend = modificationInput.dataset.detectedRegions || region;

        const response = await fetch(`${API_BASE}/api/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: currentInputBase64,
                region: regionToSend,
                modification: modification,
                language: language,
            }),
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Display result
        currentResultBase64 = data.image;
        resultImage.src = `data:image/png;base64,${data.image}`;
        resultImage.style.display = 'block';
        resultContainer.classList.add('has-image');

        // Display mask
        if (data.mask) {
            maskImage.src = `data:image/png;base64,${data.mask}`;
            maskImage.style.display = 'block';
            maskPlaceholder.style.display = 'none';
        }

        // Show prompt info with region used
        const regionUsed = data.region_used || region;
        let infoText = `Region: ${regionUsed} | Prompt: ${data.prompt_used}`;
        if (data.translated_text) {
            infoText = `Translated: ${data.translated_text}\n${infoText}`;
        }
        promptInfo.textContent = infoText;
        promptInfo.classList.add('visible');

        // Update the dropdown to show the region that was actually used
        if (data.region_used && data.region_used !== region) {
            regionSelect.value = data.region_used;
        }

        // Show action buttons
        downloadBtn.style.display = 'inline-flex';
        useAsInputBtn.style.display = 'inline-flex';

        showToast('Edit applied successfully!', 'success');

    } catch (error) {
        showToast(`Edit failed: ${error.message}`, 'error');
        resultPlaceholder.style.display = '';
    } finally {
        editBtn.disabled = false;
        editBtn.textContent = '✏️ Apply Edit';
        loadingSpinner.classList.remove('active');
    }
});

// ── Download ─────────────────────────────────────────────────────────
downloadBtn.addEventListener('click', () => {
    if (!currentResultBase64) return;
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${currentResultBase64}`;
    link.download = `forensic_edit_${Date.now()}.png`;
    link.click();
    showToast('Image downloaded!', 'success');
});

// ── Use result as new input ──────────────────────────────────────────
useAsInputBtn.addEventListener('click', () => {
    if (!currentResultBase64) return;
    currentInputBase64 = currentResultBase64;
    inputPreview.src = `data:image/png;base64,${currentResultBase64}`;
    inputPreview.style.display = 'block';
    uploadLabel.style.display = 'none';
    uploadZone.classList.add('has-image');
    showToast('Result loaded as new input — apply another edit!', 'info');
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

// ── Voice-to-Text (Speech Recognition) ──────────────────────────────
const LANG_CODES = { en: 'en-US', hi: 'hi-IN', mr: 'mr-IN' };

(function initVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        const micBtn = document.getElementById('mic-btn');
        if (micBtn) micBtn.style.display = 'none';
        return;
    }

    const micBtn = document.getElementById('mic-btn');
    const micStatus = document.getElementById('mic-status');
    const textarea = document.getElementById('modification-input');

    let recognition = null;
    let isRecording = false;

    function startRecognition() {
        recognition = new SpeechRecognition();
        
        // Settings
        const langCode = languageSelect ? languageSelect.value : 'en';
        recognition.lang = LANG_CODES[langCode] || 'en-US';
        recognition.interimResults = true;
        recognition.continuous = false;

        console.log(`[Editor] Starting recognition in: ${recognition.lang}`);
        textarea.placeholder = "Listening... Speak now!";

        recognition.addEventListener('start', () => {
            isRecording = true;
            micBtn.classList.add('recording');
            micStatus.classList.add('visible');
            micStatus.textContent = `🔴 Listening (${langCode})...`;
        });

        recognition.addEventListener('result', (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            if (finalTranscript) {
                const current = textarea.value.trim();
                textarea.value = current ? `${current} ${finalTranscript}` : finalTranscript;
                
                // Trigger the auto-detect region logic
                textarea.dispatchEvent(new Event('input'));
                
                showToast(`Captured: "${finalTranscript}"`, 'success');
            }

            if (interimTranscript) {
                micStatus.textContent = `🎤 Hearing: ${interimTranscript}...`;
            }
        });

        recognition.addEventListener('error', (event) => {
            console.error('[Editor] Voice Error:', event.error);
            isRecording = false;
            stopUI();
            
            if (event.error === 'no-speech') {
                showToast('No speech detected. Please try again.', 'info');
            } else if (event.error === 'not-allowed') {
                showToast('Microphone access denied.', 'error');
            } else if (event.error === 'language-not-supported') {
                showToast(`Language ${recognition.lang} not supported by this browser.`, 'error');
            } else {
                showToast(`Voice error: ${event.error}`, 'error');
            }
        });

        recognition.addEventListener('end', () => {
            isRecording = false;
            stopUI();
            console.log('[Editor] Recognition ended.');
        });

        recognition.start();
    }

    function stopUI() {
        micBtn.classList.remove('recording');
        micStatus.classList.remove('visible');
        textarea.placeholder = "Describe what to change (e.g. 'make the nose sharper')";
    }

    micBtn.addEventListener('click', () => {
        if (isRecording && recognition) {
            recognition.stop();
        } else {
            startRecognition();
        }
    });
})();

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
