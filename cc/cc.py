import logging
import random
import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
MAIN_MENU, BIN_INPUT, EXPIRE_INPUT, AMOUNT_INPUT, COUNTRY_INPUT, BIN_LOOKUP_INPUT = range(6)

# Country data for fake addresses
COUNTRY_DATA = {
    "usa": {
        "names": ["James Smith", "Maria Garcia", "Robert Johnson", "Jennifer Lee", "Michael Brown"],
        "streets": ["Maple Street", "Oak Avenue", "Pine Road", "Cedar Lane", "Elm Drive"],
        "cities": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
        "states": ["NY", "CA", "IL", "TX", "AZ"],
        "zip_format": "#####",
        "phone_format": "+1-###-###-####",
        "iban_prefix": "US"
    },
    "uk": {
        "names": ["William Taylor", "Olivia Wilson", "Thomas Clark", "Sophie Evans", "Daniel Harris"],
        "streets": ["High Street", "London Road", "Church Lane", "Park Avenue", "Victoria Street"],
        "cities": ["London", "Manchester", "Birmingham", "Liverpool", "Leeds"],
        "states": ["England", "Scotland", "Wales", "Northern Ireland"],
        "zip_format": "??# #??",
        "phone_format": "+44-####-######",
        "iban_prefix": "GB"
    },
    "canada": {
        "names": ["David Martin", "Emma Thompson", "Christopher White", "Sarah Wilson", "Matthew Scott"],
        "streets": ["Queen Street", "King Road", "Main Street", "First Avenue", "River Road"],
        "cities": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa"],
        "states": ["ON", "BC", "QC", "AB", "NS"],
        "zip_format": "?#? #?#",
        "phone_format": "+1-###-###-####",
        "iban_prefix": "CA"
    },
    "australia": {
        "names": ["John Walker", "Emily Robinson", "Paul Mitchell", "Jessica Hall", "Andrew Young"],
        "streets": ["George Street", "Victoria Road", "Pacific Highway", "Elizabeth Street", "King Street"],
        "cities": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
        "states": ["NSW", "VIC", "QLD", "WA", "SA"],
        "zip_format": "####",
        "phone_format": "+61-#-####-####",
        "iban_prefix": "AU"
    },
    "germany": {
        "names": ["Hans Müller", "Anna Schmidt", "Peter Fischer", "Julia Weber", "Thomas Meyer"],
        "streets": ["Hauptstraße", "Bahnhofstraße", "Kirchweg", "Dorfstraße", "Bergstraße"],
        "cities": ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt"],
        "states": ["Berlin", "Hamburg", "Bavaria", "North Rhine", "Hesse"],
        "zip_format": "#####",
        "phone_format": "+49-###-########",
        "iban_prefix": "DE"
    },
    "india": {
        "names": ["Raj Sharma", "Priya Patel", "Amit Kumar", "Neha Singh", "Vikram Reddy"],
        "streets": ["MG Road", "Church Street", "Bazaar Street", "Temple Road", "Gandhi Nagar"],
        "cities": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai"],
        "states": ["Maharashtra", "Delhi", "Karnataka", "Telangana", "Tamil Nadu"],
        "zip_format": "######",
        "phone_format": "+91-####-######",
        "iban_prefix": "IN"
    }
}

# BIN Database for lookup
BIN_DATABASE = {
    "4": {"type": "Visa", "category": "Credit/Debit", "country": "US"},
    "5": {"type": "Mastercard", "category": "Credit/Debit", "country": "US"},
    "3": {"type": "American Express", "category": "Credit", "country": "US"},
    "6": {"type": "Discover", "category": "Credit", "country": "US"},
    "35": {"type": "JCB", "category": "Credit", "country": "JP"},
    "37": {"type": "American Express", "category": "Credit", "country": "US"},
}

# Common BINs
COMMON_BINS = {
    "411111": {"bank": "Visa Test", "type": "Visa", "country": "US", "level": "Classic"},
    "511111": {"bank": "Mastercard Test", "type": "Mastercard", "country": "US", "level": "Gold"},
    "371449": {"bank": "American Express", "type": "Amex", "country": "US", "level": "Platinum"},
    "601100": {"bank": "Discover", "type": "Discover", "country": "US", "level": "Standard"},
    "510931": {"bank": "Bank of America", "type": "Mastercard", "country": "US", "level": "Gold"},
    "453211": {"bank": "Chase Bank", "type": "Visa", "country": "US", "level": "Platinum"},
    "524137": {"bank": "Citibank", "type": "Mastercard", "country": "US", "level": "World"},
    "492942": {"bank": "Wells Fargo", "type": "Visa", "country": "US", "level": "Signature"},
    "546616": {"bank": "HSBC", "type": "Mastercard", "country": "UK", "level": "Premier"},
    "400344": {"bank": "Deutsche Bank", "type": "Visa", "country": "DE", "level": "Business"},
}

class AdvancedCCBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup all handlers"""
        # Main conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start_command)],
            states={
                MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.main_menu_handler)],
                BIN_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.bin_input_handler)],
                EXPIRE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.expire_input_handler)],
                AMOUNT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.amount_input_handler)],
                COUNTRY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.country_input_handler)],
                BIN_LOOKUP_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.bin_lookup_handler)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_command)],
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("address", self.address_command))
        self.application.add_handler(CommandHandler("binlookup", self.binlookup_command))
        self.application.add_handler(CommandHandler("gen", self.quick_gen_command))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Send main menu"""
        welcome_text = """
🤖 **ADVANCED CC GENERATOR BOT** 🤖

📌 **MAIN MENU - Choose Option:**

1️⃣ **Generate CCs** - Type `1`
2️⃣ **BIN Lookup** - Type `2`
3️⃣ **Fake Address Generator** - Type `3`
4️⃣ **Quick Generate** - Type `4`

📌 **Quick Commands:**
/start - Show this menu
/gen BIN EXPIRY AMOUNT - Quick generate
/address - Fake address generator
/binlookup - Check BIN details
/help - Help & instructions

🔗 **Contact:** @Leakhunter00

📝 **Type your choice (1, 2, 3, or 4):**
        """
        
        await update.message.reply_text(welcome_text)
        return MAIN_MENU
    
    async def main_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle main menu choice"""
        choice = update.message.text.strip()
        
        if choice == '1':
            await update.message.reply_text("🔢 **Enter BIN (6-8 digits):**\n\n📌 **Popular BINs:**\n• 411111 (Visa)\n• 511111 (Mastercard)\n• 371449 (Amex)\n• 601100 (Discover)")
            return BIN_INPUT
            
        elif choice == '2':
            await update.message.reply_text("🔍 **BIN Lookup**\n\nEnter BIN to check (6 digits):\n\n📌 **Examples:**\n• 411111\n• 511111\n• 371449")
            return BIN_LOOKUP_INPUT
            
        elif choice == '3':
            keyboard = [
                [
                    InlineKeyboardButton("🇺🇸 USA", callback_data="country_usa"),
                    InlineKeyboardButton("🇬🇧 UK", callback_data="country_uk"),
                ],
                [
                    InlineKeyboardButton("🇨🇦 Canada", callback_data="country_canada"),
                    InlineKeyboardButton("🇦🇺 Australia", callback_data="country_australia"),
                ],
                [
                    InlineKeyboardButton("🇩🇪 Germany", callback_data="country_germany"),
                    InlineKeyboardButton("🇮🇳 India", callback_data="country_india"),
                ],
                [
                    InlineKeyboardButton("🎲 Random", callback_data="country_random"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🌍 **Select country for fake address:**", reply_markup=reply_markup)
            return ConversationHandler.END
            
        elif choice == '4':
            await update.message.reply_text("🚀 **Quick Generation**\n\nUsage: `/gen BIN EXPIRY AMOUNT`\n\nExample: `/gen 411111 12/25 10`")
            return ConversationHandler.END
            
        else:
            await update.message.reply_text("❌ Invalid choice! Please type:\n1️⃣ `1` - CC Generator\n2️⃣ `2` - BIN Lookup\n3️⃣ `3` - Fake Address\n4️⃣ `4` - Quick Generate")
            return MAIN_MENU
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("country_"):
            country = data.split("_")[1]
            if country == "random":
                country = random.choice(list(COUNTRY_DATA.keys()))
            
            # Generate address
            address = self.generate_fake_address(country)
            
            # Format response
            response = f"""
📍 **FAKE ADDRESS - {country.upper()}**

👤 **Name:** {address['name']}
🏠 **Address:** {address['address']}
🏙️ **City:** {address['city']}
🗺️ **State:** {address['state']}
📮 **ZIP:** {address['zip']}
📱 **Phone:** {address['phone']}
🏦 **IBAN:** {address['iban']}
💰 **Account:** {address['account']}
🆔 **SSN:** {address['ssn']}

📧 **Email:** {address['email']}
🎂 **DOB:** {address['dob']}
💼 **Occupation:** {address['occupation']}

