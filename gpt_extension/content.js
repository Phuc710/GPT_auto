// Content script for Auto Fill GPT extension (v4)
// Runs in ALL frames. Each frame fills ONLY its own fields.
// Top frame: billing address. Stripe iframe: card fields.

'use strict';

const fillLog = [];

function logStep(type, icon, msg) {
  fillLog.push({ type, icon, msg });
  console.log(`[AutoFill] ${icon} ${msg}`);

  // Broadcast log to popup for real-time visibility
  chrome.runtime.sendMessage({
    action: 'log_step',
    type,
    icon,
    msg
  }).catch(() => { });
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action !== 'fillForm') return undefined;

  const isTop = (window === window.top);
  const delay = request.fillDelay || 100;

  if (!isTop) {
    // ── SUB-FRAME (Stripe, etc.): fill card + address fields ──
    // ChatGPT embeds billing address fields INSIDE the Stripe iframe!
    // Don't sendResponse — only top frame responds to popup.
    fillCardFieldsInFrame(request.cardData, request.address || {}, delay).catch(() => { });
    return false;
  }

  // ── TOP FRAME: fill address + respond to popup ──
  fillLog.length = 0;
  const address = request.address || {};

  fillTopFrame(request.cardData, delay, address)
    .then(() => sendResponse({ success: true, log: [...fillLog] }))
    .catch((err) => {
      logStep('error', '✗', `Fatal: ${err.message}`);
      sendResponse({ success: false, error: err.message, log: [...fillLog] });
    });

  return true; // keep channel open for async sendResponse
});

// ═════════════════════════════════════════════════════════════
// TOP FRAME: fills billing address fields in its own document
// ═════════════════════════════════════════════════════════════
async function fillTopFrame(cardData, delay, address) {
  const stepDelay = Math.max(delay, 220);

  // Check hasAddress — ignore internal _isRandom / _source keys
  const addrValues = Object.entries(address || {})
    .filter(([k]) => !k.startsWith('_'))
    .map(([, v]) => v);
  const hasAddress = addrValues.some(v => v && v !== false);

  // Also try to find card fields in own document (rare but possible)
  const fields = scanPaymentFields();
  const anyCard = fields.cardNumberField || fields.combinedExpiryField ||
    fields.expiryMonthField || fields.expiryYearField || fields.cvvField;

  if (anyCard) {
    await fillCardFields(cardData, fields, stepDelay);
  }

  if (hasAddress) {
    await fillBillingAddress(address, stepDelay);
  }
}

// ═════════════════════════════════════════════════════════════
// SUB-FRAME: fills card + billing address in its own document
// ChatGPT uses 2 SEPARATE Stripe iframes:
//   - elements-inner-payment-*.html  → card fields only
//   - elements-inner-address-*.html  → billing address only
// Both receive the fillForm message, each fills what it has.
// ═════════════════════════════════════════════════════════════
async function fillCardFieldsInFrame(cardData, address, delay) {
  const stepDelay = Math.max(delay, 220);

  const addrValues = Object.entries(address || {})
    .filter(([k]) => !k.startsWith('_'))
    .map(([, v]) => v);
  const hasAddress = addrValues.some(v => v && v !== false);

  // ── Try card fields ──
  let fields = scanPaymentFields();
  if (!hasAnyPaymentField(fields)) {
    // Wait once — Stripe fields may load late
    await sleep(stepDelay);
    fields = scanPaymentFields();
  }

  const hasCard = hasAnyPaymentField(fields);

  if (hasCard) {
    await fillCardFields(cardData, fields, stepDelay);
    if (hasAddress) {
      await fillBillingAddress(address, stepDelay);
    }
    logStep('info', '✅', `Done — ${window.location.origin}`);
    return;
  }

  // ── No card fields: might be the ADDRESS iframe ──
  if (hasAddress) {
    const nameField = await waitForField(
      ['#billingAddress-nameInput', '[name="name"]', '[autocomplete="billing name"]'],
      ['full name', 'name'], stepDelay
    );
    if (nameField) {
      await fillBillingAddress(address, stepDelay);
      logStep('info', '✅', `Done — ${window.location.origin}`);
      return;
    }
  }
}

