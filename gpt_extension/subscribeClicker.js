/**
 * ═════════════════════════════════════════════════════════════
 * Dedicated Subscribe Clicker Service
 * Targets ChatGPT / Stripe Checkout Buttons specifically.
 * ═════════════════════════════════════════════════════════════
 */

(function() {
  'use strict';

  if (window.__subscribeClickerLoaded) return;
  window.__subscribeClickerLoaded = true;

  console.log('[Clicker] Subscribe Clicker Service initialized.');

  window.performSubscribe = async function() {
    if (window.__isSubscribing) {
       console.log('[Clicker] Already searching for button. Skipping duplicate call.');
       return false;
    }
    window.__isSubscribing = true;
    
    const MAX_TRIES = 15;
    const INTERVAL = 400;

    console.log('[Clicker] Starting 🚀 Auto Subscribe scan...');

    for (let i = 0; i < MAX_TRIES; i++) {
        // ... find candidates ...
      const candidates = [
        ...document.querySelectorAll('button[aria-label*="Subscribe" i]'),
        ...document.querySelectorAll('.btn-primary.w-full.p-4.text-base'),
        ...document.querySelectorAll('button[type="submit"][form*="_r_"]'),
        ...document.querySelectorAll('[data-testid*="subscribe" i]'),
        ...document.querySelectorAll('[data-testid*="payment-submit" i]'),
        ...document.querySelectorAll('button')
      ];

      let targetBtn = null;

      for (const btn of candidates) {
        if (!btn) continue;

        const text = (btn.textContent || '').trim().toLowerCase();
        const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
        
        // Stricter matching to be safer but include "Try", "Start", "Pay"
        const isExplicitMatch = 
          text === 'subscribe' || text.includes('subscribe') || 
          text === 'pay $20.00' || text === 'confirm payment' || 
          text.startsWith('pay ') || text.startsWith('start ') ||
          text.startsWith('try ') || text === 'proceed' ||
          text.includes('checkout') || text.includes('continue to payment');

        if (!isExplicitMatch && !ariaLabel.includes('subscribe') && !ariaLabel.includes('payment')) continue;

        const style = window.getComputedStyle(btn);
        const rect = btn.getBoundingClientRect();
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0' || rect.width < 50) continue;

        const isDisabled = btn.disabled || btn.getAttribute('aria-disabled') === 'true' || btn.classList.contains('disabled');
        if (!isDisabled) {
           targetBtn = btn;
           break; 
        }
      }

      if (targetBtn) {
        const humanDelay = Math.floor(Math.random() * 500) + 100;
        console.log(`[Clicker] 🚀 Button found! Clicking in ${humanDelay}ms...`);
        
        // Visual feedback: Flash the button so the user sees it
        const oldOutline = targetBtn.style.outline;
        const oldTransition = targetBtn.style.transition;
        targetBtn.style.transition = 'none';
        targetBtn.style.outline = '4px solid #ff4d4d'; // Red flash
        targetBtn.style.boxShadow = '0 0 15px #ff4d4d';
        
        await new Promise(r => setTimeout(r, humanDelay));
        
        // Clear flash
        targetBtn.style.outline = oldOutline;
        targetBtn.style.boxShadow = 'none';
        targetBtn.style.transition = oldTransition;

        await simulateHumanClick(targetBtn);
        
        if (chrome.runtime?.id) {
          try {
            chrome.runtime.sendMessage({ action: 'log_step', type: 'success', icon: '🚀', msg: '[Clicker] Auto-clicked Subscribe 1 time!' }).catch(() => {});
          } catch(e) {}
        }
        
        window.__isSubscribing = false;
        return true;
      }
      
      await new Promise(r => setTimeout(r, INTERVAL));
    }
    
    window.__isSubscribing = false;
    console.log('[Clicker] ⏳ Could not find target button in this frame.');
    return false;
  };

  async function simulateHumanClick(el) {
    if (!el) return;
    
    // 1. Di chuột tới và Focus (như người đang chuẩn bị bấm)
    const rect = el.getBoundingClientRect();
    const mouseParams = { bubbles: true, cancelable: true, view: window, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
    
    el.dispatchEvent(new MouseEvent('mouseover', mouseParams));
    el.dispatchEvent(new MouseEvent('mouseenter', mouseParams));
    el.focus();
    
    // Chờ một chút ngắn (phản xạ người)
    await new Promise(r => setTimeout(r, Math.floor(Math.random() * 50) + 50));

    // 2. Thực hiện chuỗi Click
    el.dispatchEvent(new PointerEvent('pointerdown', mouseParams));
    el.dispatchEvent(new MouseEvent('mousedown', mouseParams));
    
    // Giữ chuột xuống khoảng 80-150ms như người thật
    await new Promise(r => setTimeout(r, Math.floor(Math.random() * 70) + 80));
    
    el.dispatchEvent(new PointerEvent('pointerup', mouseParams));
    el.dispatchEvent(new MouseEvent('mouseup', mouseParams));
    el.dispatchEvent(new MouseEvent('click', mouseParams));

    // Backup click cuối cùng để chắc chắn
    setTimeout(() => { try { el.click(); } catch(e){} }, 20);
  }

})();
