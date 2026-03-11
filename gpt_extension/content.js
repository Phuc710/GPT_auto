// Content script for Auto Fill GPT extension (v3)
// Fills payment forms with generated card data

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
  }).catch(() => {
    // Ignore error if popup is closed
  });
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action !== 'fillForm') return undefined;

  // Only the top-level frame handles the fill.
  // iframes (Stripe, hcaptcha, etc.) are searched internally by collectSearchDocuments.
  // Without this guard every iframe runs in parallel → log spam + city field race condition.
  if (window !== window.top) return undefined;

  fillLog.length = 0;
  const delay = request.fillDelay || 100;

  fillPaymentForm(request.cardData, delay, request.address || {})
    .then(() => sendResponse({ success: true, log: [...fillLog] }))
    .catch((err) => {
      logStep('error', '✗', `Fatal: ${err.message}`);
      sendResponse({ success: false, error: err.message, log: [...fillLog] });
    });

  return true;
});

async function fillPaymentForm(cardData, delay = 100, address = {}) {
  const stepDelay = Math.max(delay, 220);
  const hasAddress = address && Object.values(address).some(v => v);

  // ── Step 1: Scan for card fields ─────────────────────────
  logStep('info', '🔍', 'Scanning page for payment fields...');

  let {
    cardNumberField,
    expiryMonthField,
    expiryYearField,
    combinedExpiryField,
    cvvField
  } = await discoverPaymentFields(stepDelay);

  if (shouldUseCombinedExpiryField(expiryMonthField, expiryYearField, combinedExpiryField)) {
    combinedExpiryField = combinedExpiryField || expiryMonthField || expiryYearField;
    expiryMonthField = null;
    expiryYearField = null;
  }

  const anyCardField = cardNumberField || expiryMonthField || combinedExpiryField || expiryYearField || cvvField;
  // If this frame has no card fields AND no address to fill, silently exit
  if (!anyCardField && !hasAddress) {
    return;
  }

  // ── Step 2: Name (first, inside billing address block) ────
  if (hasAddress && address.name) {
    const nameField = findField([
      '#billingAddress-nameInput',
      'input[name="name"][autocomplete*="name"]',
      'input[name="billingName" i]',
      'input[placeholder*="full name" i]',
      'input[placeholder*="name" i]'
    ], ['full name', 'name', 'billing name', 'name on card']);
    if (nameField) {
      await sleep(stepDelay);
      await fillField(nameField, address.name, stepDelay);
      logStep('success', '✓', `Name: ${address.name}`);
    }
  }

  // ── Step 3: Card Number ───────────────────────────────────
  if (cardNumberField) {
    logStep('step', '💳', `Card number field found (${fieldDesc(cardNumberField)})`);
    await sleep(stepDelay);
    await fillField(cardNumberField, cardData.number, stepDelay);
    logStep('success', '✓', `PAN filled: ${formatCardDisplay(cardData.number)}`);
  } else if (anyCardField) {
    logStep('warn', '⚠', 'Card number field: not found');
  }

  const month = cardData.expiry?.month || cardData.month;
  const year = cardData.expiry?.year || cardData.year;
  const yearShort = cardData.expiry?.yearShort || String(year).slice(-2);

  // ── Step 4: Expiry ────────────────────────────────────────
  if (combinedExpiryField && !expiryMonthField) {
    logStep('step', '📅', `Combined expiry field found (${fieldDesc(combinedExpiryField)})`);
    await sleep(stepDelay);
    const expiryValue = formatExpiryForField(combinedExpiryField, month, year, yearShort);
    await fillField(combinedExpiryField, expiryValue, stepDelay);
    logStep('success', '✓', `Expiry filled: ${expiryValue}`);
  } else {
    if (expiryMonthField) {
      logStep('step', '📅', `Month field found (${fieldDesc(expiryMonthField)})`);
      await sleep(stepDelay);
      await fillMonthField(expiryMonthField, month, stepDelay);
      logStep('success', '✓', `Month filled: ${month}`);
    } else if (anyCardField) {
      logStep('warn', '⚠', 'Month field: not found');
    }

    if (expiryYearField) {
      logStep('step', '📅', `Year field found (${fieldDesc(expiryYearField)})`);
      await sleep(stepDelay);
      await fillYearField(expiryYearField, year, yearShort, stepDelay);
      logStep('success', '✓', `Year filled: ${year}`);
    } else if (anyCardField) {
      logStep('warn', '⚠', 'Year field: not found');
    }
  }

  // ── Step 5: CVV ───────────────────────────────────────────
  if (cvvField) {
    logStep('step', '🔒', `CVV field found (${fieldDesc(cvvField)})`);
    await sleep(stepDelay);
    await fillField(cvvField, cardData.cvv || '', stepDelay);
    logStep('success', '✓', `CVV filled: ${'•'.repeat(cardData.cvv?.length || 3)}`);
  } else if (anyCardField) {
    logStep('warn', '⚠', 'CVV field: not found');
  }

  // ── Step 6: Remaining address fields (State, City, Address, Postal) ───
  if (hasAddress) {
    await fillBillingAddressFields(address, stepDelay);
  }

  logStep('info', '✅', `Done — frame ${window.location.origin} finished`);
}

