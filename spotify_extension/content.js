// Content script - Spotify Auto-Checkout Extension
// Runs in ALL frames on payments.spotify.com and pci.spotify.com
'use strict';

if (typeof self.SPOTIFY_CONTENT_LOADED === 'undefined') {
    self.SPOTIFY_CONTENT_LOADED = true;

    const IS_PCI_FRAME = typeof window !== 'undefined' && window.location.hostname === 'pci.spotify.com';
    const IS_TOP = typeof window !== 'undefined' && (window === window.top);

    // ── LOGGING ──
    function log(type, icon, msg) {
        console.log(`[SpotifyFill] ${icon} ${msg}`);
        try {
            chrome.runtime.sendMessage({ action: 'pushLog', logType: type, icon, msg });
        } catch (e) {
            // Extension context invalidated - silenty fail
        }
    }

    // ── STATE MACHINE ──
    let fillDelay = 300;

    // ─────────────────────────────────────────────────────────
    // TOP FRAME: listens for fillAndSubmit, triggers PCI fill,
    //            watches for error/success banner, reports back
    // ─────────────────────────────────────────────────────────
    if (IS_TOP) {
        let checkInterval = null;
        let currentCard = null;
        let loopDelay = 2000;
        let isRunning = false;
        let executionId = 0;

        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            if (request.action === 'fillAndSubmit') {
                executionId++;
                isRunning = true;
                const myId = executionId;

                currentCard = request.cardData;
                fillDelay = request.fillDelay || 300;
                loopDelay = request.loopDelay || 2000;

                startFillCycle(request.cardData, myId);
                sendResponse({ ack: true });
                return false;
            }

            if (request.action === 'stopExecution') {
                isRunning = false;
                executionId++;
                stopWatcher();
                log('info', '⏹', 'Runner stopped by user');
                sendResponse({ ack: true });
                return false;
            }

            if (request.action === 'pciReady') {
                sendResponse({ ack: true });
                return false;
            }
        });

        async function startFillCycle(card, myId) {
            stopWatcher();
            if (!isRunning || myId !== executionId) return;

            log('info', '⏳', 'Preparing fill cycle...');

            await selectCardPaymentOption();
            if (!isRunning || myId !== executionId) return;

            await sleep(600);
            if (!isRunning || myId !== executionId) return;

            await fillTopAddressFields(card);
            if (!isRunning || myId !== executionId) return;

            // Tell PCI iframe to fill its fields
            broadcastToPCIFrame({ action: 'fillCard', cardData: card, fillDelay, executionId: myId });

            // After filling, wait for form to be ready then submit
            await sleep(fillDelay * 10 + 2000);
            if (!isRunning || myId !== executionId) return;

            await clickSubmit(myId);
            if (!isRunning || myId !== executionId) return;

            // Now watch for result
            startWatcher(myId);
        }

        async function selectCardPaymentOption() {
            // Check for modern radio button layout (#option-cards)
            const radioBtn = document.getElementById('option-cards');
            if (radioBtn) {
                if (!radioBtn.checked) {
                    // Click the label associated with the radio button
                    const label = document.querySelector(`label[for="option-cards"]`);
                    if (label) {
                        label.click();
                        await sleep(800);
                    }
                }
                return;
            }

            // Fallback for older layout (a[data-value="cards"])
            const cardOpt = document.querySelector('a[data-value="cards"]');
            if (cardOpt) {
                // Check if already selected (has active class or aria-checked)
                const li = cardOpt.closest('li');
                const pciFrame = li?.querySelector('iframe[data-testid="pci-frame"]');
                if (!pciFrame) {
                    // Not expanded yet — click to open
                    cardOpt.click();
                    await sleep(800);
                }
            }
        }

        async function fillTopAddressFields(card) {
            // Spotify checkout top frame may have name & address fields outside PCI
            // Currently Spotify US only shows card in PCI; nothing to fill on top
        }

        function broadcastToPCIFrame(payload) {
            const iframes = document.querySelectorAll('iframe[data-testid="pci-frame"]');
            iframes.forEach(iframe => {
                // Use postMessage for cross-origin to PCI iframe
                iframe.contentWindow?.postMessage(
                    JSON.stringify({ __spotifyAutoFill__: true, ...payload }),
                    'https://pci.spotify.com'
                );
            });
        }

        // Watch DOM for success/failure banners
        function startWatcher(myId) {
            let waited = 0;
            const maxWait = 25000;

            if (checkInterval) clearInterval(checkInterval);
            checkInterval = setInterval(() => {
                if (!isRunning || myId !== executionId) {
                    stopWatcher();
                    return;
                }

                waited += 500;

                // Check error banner
                const errorEl = findErrorBanner();
                if (errorEl) {
                    const errText = errorEl.textContent?.trim() || '';
                    if (/payment method was already used|already used for an offer or trial/i.test(errText)) {
                        log('dead', '🚫', `Trial Rejected: ${errText.slice(0, 80)}`);
                        stopWatcher();
                        // 1. Report dead immediately before context dies
                        if (isRunning && myId === executionId) {
                            reportResult('dead');
                        }
                        // 2. Small delay to ensure message sends, then navigate back
                        setTimeout(() => {
                            window.history.back();
                        }, 300);
                        return;
                    }

                    if (/payment failed|try again|different payment|different card/i.test(errText)) {
                        log('dead', '❌', `Payment failed: ${errText.slice(0, 80)}`);
                        stopWatcher();
                        reportResult('dead');
                        return;
                    }
                }

                // Check success: URL change to /success or confirmation element
                if (window.location.href.includes('success') ||
                    window.location.href.includes('confirmation') ||
                    window.location.href.includes('welcome')) {
                    log('live', '✅', 'Purchase successful! URL: ' + window.location.href);
                    stopWatcher();
                    reportResult('live');
                    return;
                }

                const successEl = document.querySelector(
                    '[data-testid="purchase-success"], [class*="success"], .checkout-success, [data-testid="checkout-confirmation"]'
                );
                if (successEl && successEl.offsetParent !== null) {
                    log('live', '✅', 'Purchase confirmed!');
                    stopWatcher();
                    reportResult('live');
                    return;
                }

                if (waited >= maxWait) {
                    log('dead', '⏰', 'Timeout waiting for result — treating as dead');
                    stopWatcher();
                    reportResult('dead');
                }
            }, 500);
        }

        function stopWatcher() {
            if (checkInterval) { clearInterval(checkInterval); checkInterval = null; }
        }

        function findErrorBanner() {
            // Check specifically for Trial Rejection text anywhere in visible divs
            // The orange banner sometimes lacks standard error/alert classes
            const allTextDivs = document.querySelectorAll('div, span, p');
            for (const el of allTextDivs) {
                if (el.offsetParent !== null && typeof el.textContent === 'string') {
                    if (/payment method was already used|already used for an offer or trial/i.test(el.textContent)) {
                        return el;
                    }
                }
            }

            // Fallback for standard error banners
            const banners = document.querySelectorAll('[data-encore-id="banner"], [data-testid="error-banner-wrapper"]');
            for (const b of banners) {
                if (b.offsetParent !== null && typeof b.textContent === 'string' && b.textContent.includes('payment')) return b;
            }

            const alerts = document.querySelectorAll('[class*="banner"], [class*="error"], [class*="alert"]');
            for (const a of alerts) {
                if (a.offsetParent !== null && typeof a.textContent === 'string' && /payment failed|try again|different.*card/i.test(a.textContent)) return a;
            }
            return null;
        }

        async function clickSubmit(myId) {
            let btn = document.getElementById('checkout_submit');
            if (!btn) {
                // Find button by text "Complete purchase"
                const buttons = Array.from(document.querySelectorAll('button'));
                btn = buttons.find(b => b.textContent.includes('Complete purchase'));
            }
            if (!btn) btn = document.querySelector('button[class*="button-primary"], button[data-encore-id="buttonPrimary"], .encore-bright-accent-set');

            if (btn) {
                log('info', '🚀', 'Checking "Complete purchase" button state...');
                btn.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // Wait up to 5s for button to be enabled
                let attempts = 0;
                while (btn.disabled && attempts < 10) {
                    if (!isRunning || myId !== executionId) return;
                    log('info', '⏳', `Waiting for validation (${attempts + 1}/10)...`);
                    await sleep(500);
                    attempts++;
                }

                if (!isRunning || myId !== executionId) return;

                if (!btn.disabled) {
                    log('info', '⚡', 'Clicking submit now!');
                    btn.click();
                    // Backup click via dispatch
                    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                } else {
                    log('error', '❌', 'Submit button remains disabled — validation failed?');
                    // Try force click even if disabled? (Sometimes helps if UI is sluggish)
                    btn.click();
                }
            } else {
                log('warn', '⚠', 'Submit button not found!');
            }
        }

        function reportResult(result) {
            try {
                chrome.runtime.sendMessage({
                    action: 'cardResult',
                    result,
                    loopDelay
                });
            } catch (e) {
                // Ignore context invalidated
            }
        }
    }

    // ─────────────────────────────────────────────────────────
    // PCI FRAME (pci.spotify.com): receives postMessage, fills fields
    // ─────────────────────────────────────────────────────────
    if (IS_PCI_FRAME) {
        let pciExecutionId = 0;

        // Listen for postMessage from top frame
        window.addEventListener('message', async (event) => {
            let data;
            try { data = JSON.parse(event.data); } catch { return; }
            if (!data.__spotifyAutoFill__) return;

            if (data.action === 'fillCard') {
                pciExecutionId = data.executionId || 0;
                fillDelay = data.fillDelay || 300;
                await fillCardForm(data.cardData, pciExecutionId);
            }
        });

        async function fillCardForm(card, myId) {
            if (!card) return;
            if (myId !== pciExecutionId) return;

            log('info', '🎴', `Filling PCI iframe: ${card.number} ${card.expiry?.formatted} ${card.cvv}`);

            const stepDelay = Math.max(fillDelay, 250);

            // Wait for fields to appear
            const numField = await waitForEl('#cardnumber', 5000);
            if (!numField) { log('warn', '⚠', 'Card number field not found in PCI frame'); return; }
            if (myId !== pciExecutionId) return;

            await fillField(numField, card.number, stepDelay);
            if (myId !== pciExecutionId) return;
            log('info', '💳', `Bin: ${card.number}`);

            const expField = document.getElementById('expiry-date');
            if (expField) {
                const expVal = `${card.expiry?.month || '01'} / ${card.expiry?.yearShort || '30'}`;
                await fillField(expField, expVal, stepDelay);
                if (myId !== pciExecutionId) return;
                log('info', '📅', `Expiry: ${expVal}`);
            }

            const cvvField = document.getElementById('security-code');
            if (cvvField) {
                await fillField(cvvField, card.cvv || '', stepDelay);
                if (myId !== pciExecutionId) return;
                log('info', '🔒', `CVV: ${'•'.repeat((card.cvv || '').length)}`);
            }

            log('info', '✓', 'PCI fields filled');
        }
    }

    // ─────────────────────────────────────────────────────────
    // SHARED UTILITIES
    // ─────────────────────────────────────────────────────────

    function sleep(ms) {
        return new Promise(r => setTimeout(r, ms));
    }

    async function waitForEl(selector, timeout = 4000) {
        const interval = 150;
        let waited = 0;
        while (waited < timeout) {
            const el = document.querySelector(selector);
            if (el) return el;
            await sleep(interval);
            waited += interval;
        }
        return null;
    }

    async function fillField(field, value, delay = 350) {
        if (!field || value === null || value === undefined) return;

        field.focus();
        const win = field.ownerDocument?.defaultView || window;
        let setter = null;

        if (field.tagName === 'INPUT') {
            setter = Object.getOwnPropertyDescriptor(win.HTMLInputElement.prototype, 'value');
        }

        // Fill full string at once (Direct Injection)
        const stringValue = String(value);
        if (setter?.set) setter.set.call(field, stringValue);
        else field.value = stringValue;

        // Dispatch events so React picks it up
        field.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: stringValue }));
        field.dispatchEvent(new Event('change', { bubbles: true }));

        await sleep(50);
        field.blur();
        await sleep(delay);
    }

    function dispatchKey(field, type, key) {
        let code = 'Unidentified';
        if (/^\d$/.test(key)) code = `Digit${key}`;
        else if (key === '/') code = 'Slash';
        else if (key === ' ') code = 'Space';
        field.dispatchEvent(new KeyboardEvent(type, {
            key, code, keyCode: key.charCodeAt(0), which: key.charCodeAt(0), bubbles: true
        }));
    }
}
