// Content script for Auto Fill GPT extension

const fillLog = [];

function logStep(type, icon, msg) {
  fillLog.push({ type, icon, msg });
  console.log(`[AutoFill] ${icon} ${msg}`);
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'fillForm') {
    fillLog.length = 0;
    const delay = request.fillDelay || 100;

    fillPaymentForm(request.cardData, delay)
      .then(() => {
        sendResponse({ success: true, log: [...fillLog] });
      })
      .catch((error) => {
        logStep('error', '✗', `Fatal: ${error.message}`);
        sendResponse({ success: false, error: error.message, log: [...fillLog] });
      });
    return true;
  }
});

/**
 * Main fill function
 */
async function fillPaymentForm(cardData, delay = 100) {
  logStep('info', '🔍', 'Scanning page for form fields...');

  const cardNumberField = findField([
    'input[name*="cardnumber" i]',
    'input[name*="card_number" i]',
    'input[name*="ccnumber" i]',
    'input[name*="cc_number" i]',
    'input[name*="number" i][type="text"]',
    'input[placeholder*="card number" i]',
    'input[placeholder*="credit card" i]',
    'input[id*="cardnumber" i]',
    'input[id*="card_number" i]',
    'input[id*="ccnumber" i]',
    '#cardNumber', '#card_number', '#ccNumber', '#cc_number'
  ]);

  const expiryMonthField = findField([
    'select[name*="expmonth" i]', 'select[name*="exp_month" i]', 'select[name*="month" i]',
    'input[name*="expmonth" i]', 'input[name*="exp_month" i]', 'input[name*="month" i]',
    'select[id*="expmonth" i]', 'select[id*="exp_month" i]', 'select[id*="month" i]',
    '#expiryMonth', '#expMonth', '#month'
  ]);

  const expiryYearField = findField([
    'select[name*="expyear" i]', 'select[name*="exp_year" i]', 'select[name*="year" i]',
    'input[name*="expyear" i]', 'input[name*="exp_year" i]', 'input[name*="year" i]',
    'select[id*="expyear" i]', 'select[id*="exp_year" i]', 'select[id*="year" i]',
    '#expiryYear', '#expYear', '#year'
  ]);

  // Also look for combined expiry field (e.g. "MM/YY")
  const combinedExpiryField = findField([
    'input[name*="expiry" i]', 'input[name*="expdate" i]', 'input[name*="exp" i]',
    'input[placeholder*="mm/yy" i]', 'input[placeholder*="mm / yy" i]',
    'input[placeholder*="expiry" i]', 'input[id*="expiry" i]',
    '#expiry', '#expiryDate'
  ]);

  const cvvField = findField([
    'input[name*="cvv" i]', 'input[name*="cvc" i]',
    'input[name*="security" i]', 'input[name*="code" i]',
    'input[placeholder*="cvv" i]', 'input[placeholder*="cvc" i]',
    'input[placeholder*="security" i]',
    'input[id*="cvv" i]', 'input[id*="cvc" i]', 'input[id*="security" i]',
    '#cvv', '#cvc', '#securityCode'
  ]);

  // ── Card Number ─────────────────────────────────────────
  if (cardNumberField) {
    logStep('step', '💳', `Card number field: found (${fieldDesc(cardNumberField)})`);
    await sleep(delay);
    fillField(cardNumberField, cardData.number);
    logStep('success', '✓', `Filled: ${CardGenerator.formatCardNumber(cardData.number)}`);
  } else {
    logStep('warn', '⚠', 'Card number field: not found');
  }

  // ── Expiry ──────────────────────────────────────────────
  const month = cardData.expiry?.month || cardData.month;
  const year = cardData.expiry?.year || cardData.year;
  const yearShort = cardData.expiry?.yearShort || String(year).slice(-2);

  if (combinedExpiryField && !expiryMonthField) {
    logStep('step', '📅', `Combined expiry field: found (${fieldDesc(combinedExpiryField)})`);
    await sleep(delay);
    fillField(combinedExpiryField, `${month}/${yearShort}`);
    logStep('success', '✓', `Filled expiry: ${month}/${yearShort}`);
  } else {
    if (expiryMonthField) {
      logStep('step', '📅', `Month field: found (${fieldDesc(expiryMonthField)})`);
      await sleep(delay);
      fillMonthField(expiryMonthField, month);
      logStep('success', '✓', `Filled month: ${month}`);
    } else {
      logStep('warn', '⚠', 'Month field: not found');
    }

    if (expiryYearField) {
      logStep('step', '📅', `Year field: found (${fieldDesc(expiryYearField)})`);
      await sleep(delay);
      fillYearField(expiryYearField, year, yearShort);
      logStep('success', '✓', `Filled year: ${year}`);
    } else {
      logStep('warn', '⚠', 'Year field: not found');
    }
  }

  // ── CVV ─────────────────────────────────────────────────
  if (cvvField) {
    logStep('step', '🔒', `CVV field: found (${fieldDesc(cvvField)})`);
    await sleep(delay);
    fillField(cvvField, cardData.cvv || '');
    logStep('success', '✓', `Filled CVV: ${cardData.cvv}`);
  } else {
    logStep('warn', '⚠', 'CVV field: not found');
  }

  const filledCount = [cardNumberField, expiryMonthField || combinedExpiryField, cvvField]
    .filter(Boolean).length;

  if (filledCount === 0) {
    throw new Error('No payment fields found on this page.');
  }
}