// ═════════════════════════════════════════════════════════════
// SHARED: fill card fields from a scan result
// ═════════════════════════════════════════════════════════════
async function fillCardFields(cardData, fields, stepDelay) {
  const { cardNumberField, combinedExpiryField, expiryMonthField, expiryYearField, cvvField } = fields;

  const month = cardData.expiry?.month || cardData.month;
  const year = cardData.expiry?.year || cardData.year;
  const yearShort = cardData.expiry?.yearShort || String(year).slice(-2);

  if (cardNumberField) {
    await fillField(cardNumberField, cardData.number || '', stepDelay);
    logStep('success', '💳', `PAN: ${cardData.number?.replace(/\s/g, '').replace(/(\d{4})/g, '$1 ').trim().replace(/\d{4} \d{4} \d{4} (\d{4})/, '•••• •••• •••• $1')}`);
  }

  if (combinedExpiryField) {
    const expiryValue = formatExpiryForField(combinedExpiryField, month, year, yearShort);
    await fillField(combinedExpiryField, expiryValue, stepDelay);
    logStep('success', '📅', `Expiry: ${expiryValue}`);
  } else {
    if (expiryMonthField) {
      await fillField(expiryMonthField, month, stepDelay);
    }
    if (expiryYearField) {
      await fillField(expiryYearField, year, yearShort, stepDelay);
    }
    if (expiryMonthField || expiryYearField) {
      logStep('success', '📅', `Expiry: ${month}/${yearShort}`);
    }
  }

  if (cvvField) {
    await fillField(cvvField, cardData.cvv || '', stepDelay);
    logStep('success', '🔒', `CVV: ${cardData.cvv || ''}`);
  }
}

