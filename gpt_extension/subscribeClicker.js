/**
 * Subscribe Clicker — Auto-clicks the payment submit / subscribe button
 * after form fill completes. Works on ChatGPT + Stripe Checkout.
 */
'use strict';

if (window.__subscribeClickerLoaded) {
  // Already loaded in this frame — skip
} else {
  (() => {
    window.__subscribeClickerLoaded = true;

    // ── Config ──────────────────────────────────────────────────────
    const MAX_ATTEMPTS   = 18;
    const ATTEMPT_DELAY  = 300; // ms between retries

    // Subscribe-like button text/aria patterns
    const SUBSCRIBE_TEXT = ['subscribe', 'sign up', 'confirm payment', 'checkout'];
    const SUBSCRIBE_STARTS = ['pay ', 'start ', 'try '];

    // ── Expose globally ─────────────────────────────────────────────
    window.performSubscribe       = performSubscribe;
    window.triggerSubscribeImmediate = () => performSubscribe();

    // ── Listeners ────────────────────────────────────────────────────
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.action === 'all_fills_complete' && window === window.top) {
        setTimeout(() => performSubscribe().catch(() => {}), 400);
      }
      if (msg.action === 'trigger_subscribe_now' && window === window.top) {
        setTimeout(() => performSubscribe().catch(() => {}), 300);
      }
    });

    // ── Main function ────────────────────────────────────────────────
    async function performSubscribe() {
      if (window.__isSubscribing) return false;
      window.__isSubscribing = true;

      try {
        for (let i = 0; i < MAX_ATTEMPTS; i++) {
          const btn = findSubscribeButton();

          if (btn) {
            await highlightAndClick(btn);
            broadcastLog('success', '✅', '[Clicker] Subscribe button clicked!');
            return true;
          }

          await sleep(ATTEMPT_DELAY);
        }

        broadcastLog('error', '❌', '[Clicker] Subscribe button not found');
        return false;
      } finally {
        window.__isSubscribing = false;
      }
    }

    // ── Button detection ─────────────────────────────────────────────
    function findSubscribeButton() {
      const candidates = [
        ...document.querySelectorAll('button[aria-label="Subscribe"]'),
        ...document.querySelectorAll('button[type="submit"]'),
        ...document.querySelectorAll('[data-testid*="submit" i]'),
        ...document.querySelectorAll('[data-testid*="payment-submit" i]'),
        ...document.querySelectorAll('button[aria-label*="subscribe" i]')
      ];

      for (const btn of candidates) {
        if (!isSubscribeCandidate(btn)) continue;
        if (!isClickable(btn))         continue;
        return btn;
      }
      return null;
    }

    function isSubscribeCandidate(btn) {
      const text  = (btn.textContent || '').trim().toLowerCase();
      const aria  = (btn.getAttribute('aria-label') || '').toLowerCase();
      const combined = text + ' ' + aria;

      return (
        SUBSCRIBE_TEXT.some(t => combined.includes(t)) ||
        SUBSCRIBE_STARTS.some(t => combined.startsWith(t)) ||
        // ChatGPT-specific pattern
        (btn.classList.contains('btn-primary') && aria.includes('subscribe'))
      );
    }

    function isClickable(btn) {
      const style = window.getComputedStyle(btn);
      const rect  = btn.getBoundingClientRect();
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
      if (rect.width < 40 || rect.height < 16) return false;
      if (btn.disabled || btn.getAttribute('aria-disabled') === 'true') return false;
      return true;
    }

    // ── Click simulation ─────────────────────────────────────────────
    async function highlightAndClick(btn) {
      // Brief visual flash
      const prevOutline = btn.style.outline;
      btn.style.outline = '2px solid #10a37f';
      btn.style.boxShadow = '0 0 10px #10a37f80';
      await sleep(rand(150, 350));
      btn.style.outline   = prevOutline;
      btn.style.boxShadow = '';

      // Human click sequence
      const rect = btn.getBoundingClientRect();
      const cx   = rect.left + rect.width  / 2;
      const cy   = rect.top  + rect.height / 2;
      const mOpts = { bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy };

      btn.dispatchEvent(new MouseEvent('mouseover',  mOpts));
      btn.focus();
      await sleep(rand(40, 80));

      btn.dispatchEvent(new PointerEvent('pointerdown', mOpts));
      btn.dispatchEvent(new MouseEvent('mousedown',   mOpts));
      await sleep(rand(90, 160));

      btn.dispatchEvent(new PointerEvent('pointerup', mOpts));
      btn.dispatchEvent(new MouseEvent('mouseup',     mOpts));
      btn.dispatchEvent(new MouseEvent('click',       mOpts));

      // Backup native click
      await sleep(25);
      try { btn.click(); } catch (_) {}
    }

    // ── Helpers ──────────────────────────────────────────────────────
    function broadcastLog(type, icon, msg) {
      console.log(`[Clicker] ${icon} ${msg}`);
      if (chrome.runtime?.id) {
        chrome.runtime.sendMessage({ action: 'log_step', type, icon, msg }).catch(() => {});
      }
    }

    function rand(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
    function sleep(ms)      { return new Promise(r => setTimeout(r, ms)); }
  })();
}
