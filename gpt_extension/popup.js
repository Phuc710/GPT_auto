// Auto Fill GPT - Popup Script (v5 Refactor)
'use strict';

document.addEventListener('DOMContentLoaded', () => {
  // --- Elements ---
  const el = {
    binInput: document.getElementById('binInput'),
    monthInput: document.getElementById('monthInput'),
    yearInput: document.getElementById('yearInput'),
    cvvInput: document.getElementById('cvvInput'),
    binTypeBadge: document.getElementById('binTypeBadge'),
    typeBtns: document.querySelectorAll('.type-btn'),
    fillFullBtn: document.getElementById('fillFullBtn'),
    fillCardBtn: document.getElementById('fillCardBtn'),
    clearLogBtn: document.getElementById('clearLogBtn'),
    logContainer: document.getElementById('logContainer'),
    pageStatus: document.getElementById('pageStatus'),
    pageUrl: document.getElementById('pageUrl'),
    reloadTabBtn: document.getElementById('reloadTabBtn'),
    autoCaptchaToggle: document.getElementById('autoCaptchaToggle'),
    settingsBtn: document.getElementById('settingsBtn'),
    backBtn: document.getElementById('backBtn'),
    mainScreen: document.getElementById('mainScreen'),
    settingsScreen: document.getElementById('settingsScreen'),
    saveSettingsBtn: document.getElementById('saveSettingsBtn'),
    settings: {
      bin: document.getElementById('defaultBin'),
      type: document.getElementById('defaultCardType'),
      month: document.getElementById('defaultMonth'),
      year: document.getElementById('defaultYear'),
      cvv: document.getElementById('defaultCvv'),
      country: document.getElementById('defaultCountry'),
      name: document.getElementById('defaultName'),
      state: document.getElementById('defaultState'),
      city: document.getElementById('defaultCity'),
      addr1: document.getElementById('defaultAddress1'),
      addr2: document.getElementById('defaultAddress2'),
      postal: document.getElementById('defaultPostal'),
      delay: document.getElementById('fillDelay')
    }
  };

  // --- State ---
  let selectedType = '';
  let appSettings = {
    fillDelay: 100,
    defaultBin: '', defaultCardType: '',
    defaultMonth: '', defaultYear: '', defaultCvv: '',
    defaultCountry: 'KR',
    defaultName: '', defaultState: '',
    defaultAddress1: '', defaultAddress2: '',
    defaultCity: '', defaultPostal: ''
  };

  // --- Initialization ---
  init();

  function init() {
    loadSettings();
    updateTabInfo();
    setupEventListeners();
  }

  function setupEventListeners() {
    // Navigation
    el.settingsBtn.addEventListener('click', () => toggleScreen('settings'));
    el.backBtn.addEventListener('click', () => toggleScreen('main'));

    // Form inputs
    el.binInput.addEventListener('input', handleBinInput);
    [el.monthInput, el.yearInput, el.cvvInput].forEach(input => {
      input.addEventListener('input', e => { e.target.value = e.target.value.replace(/\D/g, ''); });
    });

    // Action buttons
    el.fillFullBtn.addEventListener('click', () => startFill(true));
    el.fillCardBtn.addEventListener('click', () => startFill(false));
    el.clearLogBtn.addEventListener('click', clearLogs);
    el.reloadTabBtn.addEventListener('click', reloadTab);
    el.saveSettingsBtn.addEventListener('click', saveSettings);

    // Feature toggles
    el.autoCaptchaToggle.addEventListener('change', toggleAutoCaptcha);
    
    // Quick selectors (card type only — country moved to Settings)
    el.typeBtns.forEach(btn => btn.addEventListener('click', () => selectCardType(btn.dataset.type)));

    // Global listeners
    chrome.runtime.onMessage.addListener(msg => {
      if (msg.action === 'log_step') addLog(msg.type, msg.icon, msg.msg);
    });
  }

  // --- Core Handlers ---

  function handleBinInput() {
    let val = el.binInput.value.trim();
    
    // Smart Pipe Parse (number|mm|yy|cvv)
    if (val.includes('|')) {
      const parts = val.split('|').map(p => p.trim());
      if (parts.length >= 3) {
        el.binInput.value = parts[0].replace(/\D/g, '');
        el.monthInput.value = parts[1].replace(/\D/g, '');
        el.yearInput.value = parts[2].replace(/\D/g, '');
        if (parts[3]) el.cvvInput.value = parts[3].replace(/\D/g, '');
        
        addLog('success', '🧬', `Smart parsed: ${el.binInput.value.slice(0,6)}...`);
        val = el.binInput.value;
      }
    }

    el.binInput.value = val.replace(/\D/g, '');
    const detected = CardGenerator.detectCardType(el.binInput.value);
    if (!selectedType) updateNetworkUI(detected ? detected.type : null);
  }

  function selectCardType(type) {
    if (selectedType === type) {
      selectedType = '';
      el.typeBtns.forEach(b => b.classList.remove('active'));
      const detected = CardGenerator.detectCardType(el.binInput.value);
      updateNetworkUI(detected ? detected.type : null);
    } else {
      selectedType = type;
      el.typeBtns.forEach(b => b.classList.toggle('active', b.dataset.type === type));
      updateNetworkUI(type);
      if (!el.binInput.value) {
        el.binInput.value = CardGenerator.generateRandomBIN(type);
        el.binInput.dispatchEvent(new Event('input'));
      }
    }
  }

  function selectCountry(code) {
    appSettings.defaultCountry = code;
    updateCountryUI(code);
    chrome.storage.local.set({ afSettings: appSettings });
    addLog('info', '🌍', `Target country: ${code}`);
  }

  // --- Automation Flow ---

  async function startFill(isFull) {
    const card = buildCardPayload();
    if (!card) return;

    el.logContainer.innerHTML = '';
    setLoading(true);

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) { addLog('error', '✗', 'No active tab'); setLoading(false); return; }

    const baseDelay = appSettings.fillDelay || 150;

    // Step 1: Fill Card
    await fillPhase(tab.id, { action: 'fillCard', cardData: card, fillDelay: baseDelay });

    if (isFull) {
      // Step 2: Gap between Card and Billing (2x Delay as requested)
      await sleep(baseDelay * 2);
      const addr = buildAddressPayload();
      if (addr._isRandom) addLog('info', '🎲', `Random address: ${addr.name} (${addr.city})`);
      await fillPhase(tab.id, { action: 'fillBilling', address: addr, fillDelay: baseDelay });
    }

    // Step 3: Click Subscribe (1x Delay after fill is done)
    await sleep(baseDelay);
    chrome.tabs.sendMessage(tab.id, { action: 'trigger_subscribe_now' });

    chrome.storage.local.set({ lastFilledAt: new Date().toISOString() });
    setLoading(false);
  }

  function fillPhase(tabId, payload) {
    return new Promise(resolve => {
      chrome.runtime.sendMessage({ action: 'fill_status', status: 'reset' });

      const timeout = setTimeout(resolve, 8000); // safety
      const handler = (msg) => {
        if (msg.action === 'phase_done') {
          chrome.runtime.onMessage.removeListener(handler);
          clearTimeout(timeout);
          resolve();
        }
      };
      chrome.runtime.onMessage.addListener(handler);

      sendToTab(tabId, payload, (res, err) => {
        if (err) {
          addLog('warn', '⚠', err);
          // If injection completely fails, resolve after delay
          setTimeout(() => {
            chrome.runtime.onMessage.removeListener(handler);
            clearTimeout(timeout);
            resolve();
          }, 2000);
        }
      });
    });
  }

  function sendToTab(tabId, payload, callback, isRetry = false) {
    chrome.tabs.sendMessage(tabId, payload, res => {
      const err = chrome.runtime.lastError;
      if (!err) return callback(res, null);

      if (!isRetry && /Receiving end does not exist/i.test(err.message)) {
        addLog('warn', '↻', 'Injecting engine...');
        chrome.scripting.executeScript({
          target: { tabId, allFrames: true },
          files: ['cardGenerator.js', 'dataGenerator.js', 'subscribeClicker.js', 'captchaSolver.js', 'content.js']
        }, () => {
          setTimeout(() => sendToTab(tabId, payload, callback, true), payload.fillDelay || 100);
        });
        return;
      }
      callback(null, err.message);
    });
  }

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  // --- Helpers ---

  function buildCardPayload() {
    const bin = el.binInput.value.trim();
    if (!bin) { addLog('error', '✗', 'BIN required'); return null; }
    try {
      return CardGenerator.generateFullCard(bin, {
        month: el.monthInput.value.trim() || null,
        year: el.yearInput.value.trim() || null,
        cvv: el.cvvInput.value.trim() || null,
        cardType: selectedType || undefined
      });
    } catch (e) {
      addLog('error', '✗', `Card error: ${e.message}`);
      return null;
    }
  }

  function buildAddressPayload() {
    const s = appSettings;
    const hasManual = s.defaultName && s.defaultState && s.defaultCity && s.defaultAddress1 && s.defaultPostal;
    if (hasManual) {
      return {
        name: s.defaultName, state: s.defaultState, city: s.defaultCity,
        line1: s.defaultAddress1, line2: s.defaultAddress2 || '',
        postal: s.defaultPostal, _isRandom: false
      };
    }
    return { ...window.DataGenerator.getRandomAddress(s.defaultCountry || 'KR'), _isRandom: true };
  }

  // --- UI State Management ---

  function toggleScreen(screen) {
    if (screen === 'settings') {
      populateSettingsUI();
      el.mainScreen.style.display = 'none';
      el.settingsScreen.style.display = 'flex';
    } else {
      el.settingsScreen.style.display = 'none';
      el.mainScreen.style.display = 'flex';
    }
  }

  function setLoading(loading) {
    el.fillFullBtn.disabled = loading;
    el.fillCardBtn.disabled = loading;
    el.fillFullBtn.textContent = loading ? 'Filling...' : 'Fill Full';
    el.fillCardBtn.textContent = loading ? 'Filling...' : 'Fill Card';
  }

  function updateNetworkUI(typeKey) {
    if (!typeKey) {
      el.binTypeBadge.textContent = 'AUTO';
      el.binTypeBadge.style.background = '#30363d';
      return;
    }
    const info = CardGenerator.CARD_TYPES[typeKey];
    if (info) {
      el.binTypeBadge.textContent = info.shortName;
      el.binTypeBadge.style.background = info.color;
    }
  }

  function updateCountryUI(code) {
    // Country is now managed only in Settings dropdown
    if (el.settings.country) el.settings.country.value = code;
  }

  function addLog(type, icon, msg) {
    const empty = el.logContainer.querySelector('.log-empty');
    if (empty) empty.remove();
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `<span class="log-icon">${icon}</span><span class="log-text">${escapeHtml(msg)}</span>`;
    
    el.logContainer.appendChild(entry);
    el.logContainer.scrollTop = el.logContainer.scrollHeight;
    
    // Save to storage (limit to last 50)
    chrome.storage.local.get(['afLog'], res => {
      const logs = res.afLog || [];
      logs.push({ type, icon, msg });
      chrome.storage.local.set({ afLog: logs.slice(-50) });
    });
  }

  function clearLogs() {
    chrome.storage.local.remove('afLog');
    el.logContainer.innerHTML = '<div class="log-empty">Waiting for fill action...</div>';
  }

  function reloadTab() {
    chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
      if (tab) chrome.tabs.reload(tab.id);
    });
  }

  function toggleAutoCaptcha(e) {
    chrome.storage.local.set({ standaloneCaptcha: e.target.checked });
    addLog('info', '🤖', `Captcha ${e.target.checked ? 'ON' : 'OFF'}`);
  }

  // --- Settings Persistence ---

  function saveSettings() {
    const s = el.settings;
    appSettings = {
      defaultBin: s.bin.value.replace(/\D/g, ''),
      defaultCardType: s.type.value,
      defaultMonth: s.month.value.replace(/\D/g, ''),
      defaultYear: s.year.value.replace(/\D/g, ''),
      defaultCvv: s.cvv.value.replace(/\D/g, ''),
      defaultCountry: s.country.value,
      defaultName: s.name.value.trim(),
      defaultState: s.state.value.trim(),
      defaultCity: s.city.value.trim(),
      defaultAddress1: s.addr1.value.trim(),
      defaultAddress2: s.addr2.value.trim(),
      defaultPostal: s.postal.value.trim(),
      fillDelay: parseInt(s.delay.value) || 100
    };

    chrome.storage.local.set({ afSettings: appSettings }, () => {
      updateMainFormFromSettings();
      el.saveSettingsBtn.textContent = '✓ Saved';
      setTimeout(() => el.saveSettingsBtn.textContent = '💾 Save Settings', 1500);
    });
  }

  function loadSettings() {
    chrome.storage.local.get(['afSettings', 'afLog', 'standaloneCaptcha'], res => {
      if (res.afSettings) appSettings = { ...appSettings, ...res.afSettings };
      if (el.autoCaptchaToggle) el.autoCaptchaToggle.checked = !!res.standaloneCaptcha;
      
      updateMainFormFromSettings();
      if (res.afLog) renderLogs(res.afLog);
    });
  }

  function populateSettingsUI() {
    const s = el.settings;
    const v = appSettings;
    s.bin.value = v.defaultBin;
    s.type.value = v.defaultCardType;
    s.month.value = v.defaultMonth;
    s.year.value = v.defaultYear;
    s.cvv.value = v.defaultCvv;
    s.country.value = v.defaultCountry;
    s.name.value = v.defaultName;
    s.state.value = v.defaultState;
    s.city.value = v.defaultCity;
    s.addr1.value = v.defaultAddress1;
    s.addr2.value = v.defaultAddress2;
    s.postal.value = v.defaultPostal;
    s.delay.value = v.fillDelay;
  }

  function updateMainFormFromSettings() {
    const v = appSettings;
    if (v.defaultBin) {
      el.binInput.value = v.defaultBin;
      el.binInput.dispatchEvent(new Event('input'));
    }
    el.monthInput.value = v.defaultMonth;
    el.yearInput.value = v.defaultYear;
    el.cvvInput.value = v.defaultCvv;
    if (v.defaultCardType) selectCardType(v.defaultCardType);
    updateCountryUI(v.defaultCountry);
  }

  function renderLogs(logs) {
    if (!logs.length) return;
    el.logContainer.innerHTML = '';
    logs.forEach(l => {
      const entry = document.createElement('div');
      entry.className = `log-entry ${l.type}`;
      entry.innerHTML = `<span class="log-icon">${l.icon}</span><span class="log-text">${escapeHtml(l.msg)}</span>`;
      el.logContainer.appendChild(entry);
    });
    el.logContainer.scrollTop = el.logContainer.scrollHeight;
  }

  function updateTabInfo() {
    chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
      if (!tab) return;
      try {
        const url = new URL(tab.url).hostname;
        el.pageUrl.textContent = url;
        const isCheckout = /pay|checkout|billing|payment|order|cart/i.test(tab.url);
        el.pageStatus.textContent = isCheckout ? 'Checkout detected' : 'Standard page';
        el.pageStatus.parentElement.style.color = isCheckout ? '#10a37f' : '#8e8ea0';
      } catch (_) {}
    });
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }
});
