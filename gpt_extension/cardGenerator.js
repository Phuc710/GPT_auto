/**
 * Card Generator - BIN-based card number generation with Luhn algorithm
 * Generates valid card numbers for testing purposes.
 */

const MIN_CARD_LENGTH = 13;
const MAX_CARD_LENGTH = 19;

// Card type detection based on BIN patterns
const CARD_TYPES = {
  VISA: {
    name: 'Visa',
    patterns: [/^4/],
    lengths: [13, 16, 19],
    cvvLength: 3
  },
  MASTERCARD: {
    name: 'Mastercard',
    patterns: [/^5[1-5]/, /^2[2-7]/],
    lengths: [16],
    cvvLength: 3
  },
  AMEX: {
    name: 'American Express',
    patterns: [/^3[47]/],
    lengths: [15],
    cvvLength: 4
  },
  DISCOVER: {
    name: 'Discover',
    patterns: [/^6011/, /^65/, /^64[4-9]/, /^622/],
    lengths: [16],
    cvvLength: 3
  },
  DINERS: {
    name: 'Diners Club',
    patterns: [/^3[068]/, /^39/],
    lengths: [14],
    cvvLength: 3
  },
  JCB: {
    name: 'JCB',
    patterns: [/^35/],
    lengths: [16],
    cvvLength: 3
  },
  UNIONPAY: {
    name: 'UnionPay',
    patterns: [/^62/],
    lengths: [16, 17, 18, 19],
    cvvLength: 3
  }
};

function sanitizeDigits(value) {
  return String(value || '').replace(/\D/g, '');
}

function randomDigits(length) {
  let output = '';

  for (let i = 0; i < length; i++) {
    output += Math.floor(Math.random() * 10);
  }

  return output;
}

function normalizeMonth(month) {
  if (month === null || month === undefined || month === '') {
    return null;
  }

  const numericMonth = Number.parseInt(String(month), 10);
  if (Number.isNaN(numericMonth) || numericMonth < 1 || numericMonth > 12) {
    throw new Error('Month must be between 1 and 12');
  }

  return String(numericMonth).padStart(2, '0');
}

function normalizeYear(year) {
  if (year === null || year === undefined || year === '') {
    return null;
  }

  const digits = sanitizeDigits(year);
  if (digits.length === 2) {
    return `20${digits}`;
  }

  if (digits.length !== 4) {
    throw new Error('Year must be 2 or 4 digits');
  }

  return digits;
}

function buildExpiry(month, year) {
  const normalizedMonth = normalizeMonth(month);
  const normalizedYear = normalizeYear(year);

  if (!normalizedMonth || !normalizedYear) {
    throw new Error('Month and year are required');
  }

  return {
    month: normalizedMonth,
    year: normalizedYear,
    yearShort: normalizedYear.slice(-2),
    formatted: `${normalizedMonth}/${normalizedYear.slice(-2)}`
  };
}

function generateRandomExpiry() {
  const now = new Date();
  const yearOffset = Math.floor(Math.random() * 5) + 1;
  const year = String(now.getFullYear() + yearOffset);
  const month = String(Math.floor(Math.random() * 12) + 1).padStart(2, '0');

  return buildExpiry(month, year);
}

function resolveCardType(cardNumberOrBin, overrideType = '') {
  const detectedType = detectCardType(cardNumberOrBin);
  if (detectedType) {
    return detectedType;
  }

  const overrideKey = String(overrideType || '').trim().toUpperCase();
  if (overrideKey && CARD_TYPES[overrideKey]) {
    return {
      type: overrideKey,
      ...CARD_TYPES[overrideKey]
    };
  }

  return null;
}

function normalizeCvv(cvv, cardType) {
  const digits = sanitizeDigits(cvv);
  if (!digits) {
    return generateCvv(cardType);
  }

  const expectedLength = cardType ? cardType.cvvLength : digits.length;
  if (digits.length > expectedLength) {
    throw new Error(`CVV cannot exceed ${expectedLength} digits`);
  }

  return digits.padStart(expectedLength, '0');
}

function generateCvv(cardType) {
  const cvvLength = cardType ? cardType.cvvLength : 3;
  return randomDigits(cvvLength);
}

/**
 * Detect card type from BIN
 * @param {string} bin - Bank Identification Number
 * @returns {object|null} Card type info or null
 */
function detectCardType(bin) {
  const binStr = sanitizeDigits(bin);

  for (const [key, cardType] of Object.entries(CARD_TYPES)) {
    for (const pattern of cardType.patterns) {
      if (pattern.test(binStr)) {
        return {
          type: key,
          ...cardType
        };
      }
    }
  }

  return null;
}