// ═════════════════════════════════════════════════════════════
// BILLING ADDRESS (top frame only)
// ═════════════════════════════════════════════════════════════
async function fillBillingAddress(address, delay) {
  // 5. 👤 Name → 6. 🗺 State → 7. 🏙 City → 8. 🏠 Addr1 → Addr2 → 📮 Postal

  // ── Name ──
  const nameSelectors = [
    // ChatGPT / Stripe billing form
    '#billingAddress-nameInput',
    'input[data-testid="billing-name"]',
    'input[name="billingName"]',
    'input[name="billing_name"]',
    'input[name="name_on_card"]',
    'input[name="nameOnCard"]',
    'input[name="cardholder"]',
    'input[name="cardholder_name"]',
    'input[name="cardholderName"]',
    // Generic
    'input[autocomplete="cc-name"]',
    'input[autocomplete="billing name"]',
    'input[autocomplete="name"]',
    'input[name="name"]',
    'input[id*="name" i][type="text"]',
    'input[placeholder*="full name" i]',
    'input[placeholder*="cardholder" i]',
    'input[placeholder*="name on card" i]',
    'input[placeholder*="card holder" i]',
    'input[placeholder*="name" i]',
    'input[aria-label*="name" i]',
  ];
  const nameField = await waitForField(nameSelectors, ['full name', 'name on card', 'cardholder', 'billing name', 'name'], delay);
  if (nameField && address.name) {
    await fillField(nameField, address.name, delay);
    logStep('success', '👤', `Name: ${address.name}`);
  }

  // ── State / Province (Do Si) ──
  const stateField = findField([
    '#billingAddress-administrativeAreaInput',
    'select[autocomplete="billing address-level1"]',
    'select[autocomplete="address-level1"]',
    'select[name="administrativeArea"]',
    'select[name="state"]',
    'select[name="province"]',
    'select[id*="state" i]',
    'input[autocomplete="address-level1"]',
    'input[name="state"]',
    'input[name="province"]',
    'input[id*="state" i]',
    '#state',
  ], ['state', 'province', 'region', 'do si']);
  if (stateField && address.state) {
    if (stateField.tagName === 'SELECT') {
      const opts = Array.from(stateField.options);
      const match = opts.find((opt) =>
        opt.value.toLowerCase() === address.state.toLowerCase() ||
        opt.textContent.toLowerCase().includes(address.state.toLowerCase())
      );
      if (match) {
        await fillField(stateField, match.value, delay);
        logStep('success', '🗺', `State: ${address.state}`);
      }
    } else {
      await fillField(stateField, address.state, delay);
      logStep('success', '🗺', `State: ${address.state}`);
    }
  }

  // ── City ──
  const cityField = await waitForField([
    '#billingAddress-localityInput',
    'input[autocomplete="billing locality"]',
    'input[autocomplete="address-level2"]',
    'input[name="city"]',
    'input[name="locality"]',
    'input[id*="city" i]',
    'input[placeholder*="city" i]',
    'input[aria-label*="city" i]',
    '#city',
  ], ['city', 'town', 'locality'], delay);
  if (cityField && address.city) {
    await fillField(cityField, address.city, delay);
    logStep('success', '🏙', `City: ${address.city}`);
  }

  // ── Address Line 1 ──
  const addr1Field = await waitForField([
    '#billingAddress-addressLine1Input',
    'input[autocomplete="billing street-address"]',
    'input[autocomplete="address-line1"]',
    'input[name="addressLine1"]',
    'input[name="address_line_1"]',
    'input[name="address1"]',
    'input[name="street"]',
    'input[name="street_address"]',
    'input[id*="address" i][id*="1"]',
    'input[placeholder*="address line 1" i]',
    'input[placeholder*="street address" i]',
    'input[placeholder*="address" i]',
    'input[aria-label*="address line 1" i]',
  ], ['address line 1', 'address 1', 'street address', 'street'], delay);
  if (addr1Field && address.line1) {
    await fillField(addr1Field, address.line1, delay);
    logStep('success', '🏠', `Addr 1: ${address.line1}`);
  }

  // ── Address Line 2 ──
  const addr2Field = findField([
    '#billingAddress-addressLine2Input',
    'input[autocomplete="address-line2"]',
    'input[autocomplete="billing address-line2"]',
    'input[name="addressLine2"]',
    'input[name="address_line_2"]',
    'input[name="address2"]',
    'input[placeholder*="address line 2" i]',
    'input[placeholder*="apt" i]',
    'input[placeholder*="suite" i]',
    'input[aria-label*="address line 2" i]',
  ], ['address line 2', 'address 2', 'apt', 'suite', 'unit']);
  if (addr2Field && address.line2) {
    await fillField(addr2Field, address.line2, delay);
    logStep('success', '🏠', `Addr 2: ${address.line2}`);
  }

  // ── Postal Code ──
  const postalField = await waitForField([
    '#billingAddress-postalCodeInput',
    'input[autocomplete="billing postal-code"]',
    'input[autocomplete="postal-code"]',
    'input[name="postalCode"]',
    'input[name="postal_code"]',
    'input[name="zip"]',
    'input[name="zipcode"]',
    'input[id*="postal" i]',
    'input[id*="zip" i]',
    'input[placeholder*="postal" i]',
    'input[placeholder*="zip" i]',
    'input[aria-label*="postal" i]',
    'input[aria-label*="zip" i]',
    '#postal', '#zip',
  ], ['postal code', 'zip code', 'zip', 'postal'], delay);
  if (postalField && address.postal) {
    await fillField(postalField, address.postal, delay);
    logStep('success', '📮', `Postal: ${address.postal}`);
  }
}

// ═════════════════════════════════════════════════════════════
// FIELD SCANNING
// ═════════════════════════════════════════════════════════════
function hasAnyPaymentField(fields) {
  return Boolean(
    fields.cardNumberField ||
    fields.expiryMonthField ||
    fields.expiryYearField ||
    fields.combinedExpiryField ||
    fields.cvvField
  );
}

function shouldUseCombinedExpiryField(monthField, yearField, combinedField) {
  if (combinedField) return true;
  if (monthField && yearField && monthField === yearField) return true;
  if (looksLikeCombinedExpiryField(monthField)) return true;
  if (looksLikeCombinedExpiryField(yearField)) return true;
  return false;
}

function looksLikeCombinedExpiryField(field) {
  if (!field) return false;
  const text = [
    field.id || '', field.name || '',
    field.getAttribute('placeholder') || '',
    field.getAttribute('aria-label') || '',
    field.getAttribute('autocomplete') || '',
    getAssociatedLabelText(field)
  ].join(' ').toLowerCase();

  return /mm\s*\/\s*yy/.test(text) ||
    /mm\s*\/\s*yyyy/.test(text) ||
    /expir/.test(text) ||
    /payment-expiryinput/.test(text);
}

