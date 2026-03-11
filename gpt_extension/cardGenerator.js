/**
 * Card Generator - BIN-based card number generation with Luhn algorithm
 * Supports: Visa, Mastercard, UnionPay, Amex, Discover, JCB, Diners
 *
 * Algorithms:
 *  - Luhn (Mod 10) for check digit generation & validation
 *  - BIN/IIN prefix matching (ordered by specificity, longest prefix first)
 */

'use strict';

const MIN_CARD_LENGTH = 13;
const MAX_CARD_LENGTH = 19;

// ─── Card Type Definitions ────────────────────────────────────────────────────
// Patterns are tested in ORDER — more specific patterns MUST come first!
// Each entry: { name, shortName, patterns (fn|regex), lengths, cvvLength, color, gradient, emoji }
const CARD_TYPES = {
  AMEX: {
    name: 'American Express',
    shortName: 'AMEX',
    // Starts with 34 or 37
    patterns: [/^3[47]/],
    lengths: [15],
    cvvLength: 4,
    color: '#2E77BC',
    gradient: 'linear-gradient(135deg, #1a5276, #2e77bc)',
    emoji: '💎',
    mask: '#### ###### #####'
  },
  DISCOVER: {
    name: 'Discover',
    shortName: 'DISC',
    // 6011, 644–649, 65, 622126–622925 (overlaps UnionPay — check before UP)
    patterns: [/^6011/, /^64[4-9]/, /^65/],
    lengths: [16, 19],
    cvvLength: 3,
    color: '#FF6600',
    gradient: 'linear-gradient(135deg, #e65c00, #f9d423)',
    emoji: '🔶',
    mask: '#### #### #### ####'
  },
  MASTERCARD: {
    name: 'Mastercard',
    shortName: 'MC',
    // 51–55 or 2221–2720 (Mastercard 2-series, exact range check via function)
    patterns: [
      /^5[1-5]/,
      (bin) => {
        // 2-series: 222100–272099
        const prefix = parseInt(bin.substring(0, 6).padEnd(6, '0'), 10);
        return prefix >= 222100 && prefix <= 272099;
      }
    ],
    lengths: [16],
    cvvLength: 3,
    color: '#EB001B',
    gradient: 'linear-gradient(135deg, #eb001b, #f79e1b)',
    emoji: '🟠',
    mask: '#### #### #### ####'
  },
  UNIONPAY: {
    name: 'UnionPay',
    shortName: 'CUP',
    // 62x or 60 (Vietnam UnionPay cards often start 60)
    patterns: [/^62/, /^60/],
    lengths: [16, 17, 18, 19],
    cvvLength: 3,
    color: '#D0021B',
    gradient: 'linear-gradient(135deg, #8B0000, #d0021b)',
    emoji: '🔴',
    mask: '#### #### #### ####'
  },
  JCB: {
    name: 'JCB',
    shortName: 'JCB',
    // 3528–3589
    patterns: [/^35[2-8]/],
    lengths: [16, 17, 18, 19],
    cvvLength: 3,
    color: '#003087',
    gradient: 'linear-gradient(135deg, #003087, #009f6b)',
    emoji: '🇯🇵',
    mask: '#### #### #### ####'
  },
  DINERS: {
    name: 'Diners Club',
    shortName: 'DC',
    // 300–305, 36, 38, 39
    patterns: [/^30[0-5]/, /^36/, /^38/, /^39/],
    lengths: [14],
    cvvLength: 3,
    color: '#5A5A5A',
    gradient: 'linear-gradient(135deg, #333, #666)',
    emoji: '⚫',
    mask: '#### ###### ####'
  },
  VISA: {
    name: 'Visa',
    shortName: 'VISA',
    // Starts with 4 (broadest — must be last)
    patterns: [/^4/],
    lengths: [13, 16, 19],
    cvvLength: 3,
    color: '#1A1F71',
    gradient: 'linear-gradient(135deg, #1a1f71, #0057b8)',
    emoji: '💳',
    mask: '#### #### #### ####'
  }
};

// ─── Utility ──────────────────────────────────────────────────────────────────

function sanitizeDigits(value) {
  return String(value || '').replace(/\D/g, '');
}