🔗 @Leakhunter00
            """
            
            await query.message.reply_text(response)
            
            # Ask for more
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Another Address", callback_data="country_random"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Generate another address?", reply_markup=reply_markup)
            
        elif data == "main_menu":
            await self.start_command(update, context)
    
    async def bin_input_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle BIN input"""
        bin_input = update.message.text.strip()
        
        # Clean input
        bin_input = bin_input.replace(" ", "").replace("-", "")
        
        # Validate
        if not bin_input.isdigit() or len(bin_input) < 6 or len(bin_input) > 8:
            await update.message.reply_text("❌ Invalid BIN! Must be 6-8 digits\n\n🔢 **Enter valid BIN:**")
            return BIN_INPUT
        
        # Store
        context.user_data['bin'] = bin_input
        
        # Show BIN info
        bin_info = self.lookup_bin(bin_input[:6])
        if bin_info:
            info_msg = f"""
✅ **BIN Detected:**
🏦 Bank: {bin_info.get('bank', 'Unknown')}
💳 Type: {bin_info.get('type', 'Unknown')}
🌍 Country: {bin_info.get('country', 'Unknown')}
📈 Level: {bin_info.get('level', 'Standard')}
            """
            await update.message.reply_text(info_msg)
        
        await update.message.reply_text("📅 **Enter expiry date (MM/YY):**\n*Example: 10/32*")
        return EXPIRE_INPUT
    
    async def expire_input_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle expiry input"""
        expire = update.message.text.strip()
        
        # Validate
        month, year = self.validate_expiry(expire)
        if not month:
            await update.message.reply_text("❌ Invalid format! Use MM/YY\n\n📅 **Enter expiry:**")
            return EXPIRE_INPUT
        
        # Store
        context.user_data['month'] = month
        context.user_data['year'] = year
        context.user_data['expire'] = expire
        
        await update.message.reply_text("🔢 **How many CCs to generate? (1-100):**")
        return AMOUNT_INPUT
    
    async def amount_input_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Generate and send CCs"""
        try:
            amount = int(update.message.text.strip())
            
            if amount < 1 or amount > 100:
                await update.message.reply_text("❌ Amount must be 1-100!\n\n🔢 **Enter number:**")
                return AMOUNT_INPUT
            
            # Get data
            bin_num = context.user_data['bin']
            month = context.user_data['month']
            year = context.user_data['year']
            
            # Generate
            await update.message.reply_text(f"⚡ Generating {amount} CCs...")
            cc_list = self.generate_ccs(bin_num, month, year, amount)
            
            # Create file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cc_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write(cc_list)
            
            # Send file
            caption = f"""
✅ **{amount} CCs Generated!**

📊 **Details:**
• BIN: `{bin_num}`
• Expiry: {context.user_data['expire']}
• Format: card|month|year|cvv
• Count: {amount}

📁 File auto-deletes
🔗 @Leakhunter00
            """
            
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    caption=caption.strip(),
                    filename=filename
                )
            
            # Delete file
            os.remove(filename)
            
            # Show sample
            sample = cc_list.split('\n')[:3]
            await update.message.reply_text(f"📄 **Sample:**\n```\n" + "\n".join(sample) + "\n```", parse_mode='Markdown')
            
            await update.message.reply_text("🔄 Generate more? Send /start")
            
        except ValueError:
            await update.message.reply_text("❌ Enter a valid number!\n\n🔢 **How many CCs?**")
            return AMOUNT_INPUT
        
        return ConversationHandler.END
    
    async def country_input_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle country input for address"""
        country = update.message.text.strip().lower()
        
        # Map aliases
        country_map = {
            "usa": "usa", "us": "usa", "united states": "usa",
            "uk": "uk", "united kingdom": "uk", "england": "uk",
            "canada": "canada", "ca": "canada",
            "australia": "australia", "au": "australia",
            "germany": "germany", "de": "germany",
            "india": "india", "in": "india"
        }
        
        country_key = country_map.get(country, country)
        
        if country_key not in COUNTRY_DATA:
            countries = "\n".join([f"• {c.title()}" for c in COUNTRY_DATA.keys()])
            await update.message.reply_text(f"❌ Country not supported!\n\n🌍 **Supported:**\n{countries}\n\n**Enter country:**")
            return COUNTRY_INPUT
        
        # Generate address
        address = self.generate_fake_address(country_key)
        
        response = f"""
📍 **FAKE ADDRESS - {country_key.upper()}**

