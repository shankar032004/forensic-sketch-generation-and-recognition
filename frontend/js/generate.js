/**
 * Generate Page — Frontend logic for text-to-sketch generation.
 */

const API_BASE = '';

// ── DOM Elements ─────────────────────────────────────────────────────
const descriptionInput = document.getElementById('description-input');
const generateBtn = document.getElementById('generate-btn');
const resultContainer = document.getElementById('result-container');
const resultImage = document.getElementById('result-image');
const resultPlaceholder = document.getElementById('result-placeholder');
const loadingSpinner = document.getElementById('loading-spinner');
const promptInfo = document.getElementById('prompt-info');
const downloadBtn = document.getElementById('download-btn');
const editBtn = document.getElementById('edit-btn');
const languageSelect = document.getElementById('language-select');

// Attribute selects
const attrGender = document.getElementById('attr-gender');
const attrAge = document.getElementById('attr-age');
const attrHair = document.getElementById('attr-hair');
const attrEyes = document.getElementById('attr-eyes');
const attrNose = document.getElementById('attr-nose');
const attrLips = document.getElementById('attr-lips');
const attrJaw = document.getElementById('attr-jaw');
const attrBeard = document.getElementById('attr-beard');
const seedInput = document.getElementById('seed-input');
const stepsInput = document.getElementById('steps-input');

let currentImageBase64 = null;

// ── Generate ─────────────────────────────────────────────────────────
generateBtn.addEventListener('click', async () => {
    const description = descriptionInput.value.trim();
    const attributes = getAttributes();
    const hasAttributes = Object.values(attributes).some(v => v !== '' && v !== null);

    if (!description && !hasAttributes) {
        showToast('Please enter a description or select attributes.', 'error');
        return;
    }

    // Show loading
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Generating…';
    loadingSpinner.classList.add('active');
    resultPlaceholder.style.display = 'none';

    try {
        const body = {};
        if (description) body.description = description;
        if (hasAttributes) body.attributes = attributes;

        const seed = seedInput.value ? parseInt(seedInput.value) : null;
        const steps = stepsInput.value ? parseInt(stepsInput.value) : null;
        if (seed) body.seed = seed;
        if (steps) body.steps = steps;

        // Include language for translation
        const language = languageSelect ? languageSelect.value : 'en';
        if (language !== 'en') body.language = language;

        const response = await fetch(`${API_BASE}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Display result
        currentImageBase64 = data.image;
        resultImage.src = `data:image/png;base64,${data.image}`;
        resultImage.style.display = 'block';
        resultContainer.classList.add('has-image');

        // Show prompt info
        let infoText = `Prompt: ${data.prompt_used}`;
        if (data.translated_text) {
            infoText = `Translated: ${data.translated_text}\n${infoText}`;
        }
        promptInfo.textContent = infoText;
        promptInfo.classList.add('visible');

        // Show action buttons
        downloadBtn.style.display = 'inline-flex';
        editBtn.style.display = 'inline-flex';

        showToast('Sketch generated successfully!', 'success');

    } catch (error) {
        showToast(`Generation failed: ${error.message}`, 'error');
        resultPlaceholder.style.display = '';
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = '🎨 Generate Sketch';
        loadingSpinner.classList.remove('active');
    }
});

// ── Get attributes from dropdowns ────────────────────────────────────
function getAttributes() {
    return {
        gender: attrGender.value,
        age: attrAge.value,
        hair: attrHair.value,
        eyes: attrEyes.value,
        nose: attrNose.value,
        lips: attrLips.value,
        jaw: attrJaw.value,
        beard: attrBeard.value,
    };
}

// ── Download ─────────────────────────────────────────────────────────
downloadBtn.addEventListener('click', () => {
    if (!currentImageBase64) return;
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${currentImageBase64}`;
    link.download = `forensic_sketch_${Date.now()}.png`;
    link.click();
    showToast('Image downloaded!', 'success');
});

// ── Edit in Editor ───────────────────────────────────────────────────
editBtn.addEventListener('click', () => {
    if (!currentImageBase64) return;
    // Store in session storage for the editor page
    sessionStorage.setItem('sketch_image', currentImageBase64);
    window.location.href = '/editor.html';
});

// ── Toast Notification ───────────────────────────────────────────────
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
    const textarea = document.getElementById('description-input');

    let recognition = null;
    let isRecording = false;

    function startRecognition() {
        recognition = new SpeechRecognition();
        
        // Settings
        const langCode = languageSelect ? languageSelect.value : 'en';
        recognition.lang = LANG_CODES[langCode] || 'en-US';
        recognition.interimResults = true;
        recognition.continuous = false;

        console.log(`[Generate] Starting recognition in: ${recognition.lang}`);
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
                showToast(`Captured: "${finalTranscript}"`, 'success');
            }

            if (interimTranscript) {
                micStatus.textContent = `🎤 Hearing: ${interimTranscript}...`;
            }
        });

        recognition.addEventListener('error', (event) => {
            console.error('[Generate] Voice Error:', event.error);
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
            console.log('[Generate] Recognition ended.');
        });

        recognition.start();
    }

    function stopUI() {
        micBtn.classList.remove('recording');
        micStatus.classList.remove('visible');
        textarea.placeholder = "Example: Male, age 30, sharp jawline...";
    }

    micBtn.addEventListener('click', () => {
        if (isRecording && recognition) {
            recognition.stop();
        } else {
            startRecognition();
        }
    });
})();
