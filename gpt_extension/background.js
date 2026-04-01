// Background service worker for Auto Fill GPT extension.
// Keeps extension settings available and exposes utility actions.

importScripts('cardGenerator.js');

const DEFAULT_SETTINGS = {
  country: 'US',
  state: '',
  province: '',
  savedAddress: '',
  bin: '',
  quantity: '10',
  cardType: '',
  cardLength: '',
  expiryMonth: '',
  expiryYear: '',
  cvv: '',
  lastFilledCard: null
};

function getStoredSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(['settings'], (result) => {
      resolve(result.settings || null);
    });
  });
}

function saveStoredSettings(settings) {
  return new Promise((resolve) => {
    chrome.storage.sync.set({ settings }, () => {
      resolve(settings);
    });
  });
}

async function getMergedSettings() {
  const storedSettings = await getStoredSettings();
  return {
    ...DEFAULT_SETTINGS,
    ...(storedSettings || {})
  };
}

async function ensureDefaultSettings() {
  const settings = await getMergedSettings();
  await saveStoredSettings(settings);
  return settings;
}

function buildGenerationOptions(request = {}) {
  return {
    month: request.month || '',
    year: request.year || '',
    cvv: request.cvv || '',
    length: request.length || null,
    cardType: request.cardType || '',
    number: request.number || ''
  };
}

async function handleGetSettings() {
  return getMergedSettings();
}

async function handleSaveSettings(request) {
  const nextSettings = {
    ...(await getMergedSettings()),
    ...(request.settings || {})
  };

  await saveStoredSettings(nextSettings);
  return { success: true, settings: nextSettings };
}

async function handleGenerateCard(request) {
  if (typeof CardGenerator === 'undefined') {
    throw new Error('CardGenerator not available in background worker');
  }

  const bin = String(request.bin || '').trim();
  if (!bin && !request.number) {
    throw new Error('BIN is required to generate a card');
  }

  const card = CardGenerator.generateFullCard(bin, buildGenerationOptions(request));
  return { success: true, card };
}

// ─── Fill Coordinator (Cross-frame sync) ──────────────────────
let activeFillCounts = {}; // tabId -> count

function handleFillStatus(request, sender) {
  const tabId = sender.tab?.id;
  if (!tabId) return;

  if (request.status === 'reset') {
    activeFillCounts[tabId] = 0;
    return;
  }

  if (!activeFillCounts[tabId]) activeFillCounts[tabId] = 0;

  if (request.status === 'started') {
    activeFillCounts[tabId]++;
    console.log(`[Coordinator] Tab ${tabId}: Frame started filling. Total active: ${activeFillCounts[tabId]}`);
  } else if (request.status === 'finished') {
    activeFillCounts[tabId] = Math.max(0, activeFillCounts[tabId] - 1);
    console.log(`[Coordinator] Tab ${tabId}: Frame finished. Remaining: ${activeFillCounts[tabId]}`);

    if (activeFillCounts[tabId] === 0) {
      // Small debounce to ensure no other frames are mid-start
      setTimeout(() => {
        if (activeFillCounts[tabId] === 0) {
          console.log(`[Coordinator] Tab ${tabId}: All frames finished! Triggering subscribe...`);
          chrome.tabs.sendMessage(tabId, { action: 'all_fills_complete' }).catch(() => {});
        }
      }, 150);
    }
  }
}

const MESSAGE_HANDLERS = {
  getSettings: handleGetSettings,
  saveSettings: handleSaveSettings,
  generateCard: handleGenerateCard,
  fill_status: (req, sender) => { handleFillStatus(req, sender); return { success: true }; }
};

chrome.runtime.onInstalled.addListener(async (details) => {
  const settings = await ensureDefaultSettings();
  console.log('Auto Fill GPT installed', {
    reason: details.reason,
    settingsInitialized: Boolean(settings)
  });
});

chrome.runtime.onStartup.addListener(() => {
  console.log('Auto Fill GPT background worker started');
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  const action = request && request.action;
  const handler = MESSAGE_HANDLERS[action];

  if (!handler) {
    return false;
  }

  Promise.resolve(handler(request, sender))
    .then((result) => {
      sendResponse(result);
    })
    .catch((error) => {
      console.error(`Background action failed: ${action}`, error);
      sendResponse({
        success: false,
        error: error instanceof Error ? error.message : String(error)
      });
    });

  return true;
});

console.log('Background service worker ready');