/**
 * Fill remaining billing address fields: address lines, city, state/province, postal.
 * Name is handled BEFORE card fields in fillPaymentForm for correct order.
 */
async function fillBillingAddressFields(address, delay) {
  logStep('step', '🏠', 'Filling billing address...');

  const addr1Field = findField([
    '#billingAddress-addressLine1Input',
    'input[name="addressLine1" i]',
    'input[name="address1" i]',
    'input[autocomplete="billing street-address"]',
    'input[placeholder*="address line 1" i]',
    'input[placeholder*="street" i]'
  ], ['address line 1', 'address 1', 'street address', 'address']);
  if (addr1Field && address.line1) {
    await sleep(delay);
    await fillField(addr1Field, address.line1, delay);
    logStep('success', '✓', `Address: ${address.line1}`);
  }

  const addr2Field = findField([
    '#billingAddress-addressLine2Input',
    'input[name="addressLine2" i]',
    'input[autocomplete="billing address-line2"]'
  ], ['address line 2', 'address 2', 'apt', 'suite', 'unit']);
  if (addr2Field && address.line2) {
    await sleep(delay);
    await fillField(addr2Field, address.line2, delay);
  }

  const cityField = findField([
    '#billingAddress-localityInput',
    'input[name="city" i]',
    'input[autocomplete="billing locality"]',
    '#city'
  ], ['city', 'town', 'locality']);
  if (cityField && address.city) {
    await sleep(delay);
    await fillField(cityField, address.city, delay);
    logStep('success', '✓', `City: ${address.city}`);
  }

  const stateField = findField([
    '#billingAddress-administrativeAreaInput',
    'select[name="administrativeArea" i]',
    'select[name="state" i]',
    'input[name="state" i]',
    'input[autocomplete="billing address-level1"]',
    '#state'
  ], ['state', 'province', 'region', 'do si']);
  if (stateField && address.state) {
    await sleep(delay);
    if (stateField.tagName === 'SELECT') {
      const opts = Array.from(stateField.options);
      const match = opts.find((opt) =>
        opt.value.toLowerCase() === address.state.toLowerCase() ||
        opt.textContent.toLowerCase().includes(address.state.toLowerCase())
      );
      if (match) {
        await fillField(stateField, match.value, delay);
        logStep('success', '✓', `State: ${address.state}`);
      }
    } else {
      await fillField(stateField, address.state, delay);
      logStep('success', '✓', `State: ${address.state}`);
    }
  }

  const postalField = findField([
    '#billingAddress-postalCodeInput',
    'input[name="postalCode" i]',
    'input[name="zip" i]',
    'input[autocomplete="billing postal-code"]',
    '#postal'
  ], ['postal code', 'zip code', 'zip', 'postal']);
  if (postalField && address.postal) {
    await sleep(delay);
    await fillField(postalField, address.postal, delay);
    logStep('success', '✓', `Postal: ${address.postal}`);
  }
}

async function discoverPaymentFields(delay = 100) {
  let fields = scanPaymentFields();
  if (hasRequiredPaymentFields(fields)) return fields;

  for (let attempt = 0; attempt < 2; attempt++) {
    await sleep(Math.max(delay, 220));
    fields = scanPaymentFields();
    if (hasRequiredPaymentFields(fields)) return fields;
  }

  return fields;
}

