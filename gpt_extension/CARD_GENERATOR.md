# 🎴 Card Generator Feature - Version 1.0.0

## Overview

The Auto Fill GPT extension now includes a powerful BIN-based card generator that creates valid card numbers using the Luhn algorithm. This feature allows you to generate test card numbers on the fly without needing external tools.

## What is BIN?

**BIN (Bank Identification Number)** is the first 6-12 digits of a payment card number that identifies:
- The card issuer (bank)
- Card type (Visa, Mastercard, etc.)
- Card category (debit, credit, prepaid)

## Features

### ✨ Key Capabilities

1. **Luhn Algorithm Validation**
   - All generated cards pass Luhn check
   - Industry-standard validation
   - Mathematically valid card numbers

2. **Card Type Detection**
   - Auto-detects from BIN:
     - Visa (starts with 4)
     - Mastercard (starts with 51-55 or 22-27)
     - American Express (starts with 34 or 37)
     - Discover (starts with 6011, 65, 644-649, 622)
     - UnionPay (starts with 62)
     - JCB (starts with 35)
     - Diners Club (starts with 30, 36, 38, 39)

3. **Flexible Generation**
   - Generate 1-100 cards at once
   - Custom card length (13-19 digits)
   - Auto-generated expiry dates
   - Auto-generated CVV codes

4. **One-Click Use**
   - Click any generated card to use it
   - Automatically fills card data field
   - Ready to fill forms immediately

## How to Use

### Basic Usage

1. **Open Extension**
   - Click extension icon
   - You'll see "🎴 Card Generator" section

2. **Show Generator**
   - Click "Show" button
   - Generator panel expands

3. **Enter BIN**
   ```
   BIN Number: 625814
   ```
   - Extension auto-detects card type
   - Sets appropriate length

4. **Generate**
   - Click "Generate Cards"
   - Cards appear below
   - Click any card to use it

### Advanced Usage

**Generate Multiple Cards**:
```
BIN: 625814
Quantity: 10
Length: Auto
```

**Custom Length**:
```
BIN: 4111
Quantity: 5
Length: 16 digits
```

**Specific Card Type**:
```
BIN: 62
Card Type: UnionPay
Quantity: 1
Length: Auto
```

## Example BINs

### Visa
```
411111  → Visa Classic
450000  → Visa Gold
```

### Mastercard
```
555555  → Mastercard
222100  → Mastercard (new range)
```

### UnionPay
```
625814  → UnionPay (your example)
621234  → UnionPay
```

### American Express
```
340000  → Amex
370000  → Amex
```

### Discover
```
601100  → Discover
650000  → Discover
```

## Generated Card Format

Each generated card includes:

```
Card Number: 6258 1423 8967 3407
Expiry: 06/33
CVV: 656
Type: UnionPay
Valid: ✓
```

## Using Generated Cards

### Method 1: Click to Use

1. Generate cards
2. Click on any card in the list
3. Card data automatically fills input field
4. Format: `6258142389673407|06|33`
5. Click "Fill Form" to use

### Method 2: Manual Copy

1. Generated cards show all details
2. Copy card number, expiry, CVV
3. Paste into card data field
4. Use as normal

## Technical Details

### Luhn Algorithm

The generator uses the Luhn algorithm (mod 10) to ensure all cards are mathematically valid:

```
1. Double every second digit from right
2. If result > 9, subtract 9
3. Sum all digits
4. Check digit makes sum divisible by 10
```

Example for BIN `625814`:
```
BIN: 625814
Middle digits: 238967340 (random)
Without check: 625814238967340
Luhn check digit: 7
Final card: 6258142389673407 ✓
```

### Card Type Detection

**Patterns**:
```javascript
Visa: /^4/
Mastercard: /^5[1-5]/ or /^2[2-7]/
Amex: /^3[47]/
Discover: /^6011/ or /^65/ or /^64[4-9]/ or /^622/
UnionPay: /^62/
JCB: /^35/
```

### Expiry Generation

```
Current date + 1-5 years
Random month: 01-12
Format: MM/YY
```

### CVV Generation

```
Visa/MC/Discover: 3 digits (000-999)
Amex: 4 digits (0000-9999)
```

## Best Practices

### Testing Workflow

1. **Generate Once, Use Multiple Times**
   ```
   Generate: 10 cards
   Use: Select different cards for different tests
   ```

