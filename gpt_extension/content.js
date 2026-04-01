// Content script for Auto Fill GPT extension (v4)
// Runs in ALL frames. Each frame fills ONLY its own fields.
// Top frame: billing address. Stripe iframe: card fields.

'use strict';

if (window.__afLoaded) {
  console.log('[AutoFill] Content script already active. Skipping duplicate listener.');
} else {
  (function() {
    window.__afLoaded = true;

    const fillLog = [];

    function logStep(type, icon, msg) {
      fillLog.push({ type, icon, msg });
      console.log(`[AutoFill] ${icon} ${msg}`);

      // Broadcast log to popup for real-time visibility
      if (chrome.runtime?.id) {
        try {
          chrome.runtime.sendMessage({
            action: 'log_step',
            type,
            icon,
            msg
          }).catch(() => { });
        } catch (e) {
          // Context invalidated, ignore silently
        }
      }
    }

    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action !== 'fillForm') return undefined;

      const isTop = (window === window.top);
      const delay = request.fillDelay || 100;

      if (!isTop) {
        // ── SUB-FRAME (Stripe, etc.): fill card + address fields ──
        fillCardFieldsInFrame(request.cardData, request.address || {}, delay).catch(() => { });
        return false;
      }

      // ── TOP FRAME: fill address + respond to popup ──
      fillLog.length = 0;
      const address = request.address || {};

      fillTopFrame(request.cardData, delay, address)
        .then(() => {
          sendResponse({ success: true, log: [...fillLog] });
          // Note: performSubscribe is now triggered by 'all_fills_complete' message from background
        })
        .catch((err) => {
          logStep('error', '✗', `Fatal: ${err.message}`);
          sendResponse({ success: false, error: err.message, log: [...fillLog] });
        });

      return true; // keep channel open for async sendResponse
    });

    // Listen for the "All frames done" signal from background
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.action === 'all_fills_complete' && window === window.top) {
        logStep('success', '✓', 'Form filled successfully!');
        if (window.performSubscribe) {
          setTimeout(() => window.performSubscribe(), 300);
        }
      }
    });

    /**
     * Cross-frame coordination helper
     */
    async function notifyFillStatus(status) {
      if (chrome.runtime?.id) {
        try {
          return new Promise(resolve => {
            chrome.runtime.sendMessage({ action: 'fill_status', status }, resolve);
          });
        } catch (e) { }
      }
    }

    // ═════════════════════════════════════════════════════════════
    // TOP FRAME: fills billing address fields in its own document
    // ═════════════════════════════════════════════════════════════
    async function fillTopFrame(cardData, delay, address) {
      const stepDelay = Math.max(delay, 80);

      // Report start if we are filling address or card fields
      const addrValues = Object.entries(address || {}).filter(([k]) => !k.startsWith('_')).map(([, v]) => v);
      const hasAddress = addrValues.some(v => v && v !== false);
      const fields = scanPaymentFields();
      const hasCard = anyPaymentFieldPresent(fields);

      if (hasAddress || hasCard) await notifyFillStatus('started');

      try {
        await uncheckAnnoyingBoxes(stepDelay);
        if (hasCard) await fillCardFields(cardData, fields, stepDelay);
        if (hasAddress) await fillBillingAddress(address, stepDelay);
      } finally {
        if (hasAddress || hasCard) await notifyFillStatus('finished');
      }
    }

    // ═════════════════════════════════════════════════════════════
    // SUB-FRAME: fills card + billing address in its own document
    // ═════════════════════════════════════════════════════════════
    async function fillCardFieldsInFrame(cardData, address, delay) {
      const stepDelay = Math.max(delay, 80);

      const addrValues = Object.entries(address || {}).filter(([k]) => !k.startsWith('_')).map(([, v]) => v);
      const hasAddress = addrValues.some(v => v && v !== false);

      let fields = scanPaymentFields();
      let hasCard = anyPaymentFieldPresent(fields);

      if (!hasCard && hasAddress) {
         // Check once more in subframe addressing
         const nameField = await waitForField(['#billingAddress-nameInput', '[name="name"]'], null, 100);
         if (nameField) hasCard = false; // Just to proceed with address
      } else if (!hasCard) {
         // Scan once more with slight delay to catch Stripe's delayed iframe loading
         await sleep(stepDelay);
         fields = scanPaymentFields();
         hasCard = anyPaymentFieldPresent(fields);
         if (!hasCard && !hasAddress) return; 
      }

      await notifyFillStatus('started');

      try {
        await uncheckAnnoyingBoxes(stepDelay);
        if (anyPaymentFieldPresent(fields)) {
          await fillCardFields(cardData, fields, stepDelay);
          if (hasAddress) await fillBillingAddress(address, stepDelay);
          logStep('info', '✅', `Card frame filled — ${window.location.origin}`);
        } else if (hasAddress) {
          await fillBillingAddress(address, stepDelay);
          logStep('info', '✅', `Address frame filled — ${window.location.origin}`);
        }
      } finally {
        await notifyFillStatus('finished');
      }
    }

    function anyPaymentFieldPresent(f) {
      return !!(f.cardNumberField || f.combinedExpiryField || f.expiryMonthField || f.expiryYearField || f.cvvField);
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
    // BILLING ADDRESS
    // ═════════════════════════════════════════════════════════════
    async function fillBillingAddress(address, delay) {
      const fields = [
        { key: 'name', selectors: ['#billingAddress-nameInput', '[name="name"]', '[autocomplete="billing name"]'], labels: ['full name', 'name'] },
        { key: 'state', selectors: ['#billingAddress-stateInput', '[name="state"]', 'select[name="state"]', '[autocomplete="billing address-level1"]'], labels: ['state', 'province', 'region'] },
        { key: 'city', selectors: ['#billingAddress-cityInput', '[name="city"]', '[autocomplete="billing address-level2"]'], labels: ['city', 'town'] },
        { key: 'line1', selectors: ['#billingAddress-line1Input', '[name="address1"]', '[name="line1"]', '[autocomplete="billing address-line1"]'], labels: ['address line 1', 'street address'] },
        { key: 'line2', selectors: ['#billingAddress-line2Input', '[name="address2"]', '[name="line2"]', '[autocomplete="billing address-line2"]'], labels: ['address line 2', 'apartment', 'suite'] },
        { key: 'postal', selectors: ['#billingAddress-postalCodeInput', '[name="postalCode"]', '[autocomplete="billing postal-code"]', '#postal', '#zip'], labels: ['postal code', 'zip code', 'zip', 'postal'] }
      ];

      for (const f of fields) {
        if (!address[f.key]) continue;
        const el = await waitForField(f.selectors, f.labels, 50);
        if (el) {
          await fillField(el, address[f.key], delay);
          const icon = f.key === 'name' ? '👤' : (f.key === 'postal' ? '📮' : '🗺');
          logStep('success', icon, `${f.key.charAt(0).toUpperCase() + f.key.slice(1)}: ${address[f.key]}`);
        }
      }
    }

    async function uncheckAnnoyingBoxes(delay) {
      const selectors = [
        '#payment-linkOptInInput', 'input[name="linkOptIn"]',
        '#business', 'input[name="business"]', 'input[name="isBusiness"]', 'input[name*="business" i]'
      ];
      for (const selector of selectors) {
        const els = document.querySelectorAll(selector);
        for (const el of els) {
          if (el.checked || el.getAttribute('aria-checked') === 'true' || el.getAttribute('data-testing-state-value') === 'true') {
            try { el.click(); } catch(e){}
            await sleep(50);
          }
        }
      }
      const labels = Array.from(document.querySelectorAll('label'));
      for (const lbl of labels) {
        const text = (lbl.textContent || '').toLowerCase();
        if (text.includes('faster checkout') || text.includes('purchasing as a business')) {
          const inputId = lbl.getAttribute('for');
          let input = document.getElementById(inputId);
          if (!input) input = lbl.querySelector('input[type="checkbox"]');
          if (input && (input.checked || input.getAttribute('aria-checked') === 'true')) {
            try { input.click(); } catch(e){}
          }
        }
      }
    }

    // ═════════════════════════════════════════════════════════════
    // FIELD SCANNING
    // ═════════════════════════════════════════════════════════════
    function scanPaymentFields() {
      const findField = (selectors, labels) => {
        for (const s of selectors) {
          const el = document.querySelector(s);
          if (el && isVisible(el)) return el;
        }
        const inputs = document.querySelectorAll('input, select');
        for (const input of inputs) {
          if (!isVisible(input)) continue;
          const labelText = getLabelText(input).toLowerCase();
          if (labels.some(l => labelText.includes(l))) return input;
          const ph = (input.placeholder || '').toLowerCase();
          if (labels.some(l => ph.includes(l))) return input;
        }
        return null;
      };

      return {
        cardNumberField: findField([
          'input[data-elements-stable-field-name="cardNumber"]',
          '#payment-cardNumberInput',
          'input[id*="cardNumberInput" i]',
          'input[class*="CardNumberInput" i]',
          'input[autocomplete="cc-number"]',
          'input[name*="cardnumber" i]', 'input[name*="number" i]'
        ], ['card number', 'pan', 'số thẻ']),

        combinedExpiryField: findField([
          'input[data-elements-stable-field-name="cardExpiry"]',
          '#payment-expiryInput',
          'input[id*="expiryInput" i]',
          'input[class*="CardExpiryInput" i]',
          'input[autocomplete="cc-exp"]'
        ], ['exp', 'expiry', 'valid thru', 'thời hạn']),

        expiryMonthField: findField([
          'input[name*="exp-month" i]', 'select[name*="exp-month" i]',
          'input[autocomplete="cc-exp-month"]'
        ], ['month', 'tháng']),

        expiryYearField: findField([
          'input[name*="exp-year" i]', 'select[name*="exp-year" i]',
          'input[autocomplete="cc-exp-year"]'
        ], ['year', 'năm']),

        cvvField: findField([
          'input[data-elements-stable-field-name="cardCvc"]',
          '#payment-cvcInput',
          'input[id*="cvcInput" i]',
          'input[class*="CardCvcInput" i]',
          'input[autocomplete="cc-csc"]',
          'input[name*="cvv" i]', 'input[name*="cvc" i]'
        ], ['cvv', 'cvc', 'security code', 'mã bảo mật'])
      };
    }

    function hasAnyPaymentField(f) {
      return !!(f.cardNumberField || f.combinedExpiryField || f.expiryMonthField || f.expiryYearField || f.cvvField);
    }

    // ── Helpers ──
    async function fillField(el, value, delay) {
      if (!el || !value) return;
      
      // 1. Mô phỏng di chuột và Focus như người thật
      const rect = el.getBoundingClientRect();
      const mouseData = { bubbles: true, cancelable: true, view: window, clientX: rect.left + 5, clientY: rect.top + 5 };
      el.dispatchEvent(new MouseEvent('mousedown', mouseData));
      el.focus();
      el.dispatchEvent(new MouseEvent('mouseup', mouseData));
      el.dispatchEvent(new MouseEvent('click', mouseData));

      // Nghỉ một chút trước khi gõ (như đang chuẩn bị tay)
      await sleep(Math.floor(Math.random() * 80) + 100);

      if (el.tagName === 'SELECT') {
        el.value = value;
        el.dispatchEvent(new Event('change', { bubbles: true }));
      } else {
        // Xóa trắng ô input trước khi gõ
        el.value = '';
        el.dispatchEvent(new Event('input', { bubbles: true }));

        const strValue = String(value);
        for (let i = 0; i < strValue.length; i++) {
          const char = strValue[i];
          const keyCode = char.charCodeAt(0);
          
          // Gửi KeyDown và KeyPress (rất quan trọng cho Stripe/ChatGPT)
          el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: char, keyCode }));
          el.dispatchEvent(new KeyboardEvent('keypress', { bubbles: true, key: char, keyCode }));
          
          // Sử dụng execCommand để "nhét" chữ vào buffer (đây là cách chân thực nhất)
          let success = false;
          try {
            success = document.execCommand('insertText', false, char);
          } catch (e) { success = false; }

          if (!success) {
            // Fallback nếu trình duyệt chặn execCommand
            el.value += char;
            el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: char }));
          }
          
          // Gửi KeyUp
          el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: char, keyCode }));

          // ── TỐC ĐỘ GÕ "TẦM TRUNG - NHANH" (40-75ms mỗi phím) ──
          let charDelay = Math.floor(Math.random() * 35) + 40; 
          
          // Thỉnh thoảng khựng lại một chút (như người thật đang đổi ngón tay)
          if (Math.random() > 0.92) charDelay += 120;
          if (char === ' ') charDelay += 50; // Phím cách thường gõ chậm hơn xíu

          await sleep(charDelay);
        }
      }
      
      // Hoàn tất: trigger change và thoát focus
      el.dispatchEvent(new Event('change', { bubbles: true }));
      await sleep(Math.floor(Math.random() * 100) + 50);
      el.blur();
      await sleep(delay);
    }

    function formatExpiryForField(el, month, year, yearShort) {
      const ph = (el.placeholder || '').toLowerCase();
      if (ph.includes('yy') && !ph.includes('yyyy')) return `${month}${yearShort}`;
      if (ph.includes('/') || ph.includes(' / ')) return `${month} / ${yearShort}`;
      return `${month}${yearShort}`;
    }

    async function waitForField(selectors, labels, timeout = 1000) {
      const start = Date.now();
      while (Date.now() - start < timeout) {
        for (const s of selectors) {
          const el = document.querySelector(s);
          if (el && isVisible(el)) return el;
        }
        const inputs = document.querySelectorAll('input, select');
        for (const input of inputs) {
          if (!isVisible(input)) continue;
          const labelText = getLabelText(input).toLowerCase();
          if (labels.some(l => labelText.includes(l))) return input;
        }
        await sleep(100);
      }
      return null;
    }

    function isVisible(el) {
      const style = window.getComputedStyle(el);
      return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && el.offsetParent !== null;
    }

    function getLabelText(input) {
      const id = input.id;
      if (id) {
        const label = document.querySelector(`label[for="${id}"]`);
        if (label) return label.textContent;
      }
      let parent = input.parentElement;
      while (parent) {
        if (parent.tagName === 'LABEL') return parent.textContent;
        parent = parent.parentElement;
      }
      return '';
    }

    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
  })();
}