// ── Field utilities ───────────────────────────────────────────

function fieldDesc(el) {
  return el.id ? `#${el.id}` : el.name ? `[name="${el.name}"]` : el.tagName.toLowerCase();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function findField(selectors) {
  for (const selector of selectors) {
    try {
      const el = document.querySelector(selector);
      if (el && isVisible(el)) return el;
    } catch { }
  }
  return null;
}

function isVisible(el) {
  return el.offsetWidth > 0 && el.offsetHeight > 0 &&
    window.getComputedStyle(el).visibility !== 'hidden';
}

function fillField(field, value) {
  field.focus();
  field.value = '';

  // Native input setter (for React/Vue controlled inputs)
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  );
  if (nativeInputValueSetter && field.tagName === 'INPUT') {
    nativeInputValueSetter.set.call(field, value);
  } else {
    field.value = value;
  }

  field.dispatchEvent(new Event('input', { bubbles: true }));
  field.dispatchEvent(new Event('change', { bubbles: true }));
  field.dispatchEvent(new Event('blur', { bubbles: true }));

  if (field.tagName === 'SELECT') {
    field.dispatchEvent(new Event('change', { bubbles: true }));
  }
}

function fillMonthField(field, month) {
  if (!month) return;
  const padded = String(month).padStart(2, '0');
  const numeric = String(parseInt(padded, 10));

  if (field.tagName === 'SELECT') {
    const opt = findMatchingOption(field, [padded, numeric, monthName(padded), monthName(padded).slice(0, 3)]);
    if (opt) { fillField(field, opt.value); return; }
  }
  fillField(field, padded);
}

function fillYearField(field, fullYear, shortYear) {
  if (!fullYear && !shortYear) return;
  const fy = String(fullYear || '');
  const sy = String(shortYear || fy.slice(-2));

  if (field.tagName === 'SELECT') {
    const opt = findMatchingOption(field, [fy, sy, fy.slice(-2)]);
    if (opt) { fillField(field, opt.value); return; }
  }
  fillField(field, fy || sy);
}

function findMatchingOption(select, candidates) {
  const norm = candidates.filter(Boolean).map(c => c.toString().trim().toLowerCase());
  return Array.from(select.options).find(opt => {
    const v = opt.value.toString().trim().toLowerCase();
    const l = opt.textContent.toString().trim().toLowerCase();
    return norm.some(c =>
      v === c || l === c ||
      v.replace(/^0/, '') === c.replace(/^0/, '') ||
      l.replace(/^0/, '') === c.replace(/^0/, '')
    );
  }) || null;
}

function monthName(month) {
  const names = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];
  return names[parseInt(month, 10) - 1] || month;
}
