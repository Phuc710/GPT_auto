2. 💳 Card Number  
3. 📅 Expiry
4. 🔒 CVV
5. 👤 Name
6. 🏠 Address Line 1 → Line 2 → City → State → Postal
Vấn đề cốt lõi: Card fields (#payment-numberInput, #payment-expiryInput, #payment-cvcInput) nằm trong Stripe iframe (b.stripecdn.com) — đây là cross-origin, top frame KHÔNG THỂ truy cập được DOM của nó.

Cách hoạt động mới (sạch, không spam):
Frame	Nhiệm vụ	Log
chatgpt.com (Top)	Fill Address: Name, City, State, Postal	✅ Log
b.stripecdn.com (Stripe)	Fill Card: Number, Expiry, CVV	✅ Log
hcaptcha, js.stripe.com, m.stripe.network...	Im lặng exit — không có fields	❌ Không log

 2 iframe riêng biệt:

elements-inner-payment-*.html → Card (number, expiry, CVV)
elements-inner-address-*.html → Billing Address (Name, City, State, Postal)
Log chứng minh:

Card fill → js.stripe.com ✅
Address fill → chatgpt.com ❌ (NOT in top frame!)
Address iframe nhận message nhưng exit sớm vì không có card fields → không bao giờ fill address!