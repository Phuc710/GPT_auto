// Auto Fill GPT - Popup Script (v4 — dual button)
document.addEventListener('DOMContentLoaded', () => {

  // ─── Elements ─────────────────────────────────────────────
  const binInput = document.getElementById('binInput');
  const monthInput = document.getElementById('monthInput');
  const yearInput = document.getElementById('yearInput');
  const cvvInput = document.getElementById('cvvInput');

  const binTypeBadge = document.getElementById('binTypeBadge');
  const typeBtns = document.querySelectorAll('.type-btn');
  const fillFullBtn = document.getElementById('fillFullBtn');
  const fillCardBtn = document.getElementById('fillCardBtn');
  const clearLogBtn = document.getElementById('clearLogBtn');
  const logContainer = document.getElementById('logContainer');
  const pageStatus = document.getElementById('pageStatus');
  const pageUrl = document.getElementById('pageUrl');
  const reloadTabBtn = document.getElementById('reloadTabBtn');
  const countryBtns = document.querySelectorAll('.country-btn');
  const autoCaptchaToggle = document.getElementById('autoCaptchaToggle');

  // Settings screen
  const settingsBtn = document.getElementById('settingsBtn');
  const backBtn = document.getElementById('backBtn');
  const mainScreen = document.getElementById('mainScreen');
  const settingsScreen = document.getElementById('settingsScreen');
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');

  // Settings fields — card
  const s_bin = document.getElementById('defaultBin');
  const s_cardType = document.getElementById('defaultCardType');
  const s_month = document.getElementById('defaultMonth');
  const s_year = document.getElementById('defaultYear');
  const s_cvv = document.getElementById('defaultCvv');
  // Settings fields — billing address
  const s_country = document.getElementById('defaultCountry');
  const s_name = document.getElementById('defaultName');
  const s_state = document.getElementById('defaultState');
  const s_addr1 = document.getElementById('defaultAddress1');
  const s_addr2 = document.getElementById('defaultAddress2');
  const s_city = document.getElementById('defaultCity');
  const s_postal = document.getElementById('defaultPostal');
  // Settings fields — behavior
  const s_delay = document.getElementById('fillDelay');

  // ─── State ────────────────────────────────────────────────
  let selectedType = '';
  let settings = {
    fillDelay: 100,
    defaultBin: '', defaultCardType: '',
    defaultMonth: '', defaultYear: '', defaultCvv: '',
    defaultCountry: 'KR',
    defaultName: '', defaultState: '',
    defaultAddress1: '', defaultAddress2: '',
    defaultCity: '', defaultPostal: ''
  };

  // Dedicated config for the global scripts
  let globalSettings = {
    standaloneCaptcha: false
  };

  // ─── Init ─────────────────────────────────────────────────
  loadSettings();
  detectCurrentTab();

  // ─── Navigation ───────────────────────────────────────────
  settingsBtn.addEventListener('click', () => {
    populateSettingsUI();
    mainScreen.style.display = 'none';
    settingsScreen.style.display = 'flex';
  });
  backBtn.addEventListener('click', () => {
    settingsScreen.style.display = 'none';
    mainScreen.style.display = 'flex';
  });

  saveSettingsBtn.addEventListener('click', () => {
    settings.defaultBin = (s_bin.value || '').replace(/\D/g, '');
    settings.defaultCardType = s_cardType.value;
    settings.defaultMonth = (s_month.value || '').replace(/\D/g, '');
    settings.defaultYear = (s_year.value || '').replace(/\D/g, '');
    settings.defaultCvv = (s_cvv.value || '').replace(/\D/g, '');
    settings.defaultCountry = s_country.value;
    settings.defaultName = s_name.value.trim();
    settings.defaultState = s_state.value.trim();
    settings.defaultAddress1 = s_addr1.value.trim();
    settings.defaultAddress2 = s_addr2.value.trim();
    settings.defaultCity = s_city.value.trim();
    settings.defaultPostal = s_postal.value.trim();
    settings.fillDelay = parseInt(s_delay.value) || 100;

    chrome.storage.local.set({ afSettings: settings }, () => {
      applySettingsToMainForm();
      saveSettingsBtn.textContent = '✓ Saved!';
      setTimeout(() => { saveSettingsBtn.textContent = '💾 Save Settings'; }, 1500);
    });
  });

  // ─── Network Type Buttons ─────────────────────────────────
  typeBtns.forEach(btn => btn.addEventListener('click', () => {
    const t = btn.dataset.type;
    if (selectedType === t) {
      selectedType = '';
      typeBtns.forEach(b => b.classList.remove('active'));
      const detected = CardGenerator.detectCardType(binInput.value);
      applyNetworkUI(detected ? detected.type : null);
    } else {
      selectedType = t;
      typeBtns.forEach(b => b.classList.toggle('active', b.dataset.type === t));
      applyNetworkUI(t);
      if (!binInput.value) {
        binInput.value = CardGenerator.generateRandomBIN(t);
        binInput.dispatchEvent(new Event('input'));
        return;
      }
    }
  }));

  // ─── Country Quick Select ────────────────────────────────
  countryBtns.forEach(btn => btn.addEventListener('click', () => {
    const c = btn.dataset.country;
    settings.defaultCountry = c;
    updateCountryUI(c);
    // Update settings in storage too
    chrome.storage.local.set({ afSettings: settings });
    addLog('info', '🌍', `Country switched to: ${btn.title}`);
  }));

  function updateCountryUI(countryCode) {
    countryBtns.forEach(b => b.classList.toggle('active', b.dataset.country === countryCode));
    if (s_country) s_country.value = countryCode;
  }

  // ─── BIN Input → live auto-detect & smart parse ───────────
  binInput.addEventListener('input', () => {
    let val = binInput.value.trim();
    
    // Smart Parse: If user pastes "number|mm|yy|cvv"
    if (val.includes('|')) {
      const parts = val.split('|').map(p => p.trim());
      if (parts.length >= 3) {
        const cardNumber = parts[0].replace(/\D/g, '');
        const month = parts[1].replace(/\D/g, '');
        const year = parts[2].replace(/\D/g, '');
        const cvv = parts[3] ? parts[3].replace(/\D/g, '') : '';
        
        binInput.value = cardNumber;
        if (month) monthInput.value = month;
        if (year) yearInput.value = year;
        if (cvv) cvvInput.value = cvv;
        
        addLog('success', '🧬', `Smart parsed card: ${cardNumber.slice(0,6)}...|${month}|${year}`);
        // Re-process simple case
        val = cardNumber;
      }
    }

    binInput.value = binInput.value.replace(/\D/g, '');
    const detected = CardGenerator.detectCardType(binInput.value);
    if (detected && !selectedType) {
      typeBtns.forEach(b => b.classList.toggle('active', b.dataset.type === detected.type));
      applyNetworkUI(detected.type);
    } else if (!selectedType) {
      typeBtns.forEach(b => b.classList.remove('active'));
      applyNetworkUI(null);
    }
  });

  // ─── Other inputs ─────────────────────────────────────────
  [monthInput, yearInput, cvvInput].forEach(el => {
    el.addEventListener('input', () => { el.value = el.value.replace(/\D/g, ''); });
  });

  // ─── Clear log ────────────────────────────────────────────
  clearLogBtn.addEventListener('click', () => {
    logEntries = [];
    chrome.storage.local.remove('afLog');
    logContainer.innerHTML = '<div class="log-empty">Waiting for fill action...</div>';
  });

  reloadTabBtn.addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.reload(tabs[0].id);
        addLog('info', '↻', 'Reloading page...');
      }
    });
  });

  // ─── Automation Toggles ───────────────────────────────────

  if (autoCaptchaToggle) {
    autoCaptchaToggle.addEventListener('change', (e) => {
      globalSettings.standaloneCaptcha = e.target.checked;
      chrome.storage.local.set({ standaloneCaptcha: e.target.checked });
      const status = e.target.checked ? 'enabled' : 'disabled';
      addLog('info', '🤖', `Auto Captcha ${status}`);
    });
  }

  // ─── FILL FULL (Card + Address) ───────────────────────────
  fillFullBtn.addEventListener('click', () => {
    const card = buildCard();
    if (!card) return;

    // Reset coordinator
    chrome.runtime.sendMessage({ action: 'fill_status', status: 'reset' });

    // Smart address: use settings if all key fields filled, else random Korean
    const addr = buildAddress(true);

    logEntries = [];
    logContainer.innerHTML = '';
    if (addr._isRandom) {
      addLog('info', '🎲', `Random address (${addr.country}): ${addr.name} — ${addr.line1}, ${addr.city}`);
    }

    setButtonsDisabled(true);
    triggerFill(card, addr);
  });

  // ─── FILL CARD ONLY (no address) ──────────────────────────
  fillCardBtn.addEventListener('click', () => {
    const card = buildCard();
    if (!card) return;

    // Reset coordinator
    chrome.runtime.sendMessage({ action: 'fill_status', status: 'reset' });

    logEntries = [];
    logContainer.innerHTML = '';

    setButtonsDisabled(true);
    triggerFill(card, {}); // empty address = card only
  });

  // ─── Core helpers ─────────────────────────────────────────

  /** Build card from inputs, returns null on error */
  function buildCard() {
    const bin = binInput.value.trim();
    if (!bin) { addLog('error', '✗', 'BIN is required.'); return null; }
    try {
      return CardGenerator.generateFullCard(bin, {
        month: monthInput.value.trim() || null,
        year: yearInput.value.trim() || null,
        cvv: cvvInput.value.trim() || null,
        cardType: selectedType || undefined
      });
    } catch (e) {
      addLog('error', '✗', `Card error: ${e.message}`);
      return null;
    }
  }

  /**
   * Build address payload.
   * If settings has all key fields → use settings.
   * Otherwise → pick random Korean address from DataGenerator.
   */
  function buildAddress(includeAddress) {
    if (!includeAddress) return {};

    const hasSettings =
      settings.defaultName &&
      settings.defaultState &&
      settings.defaultCity &&
      settings.defaultAddress1 &&
      settings.defaultPostal;

    if (hasSettings) {
      return {
        name: settings.defaultName,
        state: settings.defaultState,
        city: settings.defaultCity,
        line1: settings.defaultAddress1,
        line2: settings.defaultAddress2 || '',
        postal: settings.defaultPostal,
        _isRandom: false
      };
    }

    // Fall back to random address based on selected country
    const rand = window.DataGenerator.getRandomAddress(settings.defaultCountry || 'KR');
    return { ...rand, _isRandom: true };
  }

  function triggerFill(card, address) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]) {
        addLog('error', '✗', 'No active tab found.');
        setButtonsDisabled(false);
        return;
      }

      const payload = {
        action: 'fillForm',
        cardData: card,
        address: address,
        fillDelay: settings.fillDelay
      };

      sendFillMessage(tabs[0].id, payload, (response, errorMessage) => {
        setButtonsDisabled(false);

        if (errorMessage) {
          addLog('error', '✗', `Tab error: ${errorMessage}`);
          return;
        }

        if (response && response.success) {
          // Note: Detailed logs and final success string are now broadcasted live 
          // from the content script to maintain perfect sequence.
          chrome.storage.local.set({
            lastFilled: {
              number: card.number, type: card.type,
              expiry: card.expiry.formatted, cvv: card.cvv,
              at: new Date().toLocaleString()
            }
          });
        } else {
          addLog('error', '✗', response?.error || 'Fill failed. Is this a checkout page?');
        }
      });
    });
  }

  function setButtonsDisabled(disabled) {
    fillFullBtn.disabled = disabled;
    fillCardBtn.disabled = disabled;
    if (disabled) {
      fillFullBtn.textContent = 'Filling...';
      fillCardBtn.textContent = 'Filling...';
    } else {
      fillFullBtn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/><path d="M7 15h2M12 15h5" stroke-linecap="round"/></svg> Fill Full`;
      fillCardBtn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/></svg> Fill Card`;
    }
  }

  // ─── Network UI ───────────────────────────────────────────
  function applyNetworkUI(typeKey) {
    if (!typeKey) { updateBadge('AUTO', '#30363d'); return; }
    const info = CardGenerator.CARD_TYPES[typeKey];
    if (!info) return;
    updateBadge(info.shortName, info.color);
  }

  function updateBadge(text, color) {
    binTypeBadge.textContent = text;
    binTypeBadge.style.background = color;
  }

  // ─── Settings Helpers ─────────────────────────────────────

  function populateSettingsUI() {
    s_bin.value = settings.defaultBin || '';
    s_cardType.value = settings.defaultCardType || '';
    s_month.value = settings.defaultMonth || '';
    s_year.value = settings.defaultYear || '';
    s_cvv.value = settings.defaultCvv || '';
    s_country.value = settings.defaultCountry || 'KR';
    s_name.value = settings.defaultName || '';
    s_state.value = settings.defaultState || '';
    s_addr1.value = settings.defaultAddress1 || '';
    s_addr2.value = settings.defaultAddress2 || '';
    s_city.value = settings.defaultCity || '';
    s_postal.value = settings.defaultPostal || '';
    s_delay.value = settings.fillDelay || 100;
  }

  function applySettingsToMainForm() {
    if (settings.defaultBin) {
      binInput.value = settings.defaultBin;
      binInput.dispatchEvent(new Event('input'));
    }
    if (settings.defaultMonth) monthInput.value = settings.defaultMonth;
    if (settings.defaultYear) yearInput.value = settings.defaultYear;
    if (settings.defaultCvv) cvvInput.value = settings.defaultCvv;
    if (settings.defaultCardType) {
      selectedType = settings.defaultCardType;
      typeBtns.forEach(b => b.classList.toggle('active', b.dataset.type === selectedType));
      applyNetworkUI(selectedType);
    }
    if (settings.defaultCountry) {
      updateCountryUI(settings.defaultCountry);
    }
  }

  // ─── Log (with persistence) ───────────────────────────────
  let logEntries = [];

  function addLog(type, icon, msg) {
    const empty = logContainer.querySelector('.log-empty');
    if (empty) empty.remove();
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `<span class="log-icon">${icon}</span><span class="log-text">${escapeHtml(msg)}</span>`;
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
    logEntries.push({ type, icon, msg });
    chrome.storage.local.set({ afLog: logEntries });
  }

  function renderLog(entries) {
    logContainer.innerHTML = '';
    if (!entries || entries.length === 0) {
      logContainer.innerHTML = '<div class="log-empty">Waiting for fill action...</div>';
      return;
    }
    entries.forEach(e => {
      const el = document.createElement('div');
      el.className = `log-entry ${e.type}`;
      el.innerHTML = `<span class="log-icon">${e.icon}</span><span class="log-text">${escapeHtml(e.msg)}</span>`;
      logContainer.appendChild(el);
    });
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Listen for logs from content scripts (multi-frame)
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === 'log_step') {
      addLog(msg.type, msg.icon, msg.msg);
    }
  });

  function sendFillMessage(tabId, payload, done, retried = false) {
    chrome.tabs.sendMessage(tabId, payload, (response) => {
      const lastError = chrome.runtime.lastError;
      const errorMessage = lastError ? lastError.message : '';

      if (!lastError) { done(response, ''); return; }

      if (!retried && /Receiving end does not exist/i.test(errorMessage)) {
        addLog('warn', '↻', 'Content script missing. Injecting and retrying...');
        injectContentScripts(tabId, (injectError) => {
          if (injectError) { done(null, injectError); return; }
          window.setTimeout(() => { sendFillMessage(tabId, payload, done, true); }, 150);
        });
        return;
      }

      done(response, errorMessage);
    });
  }

  function injectContentScripts(tabId, done) {
    if (!chrome.scripting || !chrome.scripting.executeScript) {
      done('Content script is not available. Reload the extension and refresh the page.');
      return;
    }
    chrome.scripting.executeScript({
      target: { tabId, allFrames: true },
      files: ['cardGenerator.js', 'dataGenerator.js', 'subscribeClicker.js', 'captchaSolver.js', 'content.js']
    }, () => {
      const lastError = chrome.runtime.lastError;
      done(lastError ? lastError.message : '');
    });
  }

  function detectCurrentTab() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]) return;
      try {
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
      } catch (_) { }
    });
  }

  function loadSettings() {
    chrome.storage.local.get(['afSettings', 'afLog', 'standaloneCaptcha'], (res) => {
      if (res.afSettings) {
        settings = { ...settings, ...res.afSettings };
      }
      
      globalSettings.standaloneCaptcha = !!res.standaloneCaptcha;
      
      if (autoCaptchaToggle) autoCaptchaToggle.checked = globalSettings.standaloneCaptcha;

      applySettingsToMainForm();

      if (res.afLog && res.afLog.length) {
        logEntries = res.afLog;
        renderLog(logEntries);
      }
    });
  }

});