/**
 * Luhn algorithm - Calculate check digit
 * @param {string} cardNumber - Card number without check digit
 * @returns {number} Check digit (0-9)
 */
function calculateLuhnCheckDigit(cardNumber) {
  const digits = sanitizeDigits(cardNumber).split('').map(Number);
  let sum = 0;
  let isEven = true;

  for (let i = digits.length - 1; i >= 0; i--) {
    let digit = digits[i];

    if (isEven) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }

    sum += digit;
    isEven = !isEven;
  }

  return (10 - (sum % 10)) % 10;
}

/**
 * Validate card number using Luhn algorithm
 * @param {string} cardNumber - Full card number
 * @returns {boolean} True if valid
 */
function validateLuhn(cardNumber) {
  const cleanNumber = sanitizeDigits(cardNumber);

  if (!/^\d+$/.test(cleanNumber)) {
    return false;
  }

  const digits = cleanNumber.split('').map(Number);
  let sum = 0;
  let isEven = false;

  for (let i = digits.length - 1; i >= 0; i--) {
    let digit = digits[i];

    if (isEven) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }

    sum += digit;
    isEven = !isEven;
  }

  return sum % 10 === 0;
}

function resolveCardLength(bin, overrideLength, cardType) {
  if (overrideLength) {
    const parsedLength = Number.parseInt(String(overrideLength), 10);
    if (Number.isNaN(parsedLength) || parsedLength < MIN_CARD_LENGTH || parsedLength > MAX_CARD_LENGTH) {
      throw new Error(`Card length must be between ${MIN_CARD_LENGTH} and ${MAX_CARD_LENGTH}`);
    }
    return parsedLength;
  }

  if (cardType) {
    return cardType.lengths[0];
  }

  return 16;
}

/**
 * Generate random card number from BIN
 * @param {string} bin - Bank Identification Number (2-12 digits)
 * @param {number} length - Desired card number length (default: auto-detect)
 * @param {string} cardTypeOverride - Optional fallback card type when BIN is generic
 * @returns {string} Generated valid card number
 */
function generateCardFromBIN(bin, length = null, cardTypeOverride = '') {
  const binStr = sanitizeDigits(bin);
  if (!binStr || binStr.length < 2 || binStr.length > 12) {
    throw new Error('BIN must be 2 to 12 digits');
  }

  const cardType = resolveCardType(binStr, cardTypeOverride);
  const cardLength = resolveCardLength(binStr, length, cardType);

  if (binStr.length >= cardLength) {
    throw new Error(`BIN too long for card length ${cardLength}`);
  }

  const middleLength = cardLength - binStr.length - 1;
  const middleDigits = randomDigits(middleLength);
  const withoutCheck = `${binStr}${middleDigits}`;
  const checkDigit = calculateLuhnCheckDigit(withoutCheck);

  return `${withoutCheck}${checkDigit}`;
}

/**
 * Generate multiple card numbers from BIN
 * @param {string} bin - Bank Identification Number
 * @param {number} quantity - Number of cards to generate
 * @param {number} length - Card length (optional)
 * @param {string} cardTypeOverride - Optional card type fallback
 * @returns {array} Array of generated card numbers
 */
function generateMultipleCards(bin, quantity = 10, length = null, cardTypeOverride = '') {
  const cards = [];
  const generated = new Set();
  let attempts = 0;
  const maxAttempts = quantity * 20;

  while (cards.length < quantity && attempts < maxAttempts) {
    const card = generateCardFromBIN(bin, length, cardTypeOverride);

    if (!generated.has(card)) {
      generated.add(card);
      cards.push(card);
    }

    attempts++;
  }

  return cards;
}

/**
 * Generate card with expiry and CVV
 * @param {string} bin - Bank Identification Number
 * @param {object} options - Generation options
 * @returns {object} Card with number, expiry, and CVV
 */
function generateFullCard(bin, options = {}) {
  const baseNumber = options.number
    ? sanitizeDigits(options.number)
    : generateCardFromBIN(bin, options.length, options.cardType);

  if (baseNumber.length < MIN_CARD_LENGTH || baseNumber.length > MAX_CARD_LENGTH) {
    throw new Error('Card number must be between 13 and 19 digits');
  }

  if (!validateLuhn(baseNumber)) {
    throw new Error('Card number failed Luhn validation');
  }

  const cardType = resolveCardType(baseNumber, options.cardType);
  const randomExpiry = generateRandomExpiry();
  const expiry = buildExpiry(
    options.month || randomExpiry.month,
    options.year || randomExpiry.year
  );

  return {
    number: baseNumber,
    numberFormatted: formatCardNumber(baseNumber),
    expiry,
    cvv: normalizeCvv(options.cvv, cardType),
    type: cardType ? cardType.name : 'Unknown',
    cardType: cardType ? cardType.type : '',
    bin: extractBIN(baseNumber),
    isValid: validateLuhn(baseNumber)
  };
}