function scanPaymentFields() {
  return {
    cardNumberField: findField([
      'input[data-elements-stable-field-name="cardNumber"]',
      '#payment-numberInput',
      'input[id*="numberInput" i]',
      'input[class*="CardNumberInput" i]',
      'input[class*="cardNumber" i]',
      'input[autocomplete="cc-number"]',
      'input[name="number"]',
      'input[name*="cardnumber" i]',
      'input[name*="card_number" i]',
      'input[name*="ccnumber" i]',
      'input[name*="cc_number" i]',
      'input[name*="pan" i]',
      'input[placeholder*="1234 1234 1234" i]',
      'input[placeholder*="card number" i]',
      'input[placeholder*="credit card" i]',
      'input[placeholder*="debit card" i]',
      'input[id*="cardnumber" i]',
      'input[id*="card_number" i]',
      'input[id*="card-number" i]',
      'input[id*="ccnumber" i]',
      'input[id*="creditcard" i]',
      'input[data-testid*="card" i]',
      'input[data-cy*="card" i]',
      'input[aria-label*="card number" i]',
      '#cardNumber', '#card_number', '#ccNumber', '#cc_number',
      '#cardnumber', '#card-number', '#credit-card-number'
    ], ['card number', 'credit card', 'pan', 'card no']),

    expiryMonthField: findField([
      'select[name*="expmonth" i]', 'select[name*="exp_month" i]',
      'select[name*="card_month" i]', 'select[name*="month" i]',
      'input[name*="expmonth" i]', 'input[name*="exp_month" i]',
      'input[name*="cardmonth" i]', 'input[name*="month" i]',
      'select[id*="expmonth" i]', 'select[id*="exp_month" i]',
      'select[id*="month" i]',
      'input[placeholder*="mm" i][maxlength="2"]',
      'input[aria-label*="expiry month" i]',
      '#expiryMonth', '#expMonth', '#cardMonth', '#month'
    ], ['month', 'mm', 'exp month', 'expiry month']),

    expiryYearField: findField([
      'select[name*="expyear" i]', 'select[name*="exp_year" i]',
      'select[name*="card_year" i]', 'select[name*="year" i]',
      'input[name*="expyear" i]', 'input[name*="exp_year" i]',
      'input[name*="cardyear" i]', 'input[name*="year" i]',
      'select[id*="expyear" i]', 'select[id*="exp_year" i]',
      'select[id*="year" i]',
      'input[aria-label*="expiry year" i]',
      '#expiryYear', '#expYear', '#cardYear', '#year'
    ], ['year', 'yy', 'exp year', 'expiry year']),

    combinedExpiryField: findField([
      'input[data-elements-stable-field-name="cardExpiry"]',
      '#payment-expiryInput',
      'input[id*="expiryInput" i]',
      'input[class*="CardExpiryInput" i]',
      'input[autocomplete="cc-exp"]',
      'input[name*="expiry" i]', 'input[name*="expdate" i]',
      'input[name*="exp-date" i]', 'input[name*="card_exp" i]',
      'input[placeholder*="mm/yy" i]', 'input[placeholder*="mm / yy" i]',
      'input[placeholder*="mm/yyyy" i]',
      'input[placeholder*="expiry" i]', 'input[placeholder*="expiration" i]',
      'input[id*="expiry" i]', 'input[id*="expdate" i]',
      'input[aria-label*="expiration" i]', 'input[aria-label*="expiry" i]',
      'input[data-testid*="expiry" i]',
      '#expiry', '#expiryDate', '#expDate', '#cardExpiry'
    ], ['expiry', 'expiration', 'mm / yy', 'mm/yy']),

    cvvField: findField([
      'input[data-elements-stable-field-name="cardCvc"]',
      '#payment-cvcInput',
      'input[id*="cvcInput" i]',
      'input[class*="CardCvcInput" i]',
      'input[autocomplete="cc-csc"]',
      'input[name*="cvv" i]', 'input[name*="cvc" i]',
      'input[name*="cvv2" i]', 'input[name*="csc" i]',
      'input[name*="security_code" i]', 'input[name*="securitycode" i]',
      'input[placeholder*="cvv" i]', 'input[placeholder*="cvc" i]',
      'input[placeholder*="security" i]',
      'input[id*="cvv" i]', 'input[id*="cvc" i]', 'input[id*="security" i]',
      'input[aria-label*="cvv" i]', 'input[aria-label*="cvc" i]',
      'input[aria-label*="security code" i]',
      'input[data-testid*="cvv" i]',
      '#cvv', '#cvc', '#securityCode', '#securitycode', '#cardCvv'
    ], ['cvv', 'cvc', 'security code', 'cvv2'])
  };
}