function randomDigits(length) {
  let out = '';
  for (let i = 0; i < length; i++) out += Math.floor(Math.random() * 10);
  return out;
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// ─── Card Type Detection ───────────────────────────────────────────────────────

/**
 * Detect card network from BIN/partial card number.
 * Tests patterns in definition ORDER (more specific types listed first).
 * @param {string} bin - BIN or full card number
 * @returns {{ type: string, ...cardTypeProps } | null}
 */
function detectCardType(bin) {
  const binStr = sanitizeDigits(bin);
  if (!binStr) return null;

  for (const [key, cardType] of Object.entries(CARD_TYPES)) {
    for (const pattern of cardType.patterns) {
      const matches = (typeof pattern === 'function')
        ? pattern(binStr)
        : pattern.test(binStr);

      if (matches) {
        return { type: key, ...cardType };
      }
    }
  }
  return null;
}

// ─── Luhn Algorithm ───────────────────────────────────────────────────────────

/**
 * Calculate Luhn check digit for a partial card number (without check digit).
 * Steps:
 *  1. From right, double every 2nd digit (positions: 2,4,6,... from right)
 *  2. If doubled value > 9, subtract 9
 *  3. Sum all digits
 *  4. Check digit = (10 - sum%10) % 10
 *
 * @param {string} partialNumber - Card number WITHOUT check digit
 * @returns {number} Check digit 0–9
 */
function calculateLuhnCheckDigit(partialNumber) {
  const digits = sanitizeDigits(partialNumber).split('').map(Number);
  let sum = 0;

  // We process right-to-left. The rightmost digit of `partialNumber`
  // is at even position (0-indexed from right), so it gets doubled.
  for (let i = digits.length - 1; i >= 0; i--) {
    let d = digits[i];
    // Position from right (0-indexed): digits.length-1-i
    // Even positions from right → double
    const posFromRight = digits.length - 1 - i;
    if (posFromRight % 2 === 0) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    sum += d;
  }

  return (10 - (sum % 10)) % 10;
}

/**
 * Validate a full card number using Luhn algorithm.
 * @param {string} cardNumber - Full card number including check digit
 * @returns {boolean}
 */
function validateLuhn(cardNumber) {
  const clean = sanitizeDigits(cardNumber);
  if (!clean || clean.length < MIN_CARD_LENGTH) return false;

  const digits = clean.split('').map(Number);
  let sum = 0;

  for (let i = digits.length - 1; i >= 0; i--) {
    let d = digits[i];
    const posFromRight = digits.length - 1 - i;
    // Check digit itself (pos 0) is NOT doubled
    if (posFromRight % 2 === 1) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    sum += d;
  }

  return sum % 10 === 0;
}

// ─── Expiry ───────────────────────────────────────────────────────────────────

function normalizeMonth(month) {
  if (month === null || month === undefined || month === '') return null;
  const n = parseInt(String(month), 10);
  if (isNaN(n) || n < 1 || n > 12) throw new Error('Month must be 1–12');
  return String(n).padStart(2, '0');
}

function normalizeYear(year) {
  if (year === null || year === undefined || year === '') return null;
  const digits = sanitizeDigits(year);
  if (digits.length === 2) return `20${digits}`;
  if (digits.length !== 4) throw new Error('Year must be 2 or 4 digits');
  return digits;
}

function buildExpiry(month, year) {
  const m = normalizeMonth(month);
  const y = normalizeYear(year);
  if (!m || !y) throw new Error('Month and year are required');
  return {
    month: m,
    year: y,
    yearShort: y.slice(-2),
    formatted: `${m}/${y.slice(-2)}`
  };
}

function generateRandomExpiry() {
  const now = new Date();
  const year = String(now.getFullYear() + randomInt(1, 5));
  const month = String(randomInt(1, 12)).padStart(2, '0');
  return buildExpiry(month, year);
}

// ─── CVV ──────────────────────────────────────────────────────────────────────

function generateCvv(cardType) {
  return randomDigits(cardType ? cardType.cvvLength : 3);
}

function normalizeCvv(cvv, cardType) {
  const digits = sanitizeDigits(cvv);
  if (!digits) return generateCvv(cardType);
  const expectedLen = cardType ? cardType.cvvLength : digits.length;
  if (digits.length > expectedLen) throw new Error(`CVV max ${expectedLen} digits`);
  return digits.padStart(expectedLen, '0');
}

// ─── BIN Generation ───────────────────────────────────────────────────────────

/**
 * Generate a random valid BIN for a given card network.
 * BINs generated here are structurally valid (pass prefix checks)
 * but are NOT real bank BINs.
 */
function generateRandomBIN(cardType = 'VISA') {
  const key = String(cardType).toUpperCase();
  if (!CARD_TYPES[key]) throw new Error(`Unknown card type: ${cardType}`);

  switch (key) {
    case 'VISA':
      return `4${randomDigits(5)}`;

    case 'MASTERCARD':
      return Math.random() < 0.5
        ? `5${randomInt(1, 5)}${randomDigits(4)}`
        : `${randomInt(2221, 2720)}${randomDigits(2)}`;

    case 'AMEX':
      return `3${Math.random() < 0.5 ? '4' : '7'}${randomDigits(4)}`;

    case 'DISCOVER':
      return `6011${randomDigits(2)}`;

    case 'UNIONPAY':
      return Math.random() < 0.7
        ? `62${randomDigits(4)}`
        : `60${randomDigits(4)}`;

    case 'JCB':
      return `35${randomInt(28, 89)}${randomDigits(2)}`;

    case 'DINERS':
      return `30${randomInt(0, 5)}${randomDigits(3)}`;

    default:
      return `4${randomDigits(5)}`;
  }
}

// ─── Card Number Generation ───────────────────────────────────────────────────

function resolveCardLength(binStr, overrideLength, cardType) {
  if (overrideLength) {
    const l = parseInt(String(overrideLength), 10);
    if (isNaN(l) || l < MIN_CARD_LENGTH || l > MAX_CARD_LENGTH) {
      throw new Error(`Card length must be ${MIN_CARD_LENGTH}–${MAX_CARD_LENGTH}`);
    }
    return l;
  }
  return cardType ? cardType.lengths[0] : 16;
}

/**
 * Generate one card number from a BIN using Luhn.
 * @param {string} bin - BIN (2–12 digits)
 * @param {number|null} length - Total card length (null = auto by network)
 * @param {string} cardTypeOverride - Fallback network key if BIN undetected
 * @returns {string} Full card number (passes Luhn validation)
 */
function generateCardFromBIN(bin, length = null, cardTypeOverride = '') {
  const binStr = sanitizeDigits(bin);
  if (!binStr || binStr.length < 2 || binStr.length > 12) {
    throw new Error('BIN must be 2–12 digits');
  }

  const cardType = detectCardType(binStr) ||
    (cardTypeOverride && CARD_TYPES[cardTypeOverride.toUpperCase()]
      ? { type: cardTypeOverride.toUpperCase(), ...CARD_TYPES[cardTypeOverride.toUpperCase()] }
      : null);

  const cardLength = resolveCardLength(binStr, length, cardType);

  if (binStr.length >= cardLength) {
    throw new Error(`BIN (${binStr.length} digits) too long for card length ${cardLength}`);
  }

  const middleLen = cardLength - binStr.length - 1; // -1 for check digit
  const middle = randomDigits(middleLen);
  const withoutCheck = `${binStr}${middle}`;
  const checkDigit = calculateLuhnCheckDigit(withoutCheck);

  return `${withoutCheck}${checkDigit}`;
}

/**
 * Generate multiple unique card numbers from a BIN.
 */
function generateMultipleCards(bin, quantity = 10, length = null, cardTypeOverride = '') {
  const cards = [];
  const seen = new Set();
  const maxAttempts = quantity * 25;
  let attempts = 0;

  while (cards.length < quantity && attempts < maxAttempts) {
    const card = generateCardFromBIN(bin, length, cardTypeOverride);
    if (!seen.has(card)) {
      seen.add(card);
      cards.push(card);
    }
    attempts++;
  }

  return cards;
}

// ─── Full Card (number + expiry + CVV) ───────────────────────────────────────

/**
 * Generate a complete card object from a BIN.
 * @param {string} bin
 * @param {object} options - { length, month, year, cvv, cardType, holderName }
 * @returns {CardObject}
 */
function generateFullCard(bin, options = {}) {
  const baseNumber = options.number
    ? sanitizeDigits(options.number)
    : generateCardFromBIN(bin, options.length, options.cardType);

  if (baseNumber.length < MIN_CARD_LENGTH || baseNumber.length > MAX_CARD_LENGTH) {
    throw new Error(`Card number must be ${MIN_CARD_LENGTH}–${MAX_CARD_LENGTH} digits`);
  }
  if (!validateLuhn(baseNumber)) {
    throw new Error('Card number failed Luhn validation');
  }

  const cardType = detectCardType(baseNumber) ||
    (options.cardType && CARD_TYPES[options.cardType.toUpperCase()]
      ? { type: options.cardType.toUpperCase(), ...CARD_TYPES[options.cardType.toUpperCase()] }
      : null);

  const randomExpiry = generateRandomExpiry();
  const expiry = buildExpiry(
    options.month || randomExpiry.month,
    options.year || randomExpiry.year
  );


  return {
    number: baseNumber,
    numberFormatted: formatCardNumber(baseNumber, cardType),
    expiry,
    cvv: normalizeCvv(options.cvv, cardType),
    type: cardType ? cardType.name : 'Unknown',
    shortName: cardType ? cardType.shortName : '???',
    cardType: cardType ? cardType.type : '',
    color: cardType ? cardType.color : '#333',
    gradient: cardType ? cardType.gradient : 'linear-gradient(135deg,#333,#555)',
    emoji: cardType ? cardType.emoji : '💳',
    bin: extractBIN(baseNumber),
    isValid: true  // Already validated above
  };
}

function generateMultipleCardDetails(bin, quantity = 10, options = {}) {
  const cards = [];
  const seen = new Set();
  const maxAttempts = quantity * 25;
  let attempts = 0;

  while (cards.length < quantity && attempts < maxAttempts) {
    const card = generateFullCard(bin, options);
    if (!seen.has(card.number)) {
      seen.add(card.number);
      cards.push(card);
    }
    attempts++;
  }
  return cards;
}

// ─── Formatting ───────────────────────────────────────────────────────────────

/**
 * Format card number with spaces according to card network mask.
 * AMEX: 4-6-5, Diners: 4-6-4, others: 4-4-4-4 (or 4-4-4-4-x for 17–19 digits)
 */
function formatCardNumber(cardNumber, cardType = null) {
  const clean = sanitizeDigits(cardNumber);
  const type = cardType || detectCardType(clean);
  const key = type ? type.type : null;

  if (key === 'AMEX' && clean.length === 15) {
    return clean.replace(/(\d{4})(\d{6})(\d{5})/, '$1 $2 $3');
  }
  if (key === 'DINERS' && clean.length === 14) {
    return clean.replace(/(\d{4})(\d{6})(\d{4})/, '$1 $2 $3');
  }

  // Default: 4-4-4-4 (extra digits appended)
  return (clean.match(/.{1,4}/g) || []).join(' ');
}

/**
 * Mask card number for display: show only last 4 digits.
 * e.g. "4532 **** **** 1234"
 */
function maskCardNumber(cardNumber) {
  const clean = sanitizeDigits(cardNumber);
  const last4 = clean.slice(-4);
  const masked = '*'.repeat(clean.length - 4);
  const full = masked + last4;
  return (full.match(/.{1,4}/g) || []).join(' ');
}

// ─── Parse & Extract ──────────────────────────────────────────────────────────

/**
 * Parse pipe-delimited card string: "number|MM|YY|CVV" or "number|MM|YY"
 */
function parseCardData(cardString) {
  if (!cardString) return null;
  const parts = cardString.split('|').map(p => p.trim());
  if (parts.length < 3 || parts.length > 4) return null;

  const [rawNumber, rawMonth, rawYear, rawCvv = ''] = parts;
  const cardNumber = sanitizeDigits(rawNumber);
  if (cardNumber.length < MIN_CARD_LENGTH || cardNumber.length > MAX_CARD_LENGTH) return null;

  let expiry;
  try { expiry = buildExpiry(rawMonth, rawYear); }
  catch { return null; }

  const cardType = detectCardType(cardNumber);
  let cvv;
  try { cvv = rawCvv ? normalizeCvv(rawCvv, cardType) : generateCvv(cardType); }
  catch { return null; }

  return {
    number: cardNumber,
    month: expiry.month,
    year: expiry.year,
    yearShort: expiry.yearShort,
    cvv,
    expiry,
    type: cardType ? cardType.name : 'Unknown',
    shortName: cardType ? cardType.shortName : '???',
    cardType: cardType ? cardType.type : '',
    isValid: validateLuhn(cardNumber)
  };
}

function extractBIN(cardNumber, length = 6) {
  return sanitizeDigits(cardNumber).substring(0, length);
}

// ─── Misc Helpers ─────────────────────────────────────────────────────────────

const HOLDER_NAMES = [
  'NGUYEN VAN AN', 'TRAN THI BICH', 'LE MINH TUAN', 'PHAM THU HA',
  'HOANG VAN LONG', 'VU THI LAN', 'DO QUANG HUNG', 'BUI THI MAI',
  'JOHN DOE', 'JANE SMITH', 'MICHAEL JOHNSON', 'SARAH WILLIAMS'
];

function generateRandomHolderName() {
  return HOLDER_NAMES[Math.floor(Math.random() * HOLDER_NAMES.length)];
}

/**
 * Get network info for UI rendering.
 * @param {string} cardNumberOrBin
 * @returns {{ name, shortName, color, gradient, emoji } | null}
 */
function getNetworkInfo(cardNumberOrBin) {
  return detectCardType(cardNumberOrBin);
}

// ─── Export ───────────────────────────────────────────────────────────────────

const CardGeneratorAPI = {
  CARD_TYPES,
  detectCardType,
  getNetworkInfo,
  calculateLuhnCheckDigit,
  validateLuhn,
  generateCardFromBIN,
  generateMultipleCards,
  generateFullCard,
  generateMultipleCardDetails,
  generateRandomBIN,
  formatCardNumber,
  maskCardNumber,
  parseCardData,
  extractBIN,
  buildExpiry,
  generateRandomExpiry,
  generateRandomHolderName
};

if (typeof module !== 'undefined' && module.exports) module.exports = CardGeneratorAPI;
if (typeof window !== 'undefined') window.CardGenerator = CardGeneratorAPI;
if (typeof self !== 'undefined' && typeof window === 'undefined') self.CardGenerator = CardGeneratorAPI;
