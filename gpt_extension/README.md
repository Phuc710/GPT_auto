# Auto Fill GPT - Payment Form Filler Extension

## Version 1.0.0

Chrome extension for generating valid test card numbers from a BIN and filling payment forms with card, address, and contact data.

## Features

### BIN generator
- Generate mathematically valid card numbers with the Luhn algorithm
- Detect Visa, Mastercard, Amex, Discover, UnionPay, JCB, and Diners Club from BIN
- Support 13-19 digit card lengths
- Generate 1-100 cards per batch
- Optional month, year, and CVV overrides
- Blank CVV means random CVV
- Random month and year when left on `Random`

### Auto fill workflow
- `Fill Form` auto-generates a fresh card when a BIN is present
- Clicking a generated card locks that exact card for reuse
- Repeated `Fill Form` clicks generate new cards again when no generated card is selected
- Manual card data is still supported with `card|month|year|cvv`

### Address generation
- Random United States addresses
- Random South Korea addresses
- Random name, email, and phone number
- Optional preferred state or province

## Usage

### Quick start
1. Open the extension popup.
2. Enter a BIN such as `625814` or `411111`.
3. Leave `Month`, `Year`, or `CVV` blank/random unless you need fixed values.
4. Click `Fill Form` to generate a card and fill the current page immediately.

### Preview multiple cards
1. Enter BIN and optional overrides.
2. Set `Quantity`.
3. Click `Generate Cards`.
4. Click any generated card to reuse that exact number, expiry, and CVV.
5. Click `Fill Form`.

### Manual card data
- Format: `6258142389673407|06|2033|656`
- CVV is optional, but including it preserves the exact value you want filled

## Common test BINs

| Type | BIN |
|------|-----|
| UnionPay | `625814` |
| Visa | `411111` |
| Mastercard | `555555` |
| Amex | `340000` |
| Discover | `601100` |

## Supported card types

| Type | BIN pattern | Default lengths | CVV |
|------|-------------|-----------------|-----|
| Visa | `4` | `13, 16, 19` | `3` |
| Mastercard | `51-55`, `22-27` | `16` | `3` |
| Amex | `34`, `37` | `15` | `4` |
| Discover | `6011`, `65`, `644-649`, `622` | `16` | `3` |
| UnionPay | `62` | `16-19` | `3` |
| JCB | `35` | `16` | `3` |
| Diners Club | `30`, `36`, `38`, `39` | `14` | `3` |

## Files

- `manifest.json`: extension manifest
- `popup.html`: popup markup
- `popup.css`: popup styling
- `popup.js`: popup behavior
- `cardGenerator.js`: BIN, Luhn, expiry, and CVV generation
- `content.js`: page form filling
- `dataGenerator.js`: address and personal data generation

## Notes

- Generated cards are valid against Luhn only.
- They are for testing flows, not real payments.
- All data is generated locally in the extension.
