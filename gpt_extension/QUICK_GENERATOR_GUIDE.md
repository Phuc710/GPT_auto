# Quick BIN Generator Guide

## 30-second flow

1. Open the extension popup.
2. Enter a BIN, for example `625814`.
3. Leave `Month`, `Year`, and `CVV` blank if you want random values.
4. Click `Fill Form`.
5. The extension generates a valid Luhn card and fills the page immediately.

## Repeat fill quickly

- If a BIN is still present and no generated card is selected, every `Fill Form` click generates a fresh card.
- If you click a generated card from the list, `Fill Form` keeps reusing that exact card until you clear the selection.

## Preview multiple cards

1. Enter BIN.
2. Set `Quantity`.
3. Click `Generate Cards`.
4. Click any generated card to load it into the form filler.
5. Click `Fill Form`.![alt text]({DB98869F-BD13-4291-8153-F88BBE254B59}.png)

## Input rules

- `BIN`: 2-12 digits
- `Month`: `Random` or a fixed month
- `Year`: `Random` or a fixed year
- `CVV`: blank means random
- `Quantity`: 1-100

## Example setups

### Random UnionPay

```text
BIN: 625814
Month: Random
Year: Random
CVV: blank
Quantity: 10
```

### Fixed Visa month/year

```text
BIN: 411111
Month: 06
Year: 2033
CVV: blank
Quantity: 5
```

### Fixed CVV

```text
BIN: 555555
Month: Random
Year: Random
CVV: 123
Quantity: 1
```

## Manual card data

Use this format in `Card Data`:

```text
cardnumber|month|year|cvv
```

Example:

```text
6258142389673407|06|2033|656
```

## Common BINs

| Type | BIN |
|------|-----|
| UnionPay | `625814` |
| Visa | `411111` |
| Mastercard | `555555` |
| Amex | `340000` |
| Discover | `601100` |

## Notes

- Generated cards pass the Luhn check.
- Blank CVV is random.
- Repeated `Fill Form` clicks keep working without needing to pre-generate cards.
