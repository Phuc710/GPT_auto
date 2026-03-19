// Popup script - Spotify Auto-Checkout Extension
'use strict';

document.addEventListener('DOMContentLoaded', () => {
    // ─── Elements ─────────────────────────────────────────
    const binInput = document.getElementById('binInput');
    const monthInput = document.getElementById('monthInput');
    const yearInput = document.getElementById('yearInput');
    const cvvInput = document.getElementById('cvvInput');
    const cardListInput = document.getElementById('cardListInput');
    const binTypeBadge = document.getElementById('binTypeBadge');
    const typeBtns = document.querySelectorAll('.type-btn');
    const runBtn = document.getElementById('runBtn');
    const stopBtn = document.getElementById('stopBtn');
    const clearLogBtn = document.getElementById('clearLogBtn');
    const exportLogBtn = document.getElementById('exportLogBtn');
    const logContainer = document.getElementById('logContainer');
    const pageStatus = document.getElementById('pageStatus');
    const statusDot = document.getElementById('statusDot');
    const statTried = document.getElementById('statTried');
    const statLive = document.getElementById('statLive');
    const statDead = document.getElementById('statDead');
    const progressWrap = document.getElementById('progressWrap');
    const progressBar = document.getElementById('progressBar');
    const progressLabel = document.getElementById('progressLabel');
    const reloadTabBtn = document.getElementById('reloadTabBtn');
    const autoScrollChk = document.getElementById('autoScrollChk');

    // Preview elements
    const cardPreview = document.getElementById('cardPreview');
    const previewTypeIcon = document.getElementById('previewTypeIcon');
    const previewTypeName = document.getElementById('previewTypeName');
    const previewCardNumber = document.getElementById('previewCardNumber');
    const previewExpiry = document.getElementById('previewExpiry');
    const previewCvv = document.getElementById('previewCvv');

    // Tab toggle
    const tabBin = document.getElementById('tabBin');
    const tabManual = document.getElementById('tabManual');
    const binPanel = document.getElementById('binPanel');
    const manualPanel = document.getElementById('manualPanel');

    // Settings
    const settingsBtn = document.getElementById('settingsBtn');
    const backBtn = document.getElementById('backBtn');
    const mainScreen = document.getElementById('mainScreen');
    const settingsScreen = document.getElementById('settingsScreen');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    const s_bin = document.getElementById('s_bin');
    const s_month = document.getElementById('s_month');
    const s_year = document.getElementById('s_year');
    const s_cvv = document.getElementById('s_cvv');
    const s_fillDelay = document.getElementById('s_fillDelay');
    const s_loopDelay = document.getElementById('s_loopDelay');

    // ─── State ────────────────────────────────────────────
    let selectedType = '';
    let currentMode = 'bin'; // 'bin' | 'manual'
    let logEntries = [];
    let settings = {};

    // ─── Init ─────────────────────────────────────────────
    loadSettings();
    loadLog();
    listenForMessages();
    loadState();

    // ─── Tab Toggle ───────────────────────────────────────
    tabBin.addEventListener('click', () => {
        currentMode = 'bin';
        tabBin.classList.add('active'); tabManual.classList.remove('active');
        binPanel.style.display = ''; manualPanel.style.display = 'none';
    });
    tabManual.addEventListener('click', () => {
        currentMode = 'manual';
        tabManual.classList.add('active'); tabBin.classList.remove('active');
        manualPanel.style.display = ''; binPanel.style.display = 'none';
    });

    // ─── Network Type Buttons ─────────────────────────────
    typeBtns.forEach(btn => btn.addEventListener('click', () => {
        const t = btn.dataset.type;
        if (selectedType === t) {
            selectedType = '';
            typeBtns.forEach(b => b.classList.remove('active'));
            const det = CardGenerator.detectCardType(binInput.value);
            applyNetworkUI(det ? det.type : null);
        } else {
            selectedType = t;
            typeBtns.forEach(b => b.classList.toggle('active', b.dataset.type === t));
            applyNetworkUI(t);
            if (!binInput.value) {
                binInput.value = CardGenerator.generateRandomBIN(t);
                binInput.dispatchEvent(new Event('change', { bubbles: true }));
                binInput.blur();
            }
        }
        updateCardPreview();
    }));

    binInput.addEventListener('input', () => {
        binInput.value = binInput.value.replace(/\D/g, '');
        if (!selectedType) {
            const det = CardGenerator.detectCardType(binInput.value);
            typeBtns.forEach(b => b.classList.toggle('active', !!det && b.dataset.type === det.type));
            applyNetworkUI(det ? det.type : null);
        }
    });

    [monthInput, yearInput, cvvInput].forEach(el => {
        el.addEventListener('input', () => {
            el.value = el.value.replace(/\D/g, '');
            updateCardPreview();
        });
    });

    binInput.addEventListener('input', () => {
        binInput.value = binInput.value.replace(/[^\dxX]/g, '');
        updateCardPreview();
    });

    function updateCardPreview() {
        if (currentMode !== 'bin') return;
        const bin = binInput.value.trim();
        if (!bin) {
            previewCardNumber.textContent = '•••• •••• •••• ••••';
            previewTypeName.textContent = 'Unknown';
            previewTypeIcon.textContent = '💳';
            cardPreview.querySelector('.card-preview-inner').style.background = 'linear-gradient(135deg, #1a1f71, #0057b8)';
            return;
        }

        try {
            const sample = CardGenerator.generateFullCard(bin, {
                month: monthInput.value.trim(),
                year: yearInput.value.trim(),
                cvv: cvvInput.value.trim(),
                cardType: selectedType
            });

            previewCardNumber.textContent = sample.numberFormatted;
            previewTypeName.textContent = sample.type;
            previewTypeIcon.textContent = sample.emoji;
            previewExpiry.textContent = sample.expiry.formatted;
            previewCvv.textContent = '•'.repeat(sample.cvv.length);

            // Set dynamic background
            const inner = cardPreview.querySelector('.card-preview-inner');
            inner.style.background = sample.gradient;
        } catch (e) {
            // Partial BIN or invalid
            const type = CardGenerator.detectCardType((bin || '00').replace(/x/gi, '0'));
            previewTypeName.textContent = type ? type.name : 'Detecting...';
            previewTypeIcon.textContent = type ? type.emoji : '💳';
            if (type) cardPreview.querySelector('.card-preview-inner').style.background = type.gradient;
        }
    }

    // ─── Navigation ───────────────────────────────────────
    settingsBtn.addEventListener('click', () => {
        populateSettingsUI();
        mainScreen.style.display = 'none';
        settingsScreen.style.display = 'flex';
    });
    backBtn.addEventListener('click', () => {
        applySettingsToForm();
        settingsScreen.style.display = 'none';
        mainScreen.style.display = 'flex';
    });

    saveSettingsBtn.addEventListener('click', () => {
        settings = {
            bin: (s_bin.value || '').replace(/\D/g, ''),
            expiryMonth: (s_month.value || '').replace(/\D/g, ''),
            expiryYear: (s_year.value || '').replace(/\D/g, ''),
            cvv: (s_cvv.value || '').replace(/\D/g, ''),
            fillDelay: parseInt(s_fillDelay.value) || 300,
            loopDelay: parseInt(s_loopDelay.value) || 2000
        };
        chrome.storage.local.set({ spSettings: settings }, () => {
            applySettingsToForm(); // Sync to main form
            saveSettingsBtn.textContent = '✓ Saved!';
            setTimeout(() => { saveSettingsBtn.textContent = '💾 Save'; }, 1400);
        });
    });

    // ─── Reload ───────────────────────────────────────────
    reloadTabBtn.addEventListener('click', () => {
        chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
            if (tabs[0]) chrome.tabs.reload(tabs[0].id);
        });
    });

    // ─── RUN ──────────────────────────────────────────────
    runBtn.addEventListener('click', async () => {
        const tabs = await getActiveTab();
        if (!tabs) { addLog('error', '✗', 'No active tab found.'); return; }

        const tabUrl = tabs.url || '';
        if (!tabUrl.includes('spotify.com')) {
            addLog('warn', '⚠', 'Tab does not look like a Spotify checkout page!');
        }

        // Inject scripts robustly first
        await injectScripts(tabs.id);

        const payload = { action: 'startRunner', tabId: tabs.id };

        if (currentMode === 'manual') {
            const lines = (cardListInput.value || '').split('\n').map(l => l.trim()).filter(Boolean);
            if (!lines.length) { addLog('error', '✗', 'Card list is empty.'); return; }
            payload.cardList = lines;
        } else {
            const bin = binInput.value.trim();
            if (!bin) { addLog('error', '✗', 'BIN is required.'); return; }
            payload.bin = bin;
            payload.month = monthInput.value.trim() || null;
            payload.year = yearInput.value.trim() || null;
            payload.cvv = cvvInput.value.trim() || null;
            payload.cardType = selectedType || null;
        }

        payload.fillDelay = settings.fillDelay || 300;
        payload.loopDelay = settings.loopDelay || 2000;

        logEntries = [];
        renderLog();
        chrome.storage.local.remove('spLog');

        chrome.runtime.sendMessage(payload, res => {
            if (res && res.success) {
                addLog('info', '▶', `Runner started — ${res.total} cards queued`);
                setRunningUI(true);
            } else {
                addLog('error', '✗', res?.error || 'Failed to start runner');
            }
        });
    });

    // ─── STOP ─────────────────────────────────────────────
    stopBtn.addEventListener('click', () => {
        chrome.runtime.sendMessage({ action: 'stopRunner' }, () => {
            addLog('warn', '⏹', 'Runner stopped by user');
            setRunningUI(false);
        });
    });

    // ─── LOG controls ─────────────────────────────────────
    clearLogBtn.addEventListener('click', () => {
        logEntries = [];
        chrome.storage.local.remove('spLog');
        renderLog();
    });

    exportLogBtn.addEventListener('click', () => {
        const text = logEntries.map(e => `[${fmtTs(e.ts)}] ${e.icon} ${e.msg}`).join('\n');
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `spotify_checker_${Date.now()}.txt`;
        a.click(); URL.revokeObjectURL(url);
    });

    // ─── Listen for real-time messages ────────────────────
    function listenForMessages() {
        chrome.runtime.onMessage.addListener(msg => {
            if (msg.action === 'logUpdate') {
                addLog(msg.entry.type, msg.entry.icon, msg.entry.msg, msg.entry.ts);
            }
            if (msg.action === 'stateUpdate') {
                applyState(msg);
            }
        });
    }

    function applyState(state) {
        if (!state) return;
        setRunningUI(state.running);

        const stats = state.stats || {};
        statTried.textContent = `Tried: ${stats.tried || 0}`;
        statLive.textContent = `Live: ${stats.live || 0}`;
        statDead.textContent = `Dead: ${stats.died || 0}`;

        progressWrap.style.display = 'block';
        if (state.isManual) {
            const total = state.cards ? state.cards.length : (state.total || 1);
            const pct = Math.round(((state.index) / total) * 100);
            progressBar.style.width = `${pct}%`;
            progressLabel.textContent = `${state.index} / ${total}`;

            if (state.running) {
                pageStatus.textContent = `Checking ${state.index + 1}/${total}...`;
            } else if (state.index >= total) {
                pageStatus.textContent = 'All cards checked';
            } else {
                pageStatus.textContent = 'Idle';
            }
        } else {
            // Infinite BIN Mode
            progressBar.style.width = '100%'; // Full width or solid pulsing bar
            progressLabel.textContent = `∞`;

            if (state.running) {
                pageStatus.textContent = `Checking ${state.index + 1}...`;
            } else {
                pageStatus.textContent = 'Idle';
            }
        }
    }

    function loadState() {
        chrome.storage.local.get(['spState', 'spSettings'], res => {
            if (res.spSettings) {
                settings = res.spSettings;
                applySettingsToForm();
            }
            if (res.spState) applyState(res.spState);
        });
    }

    // ─── Log helpers ──────────────────────────────────────
    function addLog(type, icon, msg, ts) {
        const entry = { type, icon, msg, ts: ts || Date.now() };
        logEntries.push(entry);
        if (logEntries.length > 300) logEntries = logEntries.slice(-300);
        appendLogEntry(entry);
    }

    function appendLogEntry(e) {
        const empty = logContainer.querySelector('.log-empty');
        if (empty) empty.remove();
        const el = document.createElement('div');
        el.className = `log-entry ${e.type || 'info'}`;
        el.innerHTML =
            `<span class="log-ts">${fmtTs(e.ts)}</span>` +
            `<span class="log-icon">${e.icon || '·'}</span>` +
            `<span class="log-text">${escHtml(e.msg)}</span>`;
        logContainer.appendChild(el);
        if (autoScrollChk?.checked) logContainer.scrollTop = logContainer.scrollHeight;
        chrome.storage.local.set({ spLog: logEntries });
    }

    function renderLog() {
        logContainer.innerHTML = '';
        if (!logEntries.length) {
            logContainer.innerHTML = '<div class="log-empty">Waiting to start...</div>';
            return;
        }
        logEntries.forEach(e => appendLogEntry(e));
    }

    function loadLog() {
        chrome.storage.local.get(['spLog'], res => {
            if (res.spLog && res.spLog.length) {
                logEntries = res.spLog;
                renderLog();
            }
        });
    }

    function fmtTs(ts) {
        if (!ts) return '';
        const d = new Date(ts);
        return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    }
    function pad(n) { return String(n).padStart(2, '0'); }
    function escHtml(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

    // ─── Running UI ───────────────────────────────────────
    function setRunningUI(running) {
        runBtn.disabled = running;
        stopBtn.disabled = !running;
        statusDot.className = 'dot' + (running ? ' running' : '');
        if (!running) pageStatus.textContent = 'Stopped';
    }

    // ─── Network UI ───────────────────────────────────────
    function applyNetworkUI(typeKey) {
        if (!typeKey) { updateBadge('AUTO', '#1db954'); return; }
        const info = CardGenerator.CARD_TYPES[typeKey];
        if (!info) return;
        updateBadge(info.shortName, info.color);
    }
    function updateBadge(text, color) {
        binTypeBadge.textContent = text;
        binTypeBadge.style.background = color;
        binTypeBadge.style.color = '#fff';
    }

    // ─── Settings helpers ─────────────────────────────────
    function populateSettingsUI() {
        s_bin.value = settings.bin || '';
        s_month.value = settings.expiryMonth || '';
        s_year.value = settings.expiryYear || '';
        s_cvv.value = settings.cvv || '';
        s_fillDelay.value = settings.fillDelay || 300;
        s_loopDelay.value = settings.loopDelay || 2000;
    }

    function applySettingsToForm() {
        if (settings.bin) { binInput.value = settings.bin; binInput.dispatchEvent(new Event('input')); }
        if (settings.expiryMonth) monthInput.value = settings.expiryMonth;
        if (settings.expiryYear) yearInput.value = settings.expiryYear;
        if (settings.cvv) cvvInput.value = settings.cvv;
    }

    function loadSettings() {
        chrome.storage.local.get(['spSettings'], res => {
            if (res.spSettings) {
                settings = res.spSettings;
                applySettingsToForm();
            }
        });
    }

    // ─── Tab helpers ──────────────────────────────────────
    function getActiveTab() {
        return new Promise(resolve => {
            chrome.tabs.query({ active: true, currentWindow: true }, tabs => resolve(tabs[0] || null));
        });
    }

    async function injectScripts(tabId) {
        try {
            await chrome.scripting.executeScript({
                target: { tabId, allFrames: true },
                files: ['cardGenerator.js', 'content.js']
            });
        } catch (e) {
            // Already injected — ignore
        }
    }
});