// ═════════════════════════════════════════════════════════════
// FIELD SEARCH — each frame searches ONLY its own document
// ═════════════════════════════════════════════════════════════

/**
 * Like findField() but retries up to ~3 seconds for lazily-rendered fields.
 * Useful for billing address fields that appear after card iframe loads.
 */
async function waitForField(selectors, labels = [], baseDelay = 220) {
  const maxWait = 3000;
  const interval = Math.max(200, Math.min(400, baseDelay));
  const tries = Math.ceil(maxWait / interval);

  for (let i = 0; i < tries; i++) {
    const found = findField(selectors, labels);
    if (found) return found;
    if (i < tries - 1) await sleep(interval);
  }
  return null;
}

function findField(selectors, labels = []) {
  const doc = document;

  const selectorMatch = findFieldBySelectors(doc, selectors);
  if (selectorMatch) return selectorMatch;

  if (!labels.length) return null;

  const labelMatch = findFieldByLabels(doc, labels);
  return labelMatch || null;
}

function findFieldBySelectors(doc, selectors) {
  for (const sel of selectors) {
    try {
      const matches = Array.from(doc.querySelectorAll(sel));
      const candidate = matches.find(isVisible) || matches.find(isUsableField);
      if (candidate) return candidate;
    } catch (_) { }
  }
  return null;
}

function findFieldByLabels(doc, labels) {
  const allInputs = Array.from(doc.querySelectorAll('input, select, textarea'));
  const allLabels = Array.from(doc.querySelectorAll('label'));

  for (const labelText of labels) {
    const regex = new RegExp(escapeRegex(labelText), 'i');

    for (const lbl of allLabels) {
      if (!regex.test(lbl.textContent || '')) continue;
      const forId = lbl.getAttribute('for');
      const candidate = (forId && doc.getElementById(forId)) || lbl.querySelector('input, select, textarea');
      if (candidate && (isVisible(candidate) || isUsableField(candidate))) return candidate;
    }

    for (const input of allInputs) {
      const haystack = [
        input.getAttribute('placeholder') || '',
        input.getAttribute('aria-label') || '',
        input.getAttribute('autocomplete') || '',
        input.name || '', input.id || ''
      ].join(' ');
      if (regex.test(haystack) && (isVisible(input) || isUsableField(input))) return input;
    }
  }
  return null;
}