function hasRequiredPaymentFields(fields) {
  return Boolean(
    fields.cardNumberField &&
    (fields.expiryMonthField || fields.combinedExpiryField) &&
    (fields.expiryYearField || fields.combinedExpiryField) &&
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
    field.id || '',
    field.name || '',
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
      '#cardNumber',
      '#card_number',
      '#ccNumber',
      '#cc_number',
      '#cardnumber',
      '#card-number',
      '#credit-card-number'
    ], ['card number', 'credit card', 'pan', 'card no']),

    expiryMonthField: findField([
      'select[name*="expmonth" i]',
      'select[name*="exp_month" i]',
      'select[name*="card_month" i]',
      'select[name*="month" i]',
      'input[name*="expmonth" i]',
      'input[name*="exp_month" i]',
      'input[name*="cardmonth" i]',
      'input[name*="month" i]',
      'select[id*="expmonth" i]',
      'select[id*="exp_month" i]',
      'select[id*="month" i]',
      'input[placeholder*="mm" i][maxlength="2"]',
      'input[aria-label*="expiry month" i]',
      '#expiryMonth',
      '#expMonth',
      '#cardMonth',
      '#month'
    ], ['month', 'mm', 'exp month', 'expiry month']),

    expiryYearField: findField([
      'select[name*="expyear" i]',
      'select[name*="exp_year" i]',
      'select[name*="card_year" i]',
      'select[name*="year" i]',
      'input[name*="expyear" i]',
      'input[name*="exp_year" i]',
      'input[name*="cardyear" i]',
      'input[name*="year" i]',
      'select[id*="expyear" i]',
      'select[id*="exp_year" i]',
      'select[id*="year" i]',
      'input[aria-label*="expiry year" i]',
      '#expiryYear',
      '#expYear',
      '#cardYear',
      '#year'
    ], ['year', 'yy', 'exp year', 'expiry year']),

    combinedExpiryField: findField([
      'input[data-elements-stable-field-name="cardExpiry"]',
      '#payment-expiryInput',
      'input[id*="expiryInput" i]',
      'input[class*="CardExpiryInput" i]',
      'input[autocomplete="cc-exp"]',
      'input[name*="expiry" i]',
      'input[name*="expdate" i]',
      'input[name*="exp-date" i]',
      'input[name*="card_exp" i]',
      'input[placeholder*="mm/yy" i]',
      'input[placeholder*="mm / yy" i]',
      'input[placeholder*="mm/yyyy" i]',
      'input[placeholder*="expiry" i]',
      'input[placeholder*="expiration" i]',
      'input[id*="expiry" i]',
      'input[id*="expdate" i]',
      'input[aria-label*="expiration" i]',
      'input[aria-label*="expiry" i]',
      'input[data-testid*="expiry" i]',
      '#expiry',
      '#expiryDate',
      '#expDate',
      '#cardExpiry'
    ], ['expiry', 'expiration', 'mm / yy', 'mm/yy']),

    cvvField: findField([
      'input[data-elements-stable-field-name="cardCvc"]',
      '#payment-cvcInput',
      'input[id*="cvcInput" i]',
      'input[class*="CardCvcInput" i]',
      'input[autocomplete="cc-csc"]',
      'input[name*="cvv" i]',
      'input[name*="cvc" i]',
      'input[name*="cvv2" i]',
      'input[name*="csc" i]',
      'input[name*="security_code" i]',
      'input[name*="securitycode" i]',
      'input[placeholder*="cvv" i]',
      'input[placeholder*="cvc" i]',
      'input[placeholder*="security" i]',
      'input[id*="cvv" i]',
      'input[id*="cvc" i]',
      'input[id*="security" i]',
      'input[aria-label*="cvv" i]',
      'input[aria-label*="cvc" i]',
      'input[aria-label*="security code" i]',
      'input[data-testid*="cvv" i]',
      '#cvv',
      '#cvc',
      '#securityCode',
      '#securitycode',
      '#cardCvv'
    ], ['cvv', 'cvc', 'security code', 'cvv2'])
  };
}

function fieldDesc(el) {
  if (el.id) return `#${el.id}`;
  if (el.name) return `[name="${el.name}"]`;
  if (el.getAttribute('placeholder')) {
    return `[placeholder="${el.getAttribute('placeholder').slice(0, 20)}"]`;
  }
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
    if (parent.tagName === 'LABEL') {
      labels.push(parent.textContent || '');
      break;
    }
    parent = parent.parentElement;
  }

  return labels.join(' ');
}