👤 **Name:** {address['name']}
🏠 **Address:** {address['address']}
🏙️ **City:** {address['city']}
🗺️ **State:** {address['state']}
📮 **ZIP:** {address['zip']}
📱 **Phone:** {address['phone']}
🏦 **IBAN:** {address['iban']}
💰 **Account:** {address['account']}
🆔 **SSN:** {address['ssn']}

📧 **Email:** {address['email']}
🎂 **DOB:** {address['dob']}
💼 **Occupation:** {address['occupation']}

🔗 @Leakhunter00
        """
        
        await update.message.reply_text(response)
        await update.message.reply_text("🔄 Generate another? Send /address")
        
        return ConversationHandler.END
    
    async def bin_lookup_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle BIN lookup"""
        bin_input = update.message.text.strip()
        
        if not bin_input.isdigit() or len(bin_input) < 6:
            await update.message.reply_text("❌ Invalid BIN! Must be at least 6 digits\n\n🔍 **Enter BIN:**")
            return BIN_LOOKUP_INPUT
        
        # Lookup
        bin_info = self.lookup_bin(bin_input[:6])
        
        if bin_info:
            response = f"""
🔍 **BIN LOOKUP RESULTS**

📊 **BIN:** `{bin_input}`
🏦 **Bank:** {bin_info.get('bank', 'Unknown')}
💳 **Type:** {bin_info.get('type', 'Unknown')}
🌍 **Country:** {bin_info.get('country', 'Unknown')} {self.get_flag(bin_info.get('country'))}
📈 **Level:** {bin_info.get('level', 'Standard')}
🏷️ **Category:** {bin_info.get('category', 'Credit/Debit')}

✅ **Valid BIN Detected**
🔄 **Check another?** Send /binlookup
            """
        else:
            # Basic info from first digit
            first_digit = bin_input[0]
            basic_info = BIN_DATABASE.get(first_digit, {})
            
            response = f"""
🔍 **BIN LOOKUP RESULTS**

📊 **BIN:** `{bin_input}`
🏦 **Bank:** Not in database
💳 **Type:** {basic_info.get('type', 'Unknown')}
🌍 **Country:** {basic_info.get('country', 'Unknown')}
📈 **Level:** Unknown

📌 **Based on first digit ({first_digit}):**
• Type: {basic_info.get('type', 'Unknown')}
• Category: {basic_info.get('category', 'Unknown')}

⚠️ **Not in local database**
🔄 **Check another?** Send /binlookup
            """
        
        await update.message.reply_text(response)
        await update.message.reply_text("📊 **Options:**\n🔍 /binlookup - Check BIN\n💳 /start - Generate CCs\n📍 /address - Fake Address")
        
        return ConversationHandler.END
    
    async def address_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /address command"""
        keyboard = [
            [
                InlineKeyboardButton("🇺🇸 USA", callback_data="country_usa"),
                InlineKeyboardButton("🇬🇧 UK", callback_data="country_uk"),
            ],
            [
                InlineKeyboardButton("🇨🇦 Canada", callback_data="country_canada"),
                InlineKeyboardButton("🇦🇺 Australia", callback_data="country_australia"),
            ],
            [
                InlineKeyboardButton("🇩🇪 Germany", callback_data="country_germany"),
                InlineKeyboardButton("🇮🇳 India", callback_data="country_india"),
            ],
            [
                InlineKeyboardButton("🎲 Random", callback_data="country_random"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🌍 **Select country for fake address:**", reply_markup=reply_markup)
    
    async def binlookup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /binlookup command"""
        await update.message.reply_text("🔍 **Enter BIN to lookup (6 digits):**")
        return BIN_LOOKUP_INPUT
    
    async def quick_gen_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quick generation"""
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(
                "🚀 **Quick Generation:**\n\n"
                "Usage: `/gen BIN EXPIRY AMOUNT`\n"
                "Example: `/gen 411111 12/25 10`\n\n"
                "This generates 10 Visa cards expiring 12/25"
            )
            return
        
        try:
            bin_num = context.args[0]
            expire = context.args[1]
            amount = int(context.args[2])
            
            # Validate
            if not bin_num.isdigit() or len(bin_num) < 6:
                await update.message.reply_text("❌ Invalid BIN! 6+ digits required")
                return
            
            month, year = self.validate_expiry(expire)
            if not month:
                await update.message.reply_text("❌ Invalid expiry! Use MM/YY")
                return
            
            if amount < 1 or amount > 50:
                await update.message.reply_text("❌ Amount must be 1-50")
                return
            
            # Generate
            await update.message.reply_text(f"⚡ Generating {amount} CCs...")
            cc_list = self.generate_ccs(bin_num, month, year, amount)
            
            # Save and send
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"quick_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write(cc_list)
            
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    caption=f"✅ {amount} CCs Generated\nBIN: {bin_num}\nExpiry: {expire}\n🔗 @Leakhunter00",
                    filename=filename
                )
            
            os.remove(filename)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: Use `/gen 411111 12/25 10`")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        help_text = """
