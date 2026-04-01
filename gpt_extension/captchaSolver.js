(function () {
  'use strict';

  // Prevent multiple injections
  if (window.__captchaSolverRunning) return;
  window.__captchaSolverRunning = true;

  class CaptchaSolver {
    constructor() {
      this.timer = null;
      this.isEnabled = false;
      this.config = {
        pollingInterval: 500,
        hcaptchaMatches: ['hcaptcha.com', 'newassets.hcaptcha.com', 'stripe.com', 'chatgpt.com', 'openai.com'],
        recaptchaMatches: ['google.com/recaptcha', 'stripe.com', 'chatgpt.com'],
        turnstileMatches: ['challenges.cloudflare.com', 'chatgpt.com']
      };
      this.init();
    }

    async init() {
      // Load current state
      const res = await this.getStorage(['standaloneCaptcha']);
      this.isEnabled = !!res.standaloneCaptcha;
      if (this.isEnabled) this.start();

      // Listen for toggle changes
      chrome.storage.onChanged.addListener((changes, area) => {
        if (area === 'local' && changes.standaloneCaptcha) {
          this.isEnabled = !!changes.standaloneCaptcha.newValue;
          if (this.isEnabled) this.start();
          else this.stop();
        }
      });
    }

    start() {
      if (this.timer) return;
      this.timer = setInterval(() => this.scan(), this.config.pollingInterval);
      console.log('[Captcha Service] Monitoring for challenges...');
    }

    stop() {
      if (this.timer) clearInterval(this.timer);
      this.timer = null;
    }

    scan() {
      if (!this.isEnabled) return;
      const url = window.location.href;

      // 1. hCaptcha logic - relaxed for generic matching
      const hCaptchaCheckbox = document.getElementById('checkbox')
        || document.querySelector('#anchor #checkbox')
        || document.querySelector('div[role="checkbox"]');

      if (hCaptchaCheckbox || this.isMatch(url, this.config.hcaptchaMatches)) {
        if (hCaptchaCheckbox && (hCaptchaCheckbox.getAttribute('aria-checked') === 'false' || !hCaptchaCheckbox.getAttribute('aria-checked'))) {
          const bodyText = document.body.innerText.toLowerCase();
          if (bodyText.includes('human') || bodyText.includes('người') || bodyText.includes('robot') || bodyText.includes('captcha')) {
            if (!window.__captchaLogged) {
              this.log('success', '🧬', 'hCaptcha detected — solving...');
              window.__captchaLogged = true;
              setTimeout(() => { window.__captchaLogged = false; }, 10000);
            }
            this.performHumanClick(hCaptchaCheckbox);
            return;
          }
        }
      }

      // 2. ReCaptcha
      const reCaptchaAnchor = document.querySelector('#recaptcha-anchor') || document.querySelector('.recaptcha-checkbox');
      if (reCaptchaAnchor || this.isMatch(url, this.config.recaptchaMatches)) {
        if (reCaptchaAnchor && reCaptchaAnchor.getAttribute('aria-checked') === 'false') {
          if (!window.__captchaLogged) {
            this.log('success', '🧿', 'reCaptcha detected — solving...');
            window.__captchaLogged = true;
            setTimeout(() => { window.__captchaLogged = false; }, 10000);
          }
          this.performHumanClick(reCaptchaAnchor);
          return;
        }
      }

      // Turnstile logic removed as requested
    }

    isMatch(url, patterns) {
      return patterns.some(p => url.includes(p));
    }

    performHumanClick(el) {
      if (!el) return;
      ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(type => {
        el.dispatchEvent(new MouseEvent(type, { view: window, bubbles: true, cancelable: true, buttons: 1 }));
      });
    }

    getStorage(keys) {
      return new Promise(resolve => chrome.storage.local.get(keys, resolve));
    }

    log(type, icon, msg) {
      console.log(`[Captcha Service] ${icon} ${msg}`);
      if (chrome.runtime?.id) {
        try {
          chrome.runtime.sendMessage({ action: 'log_step', type, icon, msg: `[Captcha] ${msg}` }).catch(() => { });
        } catch (e) { }
      }
    }
  }

  // Self-start
  new CaptchaSolver();
})();