function cssEscape(value) {
  if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
    return CSS.escape(value);
  }

  return String(value).replace(/["\\]/g, '\\$&');
}

function findField(selectors, labels = []) {
  const docs = collectSearchDocuments(document);

  for (const doc of docs) {
    const selectorMatch = findFieldBySelectors(doc, selectors);
    if (selectorMatch) return selectorMatch;
  }

  if (!labels.length) return null;

  for (const doc of docs) {
    const labelMatch = findFieldByLabels(doc, labels);
    if (labelMatch) return labelMatch;
  }

  return null;
}

function collectSearchDocuments(rootDoc, seen = new Set()) {
  if (!rootDoc || seen.has(rootDoc)) return [];

  seen.add(rootDoc);
  const docs = [rootDoc];

  for (const iframe of rootDoc.querySelectorAll('iframe')) {
    try {
      const frameDoc = iframe.contentDocument || iframe.contentWindow?.document;
      if (frameDoc) {
        docs.push(...collectSearchDocuments(frameDoc, seen));
      }
    } catch (_) { }
  }

  return docs;
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
      if (candidate && (isVisible(candidate) || isUsableField(candidate))) {
        return candidate;
      }
    }

    for (const input of allInputs) {
      const haystack = [
        input.getAttribute('placeholder') || '',
        input.getAttribute('aria-label') || '',
        input.getAttribute('autocomplete') || '',
        input.name || '',
        input.id || ''
      ].join(' ');

      if (regex.test(haystack) && (isVisible(input) || isUsableField(input))) {
        return input;
      }
    }
  }

  return null;
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

  return rect.width > 0 &&
    rect.height > 0 &&
    !el.disabled &&
    style.visibility !== 'hidden' &&
    style.display !== 'none' &&
    style.opacity !== '0';
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
    if (nativeSetter?.set) {
      nativeSetter.set.call(field, value);
    } else {
      field.value = value;
    }

    ['input', 'change', 'blur'].forEach((eventName) => {
      field.dispatchEvent(new Event(eventName, { bubbles: true }));
    });
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
    if (opt) {
      await fillField(field, opt.value, delay);
      return;
    }
  }

  await fillField(field, padded, delay);
}

async function fillYearField(field, fullYear, shortYear, delay = 220) {
  if (!fullYear && !shortYear) return;

  const fy = String(fullYear || '');
  const sy = String(shortYear || fy.slice(-2));

  if (field.tagName === 'SELECT') {
    const opt = findMatchingOption(field, [fy, sy, fy.slice(-2)]);
    if (opt) {
      await fillField(field, opt.value, delay);
      return;
    }
  }

  await fillField(field, fy || sy, delay);
}

async function clearTextField(field, nativeSetter) {
  setFieldValue(field, '', nativeSetter);
  field.dispatchEvent(new InputEvent('input', {
    bubbles: true,
    inputType: 'deleteContentBackward',
    data: null
  }));
  await sleep(40);
}

async function typeTextLikeHuman(field, value, nativeSetter, delay) {
  const perCharDelay = Math.max(35, Math.min(120, Math.round(delay / 4)));

  for (const char of value) {
    dispatchKeyboardEvent(field, 'keydown', char);
    dispatchKeyboardEvent(field, 'keypress', char);
    setFieldValue(field, `${field.value}${char}`, nativeSetter);
    field.dispatchEvent(new InputEvent('input', {
      bubbles: true,
      inputType: 'insertText',
      data: char
    }));
    dispatchKeyboardEvent(field, 'keyup', char);
    await sleep(perCharDelay);
  }
}

function setFieldValue(field, value, nativeSetter) {
  if (nativeSetter?.set) {
    nativeSetter.set.call(field, value);
  } else {
    field.value = value;
  }
}

function dispatchKeyboardEvent(field, type, key) {
  let code = 'Unidentified';
  if (/^\d$/.test(key)) {
    code = `Digit${key}`;
  } else if (/^[a-z]$/i.test(key)) {
    code = `Key${key.toUpperCase()}`;
  } else if (key === '/') {
    code = 'Slash';
  } else if (key === ' ') {
    code = 'Space';
  }

  field.dispatchEvent(new KeyboardEvent(type, {
    key,
    code,
    keyCode: key.charCodeAt(0),
    which: key.charCodeAt(0),
    bubbles: true
  }));
}

function findMatchingOption(select, candidates) {
  const normalized = candidates
    .filter(Boolean)
    .map((candidate) => candidate.toString().trim().toLowerCase());

  return Array.from(select.options).find((opt) => {
    const value = opt.value.toString().trim().toLowerCase();
    const label = opt.textContent.toString().trim().toLowerCase();

    return normalized.some((candidate) =>
      value === candidate ||
      label === candidate ||
      value.replace(/^0/, '') === candidate.replace(/^0/, '') ||
      label.replace(/^0/, '') === candidate.replace(/^0/, '')
    );
  }) || null;
}

function monthName(month) {
  const names = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  return names[parseInt(month, 10) - 1] || month;
}

function formatCardDisplay(number) {
  const clean = String(number).replace(/\D/g, '');
  const last4 = clean.slice(-4);
  return `•••• •••• •••• ${last4}`;
}

function formatExpiryForField(field, month, year, yearShort) {
  const fullYear = String(year || '');
  const short = String(yearShort || fullYear.slice(-2));
  const text = [
    field?.getAttribute('placeholder') || '',
    field?.getAttribute('aria-label') || '',
    field?.name || '',
    field?.id || '',
    getAssociatedLabelText(field)
  ].join(' ').toLowerCase();

  if (/yyyy/.test(text)) {
    return `${month}/${fullYear}`;
  }

  return `${month}/${short}`;
}