🤖 **ADVANCED CC GENERATOR BOT**

📌 **FEATURES:**
✅ CC Generation with Luhn algorithm
✅ BIN Lookup (detect bank & type)
✅ Fake Address Generator (6 countries)
✅ Quick generation command

📌 **COMMANDS:**
/start - Main menu
/gen BIN EXPIRY AMOUNT - Quick generate
/address - Generate fake address
/binlookup - Check BIN details
/help - This message
/cancel - Cancel operation

📌 **EXAMPLES:**
• Send /start and choose option
• `/gen 411111 12/25 10` - Quick generate
• `/binlookup 511111` - Check BIN
• Send /address - Get fake address

📌 **COUNTRIES SUPPORTED:**
🇺🇸 USA, 🇬🇧 UK, 🇨🇦 Canada
🇦🇺 Australia, 🇩🇪 Germany, 🇮🇳 India

📌 **OUTPUT FORMAT:**
card_number|month|year|cvv
Example: 4111111111111111|12|25|123

🔗 **Contact:** @Leakhunter00
        """
        await update.message.reply_text(help_text)
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel command"""
        await update.message.reply_text("❌ Operation cancelled.\n\nSend /start to begin.")
        return ConversationHandler.END
    
    # Helper methods
    def generate_ccs(self, bin_num, month, year, amount):
        """Generate CCs with Luhn algorithm"""
        cc_list = []
        for _ in range(amount):
            # Generate remaining digits
            remaining = 16 - len(bin_num)
            if remaining > 1:
                random_part = ''.join(str(random.randint(0, 9)) for _ in range(remaining - 1))
            else:
                random_part = ""
            
            # Create base and calculate Luhn
            base = bin_num + random_part
            check = self.calculate_luhn(base)
            cc = base + str(check)
            
            # Add CVV and format
            cvv = str(random.randint(100, 999))
            cc_list.append(f"{cc}|{month}|{year}|{cvv}")
        
        return "\n".join(cc_list)
    
    def calculate_luhn(self, number):
        """Luhn algorithm"""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(number)
        odd = digits[-1::-2]
        even = digits[-2::-2]
        
        total = sum(odd)
        for d in even:
            total += sum(digits_of(d * 2))
        
        return (10 - (total % 10)) % 10
    
    def validate_expiry(self, date_str):
        """Validate MM/YY format"""
        try:
            if '/' not in date_str:
                return None, None
            
            month_str, year_str = date_str.split('/')
            
            if len(month_str) != 2 or len(year_str) != 2:
                return None, None
            
            month = int(month_str)
            year = int(year_str)
            
            if month < 1 or month > 12:
                return None, None
            
            if year < 0 or year > 99:
                return None, None
            
            return month_str, year_str
        except:
            return None, None
    
    def lookup_bin(self, bin_num):
        """Lookup BIN information"""
        # Check common BINs
        for prefix, info in COMMON_BINS.items():
            if bin_num.startswith(prefix):
                return info.copy()
        
        # Check first digits
        first_digit = bin_num[0]
        if first_digit in BIN_DATABASE:
            info = BIN_DATABASE[first_digit].copy()
            info['bank'] = self.guess_bank(bin_num)
            info['level'] = self.guess_level(bin_num)
            return info
        
        return None
    
    def guess_bank(self, bin_num):
        """Guess bank from BIN"""
        banks = {
            "4": ["Visa"],
            "51": ["Citibank", "Mastercard"],
            "52": ["Chase", "Mastercard"],
            "53": ["Bank of America", "Mastercard"],
            "54": ["HSBC", "Mastercard"],
            "55": ["Capital One", "Mastercard"],
            "34": ["American Express"],
            "37": ["American Express"],
            "6011": ["Discover"],
        }
        
        for prefix, bank_list in banks.items():
            if bin_num.startswith(prefix):
                return random.choice(bank_list)
        
        return "Unknown Bank"
    
    def guess_level(self, bin_num):
        """Guess card level"""
        levels = ["Classic", "Standard", "Gold", "Platinum", "Signature", "World"]
        hash_val = sum(int(d) for d in bin_num[:4])
        return levels[hash_val % len(levels)]
    
    def get_flag(self, country_code):
        """Get flag emoji"""
        flags = {
            "US": "🇺🇸", "GB": "🇬🇧", "CA": "🇨🇦", "AU": "🇦🇺",
            "DE": "🇩🇪", "IN": "🇮🇳", "JP": "🇯🇵", "FR": "🇫🇷"
        }
        return flags.get(country_code, "🏳️")
    
    def generate_fake_address(self, country):
        """Generate fake address"""
        data = COUNTRY_DATA[country]
        
        # Generate data
        name = random.choice(data["names"])
        street = f"{random.randint(1, 9999)} {random.choice(data['streets'])}"
        city = random.choice(data["cities"])
        state = random.choice(data["states"])
        
        # Generate formatted fields
        zip_code = self.generate_zip(data["zip_format"])
        phone = self.generate_phone(data["phone_format"])
        iban = f"{data['iban_prefix']}{random.randint(10, 99)} " + \
               f"{''.join(str(random.randint(0, 9)) for _ in range(8))} " + \
               f"{''.join(str(random.randint(0, 9)) for _ in range(10))}"
        
        account = ''.join(str(random.randint(0, 9)) for _ in range(12))
        ssn = self.generate_ssn(country)
        
        # Email from name
        name_parts = name.lower().split()
        if len(name_parts) >= 2:
            email = f"{name_parts[0]}.{name_parts[1]}{random.randint(1, 99)}"
        else:
            email = f"{name_parts[0]}{random.randint(100, 999)}"
        email += f"@{random.choice(['gmail.com', 'yahoo.com', 'outlook.com'])}"
        
        # DOB
        dob = f"{random.randint(1, 28):02d}/{random.randint(1, 12):02d}/{random.randint(1970, 2000)}"
        
        # Occupation
        occupations = ["Software Engineer", "Doctor", "Teacher", "Business Analyst", 
                      "Sales Manager", "Accountant", "Marketing Specialist"]
        
        return {
            'name': name,
            'address': street,
            'city': city,
            'state': state,
            'zip': zip_code,
            'phone': phone,
            'iban': iban,
            'account': account,
            'ssn': ssn,
            'email': email,
            'dob': dob,
            'occupation': random.choice(occupations)
        }
    
    def generate_zip(self, format_str):
        """Generate ZIP code"""
        result = ""
        for char in format_str:
            if char == '#':
                result += str(random.randint(0, 9))
            elif char == '?':
                result += chr(random.randint(65, 90))
            else:
                result += char
        return result
    
    def generate_phone(self, format_str):
        """Generate phone number"""
        result = ""
        for char in format_str:
            if char == '#':
                result += str(random.randint(0, 9))
            else:
                result += char
        return result
    
    def generate_ssn(self, country):
        """Generate SSN based on country"""
        if country == "usa":
            return f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
        elif country == "uk":
            return f"AB {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} C"
        elif country == "canada":
            return f"{random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)}"
        else:
            return f"{random.randint(100000000, 999999999)}"
    
    def run(self):
        """Run the bot"""
        logger.info("Starting Advanced CC Bot...")
        
        print("=" * 60)
        print("🤖 ADVANCED CC GENERATOR BOT")
        print("📞 Contact: @Leakhunter00")
        print("=" * 60)
        print("\nStarting bot...")
        
        self.application.run_polling(drop_pending_updates=True)

def main():
    """Main function"""
    print("\n" + "="*60)
    print("🚀 ADVANCED CC GENERATOR BOT")
    print("="*60)
    
    # YOUR BOT TOKEN
    TOKEN = "8219397613:AAGRuK3UoiwTZjLxfbBxDai1axGXiKKldVdhg"
    
    if not TOKEN or "YOUR" in TOKEN:
        print("❌ ERROR: Add your bot token!")
        print("\n💡 Get token from @BotFather")
        print("💡 Edit line 419: TOKEN = \"YOUR_TOKEN\"")
        return
    
    try:
        print(f"✅ Token: {TOKEN[:15]}...")
        print("🔄 Connecting...")
        
        bot = AdvancedCCBot(TOKEN)
        bot.run()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 Check internet & token")

if __name__ == '__main__':
    try:
        import telegram
        print(f"✅ python-telegram-bot: {telegram.__version__}")
    except:
        print("❌ Install: pip install python-telegram-bot")
        exit(1)
    
    main()