// ═════════════════════════════════════════════════════════════
// UTILITIES
// ═════════════════════════════════════════════════════════════
function fieldDesc(el) {
  if (el.id) return `#${el.id}`;
  if (el.name) return `[name="${el.name}"]`;
  if (el.getAttribute('placeholder')) return `[placeholder="${el.getAttribute('placeholder').slice(0, 20)}"]`;
  return el.tagName.toLowerCase();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getAssociatedLabelText(field) {
  if (!field || !field.ownerDocument) return '';
  const labels = [];
  const fieldId = field.id;
  if (fieldId) {
    for (const label of field.ownerDocument.querySelectorAll(`label[for="${cssEscape(fieldId)}"]`)) {
      labels.push(label.textContent || '');
    }
  }
  let parent = field.parentElement;
  while (parent) {
    if (parent.tagName === 'LABEL') { labels.push(parent.textContent || ''); break; }
    parent = parent.parentElement;
  }
  return labels.join(' ');
}

function cssEscape(value) {
  if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') return CSS.escape(value);
  return String(value).replace(/["\\]/g, '\\$&');
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function isUsableField(el) {
  return Boolean(el) && !el.disabled && !el.readOnly;
}

function isVisible(el) {
  if (!el) return false;
  const view = el.ownerDocument?.defaultView || window;
  const style = view.getComputedStyle(el);
  const rect = el.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0 &&
    !el.disabled && style.visibility !== 'hidden' &&
    style.display !== 'none' && style.opacity !== '0';
}

async function fillField(field, value, delay = 220) {
  field.focus();
  const view = field.ownerDocument?.defaultView || window;
  let nativeSetter = null;

  if (field.tagName === 'INPUT') {
    nativeSetter = Object.getOwnPropertyDescriptor(view.HTMLInputElement.prototype, 'value');
  } else if (field.tagName === 'TEXTAREA') {
    nativeSetter = Object.getOwnPropertyDescriptor(view.HTMLTextAreaElement.prototype, 'value');
  } else if (field.tagName === 'SELECT') {
    nativeSetter = Object.getOwnPropertyDescriptor(view.HTMLSelectElement.prototype, 'value');
  }

  if (field.tagName === 'SELECT') {
    if (nativeSetter?.set) nativeSetter.set.call(field, value);
    else field.value = value;
    ['input', 'change', 'blur'].forEach((e) => field.dispatchEvent(new Event(e, { bubbles: true })));
    field.blur();
    return;
  }

  await clearTextField(field, nativeSetter);
  await typeTextLikeHuman(field, String(value ?? ''), nativeSetter, delay);
  field.dispatchEvent(new Event('change', { bubbles: true }));
  field.blur();
}

async function fillMonthField(field, month, delay = 220) {
  if (!month) return;
  const padded = String(month).padStart(2, '0');
  const numeric = String(parseInt(padded, 10));
  if (field.tagName === 'SELECT') {
    const candidates = [padded, numeric, monthName(padded), monthName(padded).slice(0, 3)];
    const opt = findMatchingOption(field, candidates);
    if (opt) { await fillField(field, opt.value, delay); return; }
  }
  await fillField(field, padded, delay);
}

async function fillYearField(field, fullYear, shortYear, delay = 220) {
  if (!fullYear && !shortYear) return;
  const fy = String(fullYear || '');
  const sy = String(shortYear || fy.slice(-2));
  if (field.tagName === 'SELECT') {
    const opt = findMatchingOption(field, [fy, sy, fy.slice(-2)]);
    if (opt) { await fillField(field, opt.value, delay); return; }
  }
  await fillField(field, fy || sy, delay);
}

async function clearTextField(field, nativeSetter) {
  setFieldValue(field, '', nativeSetter);
  field.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward', data: null }));
  await sleep(40);
}

async function typeTextLikeHuman(field, value, nativeSetter, delay) {
  const perCharDelay = Math.max(35, Math.min(120, Math.round(delay / 4)));
  for (const char of value) {
    dispatchKeyboardEvent(field, 'keydown', char);
    dispatchKeyboardEvent(field, 'keypress', char);
    setFieldValue(field, `${field.value}${char}`, nativeSetter);
    field.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: char }));
    dispatchKeyboardEvent(field, 'keyup', char);
    await sleep(perCharDelay);
  }
}

function setFieldValue(field, value, nativeSetter) {
  if (nativeSetter?.set) nativeSetter.set.call(field, value);
  else field.value = value;
}

function dispatchKeyboardEvent(field, type, key) {
  let code = 'Unidentified';
  if (/^\d$/.test(key)) code = `Digit${key}`;
  else if (/^[a-z]$/i.test(key)) code = `Key${key.toUpperCase()}`;
  else if (key === '/') code = 'Slash';
  else if (key === ' ') code = 'Space';

  field.dispatchEvent(new KeyboardEvent(type, {
    key, code, keyCode: key.charCodeAt(0), which: key.charCodeAt(0), bubbles: true
  }));
}

function findMatchingOption(select, candidates) {
  const normalized = candidates.filter(Boolean).map(c => c.toString().trim().toLowerCase());
  return Array.from(select.options).find((opt) => {
    const value = opt.value.toString().trim().toLowerCase();
    const label = opt.textContent.toString().trim().toLowerCase();
    return normalized.some(c =>
      value === c || label === c ||
      value.replace(/^0/, '') === c.replace(/^0/, '') ||
      label.replace(/^0/, '') === c.replace(/^0/, '')
    );
  }) || null;
}

function monthName(month) {
  const names = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  return names[parseInt(month, 10) - 1] || month;
}

function formatCardDisplay(number) {
  const clean = String(number).replace(/\D/g, '');
  return `•••• •••• •••• ${clean.slice(-4)}`;
}

function formatExpiryForField(field, month, year, yearShort) {
  const fullYear = String(year || '');
  const short = String(yearShort || fullYear.slice(-2));
  const text = [
    field?.getAttribute('placeholder') || '', field?.getAttribute('aria-label') || '',
    field?.name || '', field?.id || '', getAssociatedLabelText(field)
  ].join(' ').toLowerCase();
  if (/yyyy/.test(text)) return `${month}/${fullYear}`;
  return `${month}/${short}`;
}
