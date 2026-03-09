// Auto Fill GPT - Popup Script
document.addEventListener('DOMContentLoaded', () => {

  // ─── Elements ─────────────────────────────────────────────
  const binInput = document.getElementById('binInput');
  const monthInput = document.getElementById('monthInput');
  const yearInput = document.getElementById('yearInput');
  const cvvInput = document.getElementById('cvvInput');
  const binTypeBadge = document.getElementById('binTypeBadge');
  const typeBtns = document.querySelectorAll('.type-btn');
  const fillBtn = document.getElementById('fillBtn');
  const clearLogBtn = document.getElementById('clearLogBtn');
  const logContainer = document.getElementById('logContainer');
  const pageStatus = document.getElementById('pageStatus');
  const pageUrl = document.getElementById('pageUrl');

  // Settings screen
  const settingsBtn = document.getElementById('settingsBtn');
  const backBtn = document.getElementById('backBtn');
  const mainScreen = document.getElementById('mainScreen');
  const settingsScreen = document.getElementById('settingsScreen');
  const defaultBin = document.getElementById('defaultBin');
  const defaultCardType = document.getElementById('defaultCardType');
  const fillDelay = document.getElementById('fillDelay');
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');

  // ─── State ────────────────────────────────────────────────
  let selectedType = '';
  let settings = { fillDelay: 100, defaultBin: '', defaultCardType: '' };

  // ─── Init ─────────────────────────────────────────────────
  loadSettings();
  detectCurrentTab();

  // ─── Navigation ───────────────────────────────────────────
  settingsBtn.addEventListener('click', () => {
    mainScreen.style.display = 'none';
    settingsScreen.style.display = 'flex';
  });

  backBtn.addEventListener('click', () => {
    settingsScreen.style.display = 'none';
    mainScreen.style.display = 'flex';
  });

  saveSettingsBtn.addEventListener('click', () => {
    settings.defaultBin = defaultBin.value.replace(/\D/g, '');
    settings.defaultCardType = defaultCardType.value;
    settings.fillDelay = parseInt(fillDelay.value) || 100;
    chrome.storage.local.set({ afSettings: settings }, () => {
      saveSettingsBtn.textContent = '✓ Saved!';
      setTimeout(() => saveSettingsBtn.textContent = 'Save Settings', 1500);
    });
  });

  // ─── Type Selector Buttons ────────────────────────────────
  typeBtns.forEach(btn => btn.addEventListener('click', () => {
    const t = btn.dataset.type;
    if (selectedType === t) {
      selectedType = '';
      typeBtns.forEach(b => b.classList.remove('active'));
      updateTypeBadge(CardGenerator.detectCardType(binInput.value)?.type || 'AUTO');
    } else {
      selectedType = t;
      typeBtns.forEach(b => b.classList.toggle('active', b.dataset.type === t));
      updateTypeBadge(t);
    }
  }));

  // ─── BIN Input ────────────────────────────────────────────
  binInput.addEventListener('input', () => {
    binInput.value = binInput.value.replace(/\D/g, '');
    const detected = CardGenerator.detectCardType(binInput.value);
    if (detected && !selectedType) {
      updateTypeBadge(detected.type);
      // Auto-highlight match
      typeBtns.forEach(b => b.classList.toggle('active', b.dataset.type === detected.type));
    } else {
      updateTypeBadge(selectedType || 'AUTO');
    }
  });

  // Only digits for month/year/cvv
  [monthInput, yearInput, cvvInput].forEach(el => {
    el.addEventListener('input', () => { el.value = el.value.replace(/\D/g, ''); });
  });

  // ─── Clear log ────────────────────────────────────────────
  clearLogBtn.addEventListener('click', () => {
    logContainer.innerHTML = '<div class="log-empty">Waiting for fill action...</div>';
  });

  // ─── FILL ─────────────────────────────────────────────────
  fillBtn.addEventListener('click', () => {
    const bin = binInput.value.trim();
    if (!bin) {
      addLog('error', '✗', 'BIN is required.');
      return;
    }

    // Build card
    let card;
    try {
      card = CardGenerator.generateFullCard(bin, {
        month: monthInput.value.trim() || null,
        year: yearInput.value.trim() || null,
        cvv: cvvInput.value.trim() || null,
        cardType: selectedType || undefined
      });
    } catch (e) {
      addLog('error', '✗', `Card error: ${e.message}`);
      return;
    }

    logContainer.innerHTML = '';
    addLog('info', 'ℹ', `Card type: ${card.type} | Luhn: ${card.isValid ? 'valid' : 'INVALID'}`);
    addLog('step', '→', `Number: ${card.numberFormatted}`);
    addLog('step', '→', `Expiry: ${card.expiry.formatted} | CVV: ${card.cvv}`);
    addLog('info', '⏳', 'Sending to page...');

    fillBtn.disabled = true;
    fillBtn.textContent = 'Filling...';

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]) {
        addLog('error', '✗', 'No active tab found.');
        resetFillBtn(); return;
      }

      chrome.tabs.sendMessage(tabs[0].id, {
        action: 'fillForm',
        cardData: card,
        fillDelay: settings.fillDelay
      }, (response) => {
        resetFillBtn();

        if (chrome.runtime.lastError) {
          addLog('error', '✗', `Tab error: ${chrome.runtime.lastError.message}`);
          return;
        }

        if (response && response.success) {
          addLog('success', '✓', 'Form filled successfully!');
          if (response.log && response.log.length) {
            response.log.forEach(entry => addLog(entry.type || 'step', entry.icon || '·', entry.msg));
          }
          chrome.storage.local.set({
            lastFilled: {
              number: card.number, type: card.type,
              expiry: card.expiry.formatted, cvv: card.cvv,
              at: new Date().toLocaleString()
            }
          });
        } else {
          addLog('error', '✗', response?.error || 'Fill failed. Is the page a checkout form?');
          if (response?.log) {
            response.log.forEach(entry => addLog(entry.type || 'warn', entry.icon || '·', entry.msg));
          }
        }
      });
    });
  });

  // ─── Helpers ──────────────────────────────────────────────
  function updateTypeBadge(type) {
    binTypeBadge.textContent = type;
    binTypeBadge.style.background = type === 'AUTO' ? '#30363d' : '#3b82f6';
  }

  function addLog(type, icon, msg) {
    // Remove "waiting" message if present
    const empty = logContainer.querySelector('.log-empty');
    if (empty) empty.remove();

    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `<span class="log-icon">${icon}</span><span class="log-text">${escapeHtml(msg)}</span>`;
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function resetFillBtn() {
    fillBtn.disabled = false;
    fillBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/></svg> Fill Checkout Form`;
  }

  function detectCurrentTab() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]) return;
      const url = tabs[0].url || '';
      pageUrl.textContent = new URL(url).hostname;

      const isCheckout = /pay|checkout|billing|payment|order|cart/i.test(url);
      if (isCheckout) {
        pageStatus.textContent = 'Checkout page detected';
        pageStatus.parentElement.style.color = 'var(--success)';
      } else {
        pageStatus.textContent = 'Navigate to a checkout page';
        pageStatus.parentElement.style.color = 'var(--warn)';
      }
    });
  }

  function loadSettings() {
    chrome.storage.local.get(['afSettings'], (res) => {
      if (res.afSettings) {
        settings = { ...settings, ...res.afSettings };
        fillDelay.value = settings.fillDelay;
        defaultCardType.value = settings.defaultCardType || '';
        if (settings.defaultBin) {
          binInput.value = settings.defaultBin;
          binInput.dispatchEvent(new Event('input'));
        }
      }
    });
  }
});