2. **BIN Consistency**
   ```
   Same BIN → Same issuer/type
   Different BIN → Test various card types
   ```

3. **Expiry Dates**
   ```
   Auto-generated: Always future dates
   Valid for: 1-5 years
   ```

### Common BINs for Testing

**High Success Rate BINs**:
```
625814  → UnionPay (your example)
411111  → Visa test
555555  → Mastercard test
601100  → Discover test
340000  → Amex test
```

## Integration with Form Filler

### Full Workflow

1. **Generate Card**
   - Enter BIN: `625814`
   - Click Generate
   - Click on generated card

2. **Configure Address**
   - Country: South Korea
   - Province: Busan

3. **Fill Form**
   - Click "Fill Form"
   - All fields auto-filled
   - Card + Address + CVV

### Quick Workflow

1. **After First Fill**
   - Click Refresh 🔄
   - Page reloads

2. **Generate New Card**
   - Generate different card
   - Click to select

3. **Quick Fill**
   - Click "Fill Form"
   - Only card fields filled

## Troubleshooting

### BIN Not Detected

**Problem**: Card type shows "Auto-detect"

**Solution**:
- BIN must be at least 2 digits
- Enter 6+ digits for best detection
- Manually select card type if needed

### Invalid Cards Generated

**Problem**: Cards fail validation

**Solution**:
- This should never happen (Luhn validated)
- Check console for errors
- Reload extension
- Report bug if persists

### Generation Fails

**Problem**: "Error generating cards"

**Solution**:
- Check BIN length (6-12 digits)
- Reduce quantity if too high
- Clear BIN and try again
- Check browser console

## FAQs

### Q: Are these real cards?
**A**: No! These are mathematically valid but not linked to any bank account. For testing only.

### Q: Will these cards work for actual purchases?
**A**: No! They pass Luhn validation but won't work with real payment processors.

### Q: How many cards can I generate?
**A**: 1-100 per generation. Generate more by clicking again.

### Q: Can I save generated cards?
**A**: Currently no, but you can copy them manually. Saved cards feature coming soon.

### Q: What's the best BIN to use?
**A**: Use `625814` for UnionPay or `411111` for Visa. Both work well.

### Q: Can I generate specific card numbers?
**A**: No, numbers are random (except BIN prefix). This ensures uniqueness.

## Advanced Tips

### Batch Testing

```javascript
// Generate 10 cards
BIN: 625814
Quantity: 10

// Test each card:
Card 1: 6258142389673407|06|33
Card 2: 6258142389671195|04|26
Card 3: 6258142389677556|09|33
... etc
```

### Different Issuers

```javascript
// Test multiple card types
UnionPay: 625814
Visa: 411111
Mastercard: 555555
Amex: 340000
```

### Expiry Variations

```javascript
// Cards have random expiry dates
Card 1: 06/33 (2033)
Card 2: 04/26 (2026)  
Card 3: 09/33 (2033)
```

## Keyboard Shortcuts (Coming Soon)

```
Ctrl+G: Toggle generator
Ctrl+Enter: Generate cards
Ctrl+1-9: Select card 1-9
```

## API Reference

### Card Generator Functions

```javascript
// Detect card type
CardGenerator.detectCardType('625814')

// Generate single card
CardGenerator.generateFullCard('625814')

// Generate multiple
CardGenerator.generateMultipleCards('625814', 10)

// Validate card
CardGenerator.validateLuhn('6258142389673407')
```

## Version History

### v1.2.0 (Current)
- ✅ BIN-based card generator
- ✅ Luhn algorithm validation
- ✅ Multi-card generation
- ✅ One-click card selection
- ✅ Auto card type detection

### Coming in v1.3.0
- Save generated cards
- Export cards to file
- Import BIN lists
- Keyboard shortcuts
- Card history

## Support

**Issues?**
1. Check BIN is valid (6+ digits)
2. Try different BIN
3. Reload extension
4. Check browser console
5. Report bug with details

**Need Help?**
- Read this guide
- Check QUICK_START.md
- Try example BINs
- Contact support

---

**Version**: 1.2.0  
**Feature**: BIN Card Generator  
**Algorithm**: Luhn (mod 10)  
**Status**: Production Ready

Remember: **Always use for testing only!** Never use real payment cards! ⚠️
