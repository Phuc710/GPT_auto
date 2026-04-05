// Auto Fill GPT — Content Script v6 (Sequential: fillCard → fillBilling)
'use strict';

if (!window.__afLoaded) {
  window.__afLoaded = true;
  (() => {
    // ─── Logging ─────────────────────────────────────────────
    const log = (type, icon, msg) => {
      console.log(`[AutoFill] ${icon} ${msg}`);
      if (chrome.runtime?.id) chrome.runtime.sendMessage({ action: 'log_step', type, icon, msg }).catch(() => {});
    };
    const notify = (s) => {
      if (chrome.runtime?.id) chrome.runtime.sendMessage({ action: 'fill_status', status: s }).catch(() => {});
    };

    // ─── Message Router ──────────────────────────────────────
    chrome.runtime.onMessage.addListener((req, _s, sendResponse) => {
      const delay = Math.max(req.fillDelay || 100, 80);

      if (req.action === 'fillCard') {
        const fields = scanCardFields();
        if (hasCardFields(fields)) {
          notify('started');
          uncheckOptIns(delay)
            .then(() => fillCard(req.cardData, fields, delay))
            .then(() => notify('finished'))
            .catch(() => notify('finished'));
        }
        // Top frame acknowledges so popup knows scripts are loaded
        if (window === window.top) { sendResponse({ ok: true }); return false; }
      }

      if (req.action === 'fillBilling') {
        if (hasAddrData(req.address) && hasBillingNow()) {
          notify('started');
          fillBilling(req.address, delay)
            .then(() => notify('finished'))
            .catch(() => notify('finished'));
        }
        if (window === window.top) { sendResponse({ ok: true }); return false; }
      }

      if (req.action === 'trigger_subscribe_now' && window === window.top) {
        if (window.performSubscribe) window.performSubscribe().catch(() => {});
      }
    });

    async function fillCard(card, fields, delay) {
      const month = card.expiry?.month || card.month || '';
      const yearShort = card.expiry?.yearShort || String(card.expiry?.year || card.year || '').slice(-2);

      if (fields.number) { await typeInto(fields.number, card.number || '', delay); await sleep(delay); }
      if (fields.expiry) {
        await typeInto(fields.expiry, `${month}${yearShort}`, delay); // raw MMYY
        await sleep(delay);
      } else {
        if (fields.expiryMonth) { await typeInto(fields.expiryMonth, month, delay); await sleep(delay); }
        if (fields.expiryYear)  { await typeInto(fields.expiryYear, yearShort, delay); await sleep(delay); }
      }
      if (fields.cvv) { await typeInto(fields.cvv, card.cvv || '', delay); await sleep(delay); }

      log('info', '🔢', `BIN: ${String(card.number).replace(/\D/g, '')}`);
      log('info', '📅', `Expiry: ${month}/${yearShort}`);
      log('info', '🔒', `CVV: ${card.cvv || ''}`);
      await sleep(delay);
    }

    // ─── Fill Billing ────────────────────────────────────────
    async function fillBilling(addr, delay) {
      const FIELDS = [
        { key: 'name',   sels: ['#billingAddress-nameInput', '[autocomplete="billing name"]', '[name="name"]'] },
        { key: 'line1',  sels: ['#billingAddress-addressLine1Input', '[autocomplete="billing address-line1"]', '[name="addressLine1"]'] },
        { key: 'line2',  sels: ['#billingAddress-line2Input', '[autocomplete="billing address-line2"]', '[name="addressLine2"]'] },
        { key: 'city',   sels: ['#billingAddress-cityInput', '[autocomplete="billing address-level2"]', '[name="city"]'] },
        { key: 'state',  sels: ['select[autocomplete="billing address-level1"]', '#billingAddress-stateInput', 'select[name="state"]', '[name="state"]'] },
        { key: 'postal', sels: ['#billingAddress-postalCodeInput', '[autocomplete="billing postal-code"]', '[name="postalCode"]'] },
      ];
      let filled = 0;
      for (const f of FIELDS) {
        if (!addr[f.key]) continue;
        const el = await waitFor(f.sels, delay * 20, delay);
        if (el) { await typeInto(el, addr[f.key], delay); filled++; await sleep(delay); }
      }
      if (filled) log('info', '🏠', `Address: ${addr.name || ''} — ${addr.line1 || ''}, ${addr.city || ''}`);
    }

    // ─── Human Typing Engine ─────────────────────────────────
    async function typeInto(el, value, baseDelay = 100) {
      if (!el || value == null) return;
      const str = String(value);
      const d = (ms) => Math.max(5, Math.floor(ms * (baseDelay / 100)));

      // Focus with realistic click
      const r = el.getBoundingClientRect();
      const m = { bubbles: true, clientX: r.left + 4, clientY: r.top + 4 };
      el.dispatchEvent(new MouseEvent('mousedown', m));
      el.focus();
      el.dispatchEvent(new MouseEvent('mouseup', m));
      el.dispatchEvent(new MouseEvent('click', m));
      await sleep(d(rand(20, 50)));

      // SELECT dropdown
      if (el.tagName === 'SELECT') {
        const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value')?.set;
        setter ? setter.call(el, str) : (el.value = str);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(d(rand(25, 60)));
        return;
      }

      // Clear field
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
      try { el.setSelectionRange(0, 99999); } catch (_) {}
      try { document.execCommand('delete', false, null); } catch (_) {}
      if (setter) setter.call(el, ''); else el.value = '';
      el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward' }));
      await sleep(d(rand(40, 90)));

      // Type char by char
      for (const ch of str) {
        const k = { bubbles: true, key: ch, keyCode: ch.charCodeAt(0) };
        el.dispatchEvent(new KeyboardEvent('keydown', k));
        el.dispatchEvent(new KeyboardEvent('keypress', k));

        let ok = false;
        try { ok = document.execCommand('insertText', false, ch); } catch (_) {}
        if (!ok) {
          const v = el.value + ch;
          setter ? setter.call(el, v) : (el.value = v);
          el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: ch }));
        }
        el.dispatchEvent(new KeyboardEvent('keyup', k));
        
        let cDelay = d(rand(20, 50)); // Faster per-char delay
        if (Math.random() > 0.96) cDelay += d(rand(80, 120)); // Rarer, shorter pauses
        await sleep(cDelay);
      }
      el.dispatchEvent(new Event('change', { bubbles: true }));
      await sleep(d(rand(20, 50)));
      el.blur();
    }

    // ─── Field Scanning ──────────────────────────────────────
    function scanCardFields() {
      const q = (sels) => { for (const s of sels) { const e = document.querySelector(s); if (e && isVis(e)) return e; } return null; };
      return {
        number:      q(['input[data-elements-stable-field-name="cardNumber"]', '#payment-cardNumberInput', 'input[autocomplete="cc-number"]', 'input[id*="cardNumber" i]']),
        expiry:      q(['input[data-elements-stable-field-name="cardExpiry"]', '#payment-expiryInput', 'input[autocomplete="cc-exp"]', 'input[id*="expiry" i]']),
        expiryMonth: q(['input[name*="exp-month" i]', 'input[autocomplete="cc-exp-month"]']),
        expiryYear:  q(['input[name*="exp-year" i]', 'input[autocomplete="cc-exp-year"]']),
        cvv:         q(['input[data-elements-stable-field-name="cardCvc"]', '#payment-cvcInput', 'input[autocomplete="cc-csc"]', 'input[name*="cvv" i]', 'input[name*="cvc" i]']),
      };
    }

    function hasCardFields(f) { return !!(f.number || f.expiry || f.expiryMonth || f.expiryYear || f.cvv); }
    function hasAddrData(a) { return a && Object.entries(a).some(([k, v]) => v && !k.startsWith('_')); }
    function hasBillingNow() {
      return ['#billingAddress-nameInput', '#billingAddress-addressLine1Input', '[autocomplete="billing name"]', '[autocomplete="billing address-line1"]']
        .some(s => { const e = document.querySelector(s); return e && isVis(e); });
    }

    async function waitFor(sels, timeout, poll = 50) {
      const end = Date.now() + timeout;
      while (Date.now() < end) {
        for (const s of sels) { const e = document.querySelector(s); if (e && isVis(e)) return e; }
        await sleep(poll);
      }
      return null;
    }

    // ─── Helpers ─────────────────────────────────────────────
    function isVis(el) { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0' && el.offsetParent !== null; }
    function rand(a, b) { return Math.floor(Math.random() * (b - a + 1)) + a; }
    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    async function uncheckOptIns(delay = 50) {
      document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        const txt = (cb.closest('label')?.textContent || '').toLowerCase();
        if (/save|remember|faster|marketing|newsletter|business/i.test(txt) && cb.checked) {
          cb.click();
          log('info', '☐', 'Unchecked opt-in');
        }
      });
      await sleep(delay);
    }
  })();
}