function generateMultipleCardDetails(bin, quantity = 10, options = {}) {
  const cards = [];
  const generated = new Set();
  let attempts = 0;
  const maxAttempts = quantity * 20;

  while (cards.length < quantity && attempts < maxAttempts) {
    const card = generateFullCard(bin, options);

    if (!generated.has(card.number)) {
      generated.add(card.number);
      cards.push(card);
    }

    attempts++;
  }

  return cards;
}

/**
 * Format card number with spaces
 * @param {string} cardNumber - Card number
 * @returns {string} Formatted card number
 */
function formatCardNumber(cardNumber) {
  const cleaned = sanitizeDigits(cardNumber);

  if (cleaned.length === 15) {
    return cleaned.replace(/(\d{4})(\d{6})(\d{5})/, '$1 $2 $3');
  }

  return cleaned.match(/.{1,4}/g).join(' ');
}

/**
 * Parse card data string (format: cardnumber|month|year|cvv)
 * CVV is optional.
 * @param {string} cardString - Card data string
 * @returns {object|null} Parsed card data
 */
function parseCardData(cardString) {
  if (!cardString) {
    return null;
  }

  const parts = cardString.split('|').map((part) => part.trim());
  if (parts.length !== 3 && parts.length !== 4) {
    return null;
  }

  const [rawCardNumber, rawMonth, rawYear, rawCvv = ''] = parts;
  const cardNumber = sanitizeDigits(rawCardNumber);

  if (cardNumber.length < MIN_CARD_LENGTH || cardNumber.length > MAX_CARD_LENGTH) {
    return null;
  }

  let expiry;
  try {
    expiry = buildExpiry(rawMonth, rawYear);
  } catch (error) {
    return null;
  }

  const cardType = resolveCardType(cardNumber);
  let cvv = '';

  try {
    cvv = rawCvv ? normalizeCvv(rawCvv, cardType) : generateCvv(cardType);
  } catch (error) {
    return null;
  }

  return {
    number: cardNumber,
    month: expiry.month,
    year: expiry.year,
    yearShort: expiry.yearShort,
    cvv,
    expiry,
    type: cardType ? cardType.name : 'Unknown',
    cardType: cardType ? cardType.type : '',
    isValid: validateLuhn(cardNumber)
  };
}

/**
 * Get BIN from full card number
 * @param {string} cardNumber - Full card number
 * @returns {string} BIN (first 6 digits)
 */
function extractBIN(cardNumber) {
  return sanitizeDigits(cardNumber).substring(0, 6);
}

/**
 * Generate random BIN for card type
 * @param {string} cardType - Card type (VISA, MASTERCARD, etc.)
 * @returns {string} Random valid BIN
 */
function generateRandomBIN(cardType = 'VISA') {
  const normalizedType = String(cardType || 'VISA').toUpperCase();

  if (!CARD_TYPES[normalizedType]) {
    throw new Error(`Unknown card type: ${cardType}`);
  }

  if (normalizedType === 'VISA') {
    return `4${randomDigits(5)}`;
  }

  if (normalizedType === 'MASTERCARD') {
    if (Math.random() < 0.5) {
      return `5${Math.floor(Math.random() * 5) + 1}${randomDigits(4)}`;
    }

    return `2${Math.floor(Math.random() * 6) + 2}${randomDigits(4)}`;
  }

  if (normalizedType === 'AMEX') {
    return `3${Math.random() < 0.5 ? '4' : '7'}${randomDigits(4)}`;
  }

  if (normalizedType === 'DISCOVER') {
    return `6011${randomDigits(2)}`;
  }

  if (normalizedType === 'UNIONPAY') {
    return `62${randomDigits(4)}`;
  }

  if (normalizedType === 'JCB') {
    return `35${randomDigits(4)}`;
  }

  return `30${randomDigits(4)}`;
}

const exportedApi = {
  detectCardType,
  calculateLuhnCheckDigit,
  validateLuhn,
  generateCardFromBIN,
  generateMultipleCards,
  generateFullCard,
  generateMultipleCardDetails,
  formatCardNumber,
  parseCardData,
  extractBIN,
  generateRandomBIN,
  buildExpiry,
  CARD_TYPES
};

// Export functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = exportedApi;
}

// Browser/Extension context
if (typeof window !== 'undefined') {
  window.CardGenerator = exportedApi;
}

// Service Worker context
if (typeof self !== 'undefined' && typeof window === 'undefined') {
  self.CardGenerator = exportedApi;
}
