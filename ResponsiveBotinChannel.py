import logging
import re
import threading
import asyncio
import requests
import datetime
from flask import Flask, request, jsonify
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
)
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters,
    ConversationHandler
)
import nest_asyncio
import urllib.parse

nest_asyncio.apply()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = '8020928937:AAElhu5BE995M1w9nvJQZSl3kY8R3SeU-PU'  # Replace with your token
ADMIN_CHAT_ID = 7428761789
BASE_URL = "https://f8c1-23-230-253-229.ngrok-free.app"  # Replace with your public URL
VERIFF_API_KEY = "b8220d29-5405-4fe5-8f31-a290132792fd"
CALENDLY_BASE_URL = "https://calendly.com/vonartis/30min"  # Replace with your Calendly event link

app = Flask(__name__)

# Conversation states
(SELECT_LANGUAGE, 
 SIGNUP_NAME, SIGNUP_EMAIL, SIGNUP_SERVICE,
 CONSULT_NAME, CONSULT_EMAIL, CONSULT_DATE, CONSULT_TOPIC,
 ASK_QUESTION,
 FAQ_Q) = range(10)

# Translation dictionaries
translations = {
    'en': {
        'welcome': "Welcome! Please select your language:",
        'menu': "Welcome! Tap below to explore our services:",
        'verify': "🛡️ Click the button below to start verification.",
        'verification_error': "❌ Verification error: {}",
        'signup_name': "Please enter your full name:",
        'signup_email': "Great! Now enter your email address:",
        'invalid_email': "Please enter a valid email address:",
        'signup_service': "Which service are you interested in?\nOptions: Investment, Trading, Consulting",
        'signup_summary': (
            "Signup info received:\n\n"
            "Name: {}\n"
            "Email: {}\n"
            "Service: {}\n\n"
            "Thank you! Our team will contact you soon."
        ),
        'consult_name': "Enter your full name for consultation:",
        'consult_email': "Enter your email address for consultation:",
        'consult_date': "Preferred date and time for consultation (e.g., 2023-12-01 14:00):",
        'consult_topic': "Briefly describe the topic or questions you want to discuss:",
        'consult_summary': (
            "Consultation request:\n\n"
            "Name: {}\n"
            "Email: {}\n"
            "Date: {}\n"
            "Topic: {}\n\n"
            "Thank you! We will get back to you soon."
        ),
        'ask_question': "Type your question below:",
        'question_thanks': "Thank you for your question! We will respond soon.",
        'cancel': "Operation cancelled.",
        'back_to_menu': "Welcome back! Tap below:",
        'faq': "FAQ",
        'website': "Website",
        'signup': "Sign Up",
        'verify_btn': "Become Verified",
        'consult': "Book Consultation",
        'ask_question_btn': "Ask a Question",
        'calendly': "Book Consultation via Calendly",
        'verify_now': "🔗 Verify Now",
        'previous': "⬅️ Previous Question",
        'next': "Next Question ➡️",
        'main_menu': "Back to Menu"
    },
    'es': {
        'welcome': "¡Bienvenido! Por favor seleccione su idioma:",
        'menu': "¡Bienvenido! Toque abajo para explorar nuestros servicios:",
        'verify': "🛡️ Haga clic en el botón a continuación para comenzar la verificación.",
        'verification_error': "❌ Error de verificación: {}",
        'signup_name': "Por favor ingrese su nombre completo:",
        'signup_email': "¡Genial! Ahora ingrese su dirección de correo electrónico:",
        'invalid_email': "Por favor ingrese una dirección de correo electrónico válida:",
        'signup_service': "¿Qué servicio le interesa?\nOpciones: Inversión, Trading, Consultoría",
        'signup_summary': (
            "Información de registro recibida:\n\n"
            "Nombre: {}\n"
            "Email: {}\n"
            "Servicio: {}\n\n"
            "¡Gracias! Nuestro equipo se pondrá en contacto con usted pronto."
        ),
        'consult_name': "Ingrese su nombre completo para la consulta:",
        'consult_email': "Ingrese su dirección de correo electrónico para la consulta:",
        'consult_date': "Fecha y hora preferida para la consulta (ejemplo: 2023-12-01 14:00):",
        'consult_topic': "Describa brevemente el tema o las preguntas que desea discutir:",
        'consult_summary': (
            "Solicitud de consulta:\n\n"
            "Nombre: {}\n"
            "Email: {}\n"
            "Fecha: {}\n"
            "Tema: {}\n\n"
            "¡Gracias! Nos pondremos en contacto con usted pronto."
        ),
        'ask_question': "Escriba su pregunta a continuación:",
        'question_thanks': "¡Gracias por su pregunta! Responderemos pronto.",
        'cancel': "Operación cancelada.",
        'back_to_menu': "¡Bienvenido de nuevo! Toque abajo:",
        'faq': "Preguntas Frecuentes",
        'website': "Sitio Web",
        'signup': "Registrarse",
        'verify_btn': "Verificarse",
        'consult': "Reservar Consulta",
        'ask_question_btn': "Hacer una Pregunta",
        'calendly': "Reservar Consulta via Calendly",
        'verify_now': "🔗 Verificar Ahora",
        'previous': "⬅️ Pregunta Anterior",
        'next': "Siguiente Pregunta ➡️",
        'main_menu': "Volver al Menú"
    },
    'ru': {
        'welcome': "Добро пожаловать! Пожалуйста, выберите язык:",
        'menu': "Добро пожаловать! Нажмите ниже, чтобы изучить наши услуги:",
        'verify': "🛡️ Нажмите кнопку ниже, чтобы начать проверку.",
        'verification_error': "❌ Ошибка проверки: {}",
        'signup_name': "Пожалуйста, введите ваше полное имя:",
        'signup_email': "Отлично! Теперь введите ваш адрес электронной почты:",
        'invalid_email': "Пожалуйста, введите действительный адрес электронной почты:",
        'signup_service': "Какая услуга вас интересует?\nВарианты: Инвестиции, Трейдинг, Консультации",
        'signup_summary': (
            "Получена информация о регистрации:\n\n"
            "Имя: {}\n"
            "Email: {}\n"
            "Услуга: {}\n\n"
            "Спасибо! Наша команда свяжется с вами в ближайшее время."
        ),
        'consult_name': "Введите ваше полное имя для консультации:",
        'consult_email': "Введите ваш адрес электронной почты для консультации:",
        'consult_date': "Предпочтительная дата и время консультации (например, 2023-12-01 14:00):",
        'consult_topic': "Кратко опишите тему или вопросы, которые вы хотите обсудить:",
        'consult_summary': (
            "Запрос на консультацию:\n\n"
            "Имя: {}\n"
            "Email: {}\n"
            "Дата: {}\n"
            "Тема: {}\n\n"
            "Спасибо! Мы свяжемся с вами в ближайшее время."
        ),
        'ask_question': "Введите ваш вопрос ниже:",
        'question_thanks': "Спасибо за ваш вопрос! Мы ответим в ближайшее время.",
        'cancel': "Операция отменена.",
        'back_to_menu': "С возвращением! Нажмите ниже:",
        'faq': "ЧаВо",
        'website': "Веб-сайт",
        'signup': "Регистрация",
        'verify_btn': "Верификация",
        'consult': "Забронировать Консультацию",
        'ask_question_btn': "Задать Вопрос",
        'calendly': "Забронировать Консультацию через Calendly",
        'verify_now': "🔗 Пройти Верификацию",
        'previous': "⬅️ Предыдущий Вопрос",
        'next': "Следующий Вопрос ➡️",
        'main_menu': "Вернуться в Меню"
    },
    'ar': {
        'welcome': "مرحبًا! الرجاء اختيار لغتك:",
        'menu': "مرحبًا! اضغط أدناه لاستكشاف خدماتنا:",
        'verify': "🛡️ انقر فوق الزر أدناه لبدء التحقق.",
        'verification_error': "❌ خطأ في التحقق: {}",
        'signup_name': "الرجاء إدخال اسمك الكامل:",
        'signup_email': "عظيم! الآن أدخل عنوان بريدك الإلكتروني:",
        'invalid_email': "الرجاء إدخال عنوان بريد إلكتروني صالح:",
        'signup_service': "ما الخدمة التي تهتم بها؟\nالخيارات: استثمار، تداول، استشارة",
        'signup_summary': (
            "تم استلام معلومات التسجيل:\n\n"
            "الاسم: {}\n"
            "البريد الإلكتروني: {}\n"
            "الخدمة: {}\n\n"
            "شكرًا لك! سيتواصل معك فريقنا قريبًا."
        ),
        'consult_name': "أدخل اسمك الكامل للاستشارة:",
        'consult_email': "أدخل عنوان بريدك الإلكتروني للاستشارة:",
        'consult_date': "التاريخ والوقت المفضلان للاستشارة (مثال: 2023-12-01 14:00):",
        'consult_topic': "صف بإيجاز الموضوع أو الأسئلة التي تريد مناقشتها:",
        'consult_summary': (
            "طلب استشارة:\n\n"
            "الاسم: {}\n"
            "البريد الإلكتروني: {}\n"
            "التاريخ: {}\n"
            "الموضوع: {}\n\n"
            "شكرًا لك! سنتواصل معك قريبًا."
        ),
        'ask_question': "اكتب سؤالك أدناه:",
        'question_thanks': "شكرًا لك على سؤالك! سنجيب قريبًا.",
        'cancel': "تم إلغاء العملية.",
        'back_to_menu': "مرحبًا بعودتك! اضغط أدناه:",
        'faq': "الأسئلة الشائعة",
        'website': "الموقع الإلكتروني",
        'signup': "التسجيل",
        'verify_btn': "التحقق",
        'consult': "حجز استشارة",
        'ask_question_btn': "طرح سؤال",
        'calendly': "حجز استشارة عبر Calendly",
        'verify_now': "🔗 التحقق الآن",
        'previous': "⬅️ السؤال السابق",
        'next': "السؤال التالي ➡️",
        'main_menu': "العودة إلى القائمة"
    },
    'zh': {
        'welcome': "欢迎！请选择您的语言：",
        'menu': "欢迎！点击下方探索我们的服务：",
        'verify': "🛡️ 点击下方按钮开始验证。",
        'verification_error': "❌ 验证错误：{}",
        'signup_name': "请输入您的全名：",
        'signup_email': "很好！现在请输入您的电子邮件地址：",
        'invalid_email': "请输入有效的电子邮件地址：",
        'signup_service': "您对哪种服务感兴趣？\n选项：投资、交易、咨询",
        'signup_summary': (
            "已收到注册信息：\n\n"
            "姓名：{}\n"
            "电子邮件：{}\n"
            "服务：{}\n\n"
            "谢谢！我们的团队将很快与您联系。"
        ),
        'consult_name': "输入您的全名以进行咨询：",
        'consult_email': "输入您的电子邮件地址以进行咨询：",
        'consult_date': "首选的咨询日期和时间（例如：2023-12-01 14:00）：",
        'consult_topic': "简要描述您想讨论的主题或问题：",
        'consult_summary': (
            "咨询请求：\n\n"
            "姓名：{}\n"
            "电子邮件：{}\n"
            "日期：{}\n"
            "主题：{}\n\n"
            "谢谢！我们会尽快与您联系。"
        ),
        'ask_question': "在下面输入您的问题：",
        'question_thanks': "感谢您的问题！我们会尽快回复。",
        'cancel': "操作已取消。",
        'back_to_menu': "欢迎回来！点击下方：",
        'faq': "常见问题",
        'website': "网站",
        'signup': "注册",
        'verify_btn': "验证身份",
        'consult': "预约咨询",
        'ask_question_btn': "提问",
        'calendly': "通过Calendly预约咨询",
        'verify_now': "🔗 立即验证",
        'previous': "⬅️ 上一个问题",
        'next': "下一个问题 ➡️",
        'main_menu': "返回主菜单"
    }
}

# FAQ translations
faq_translations = {
    'en': [
        ("What is Vonartis Capital?",
         "Vonartis Capital is a boutique financial advisory service offering high-yield deposit accounts for accredited investors and verified clients. We provide alternative banking solutions with flexible investment options, including crypto."),
        ("Who can invest with Vonartis Capital?",
         "Only accredited investors and verified clients can invest. You must complete identity verification through Verify, our AI-powered onboarding platform."),
        ("What is the minimum investment amount?",
         "The minimum investment amount is $20,000 USD."),
        ("What is the maximum investment per account?",
         "You can invest up to $250,000 USD per account. Multiple accounts are allowed."),
        ("What are the available interest rates?",
         "Interest rates depend on the amount and term of the investment. Returns go up to 20% per annum for Elite clients."),
        ("What are the membership tiers?",
         "Verified Plus: $20K–$50K\nPremium: Up to $100K\nVIP: $100K–$250K\nElite: Over $250K\nEach tier offers increasing access to exclusive benefits such as private consultations, early bird investment options, and custom investment structures."),
        ("Are the funds locked?",
         "Yes, investments are time-locked for the chosen term (6 or 12 months). Your capital and interest are paid out at the end of the term."),
        ("Can I invest using cryptocurrency?",
         "Yes. You can fund your account via crypto wallet. We handle the conversion to fiat and deposit the funds for you."),
        ("Is there a way to track or manage my investment?",
         "You'll receive secure communications via our Telegram channel. For detailed account support or consultations, use our Telegram chatbot or request a direct appointment."),
        ("How do I verify my identity?",
         "We use Verify.ai, a trusted, AI-powered verification system. Simply start the process via our Telegram chatbot."),
        ("Is my investment safe?",
         "Your funds are deposited in a regulated bank and are never blocked, apart from the agreed investment term. We do not use or re-invest your funds."),
        ("How do I get started?",
         "Join our Telegram Channel @vonartis, engage with our chatbot, complete verification, and choose your investment plan."),
    ],
    'es': [
        ("¿Qué es Vonartis Capital?",
         "Vonartis Capital es un servicio de asesoramiento financiero boutique que ofrece cuentas de depósito de alto rendimiento para inversores acreditados y clientes verificados. Ofrecemos soluciones bancarias alternativas con opciones de inversión flexibles, incluyendo criptomonedas."),
        ("¿Quién puede invertir con Vonartis Capital?",
         "Solo inversores acreditados y clientes verificados pueden invertir. Debes completar la verificación de identidad a través de Verify, nuestra plataforma de incorporación con IA."),
        ("¿Cuál es el monto mínimo de inversión?",
         "El monto mínimo de inversión es de $20,000 USD."),
        ("¿Cuál es la inversión máxima por cuenta?",
         "Puedes invertir hasta $250,000 USD por cuenta. Se permiten múltiples cuentas."),
        ("¿Cuáles son las tasas de interés disponibles?",
         "Las tasas de interés dependen del monto y plazo de la inversión. Los rendimientos llegan hasta 20% anual para clientes Elite."),
        ("¿Cuáles son los niveles de membresía?",
         "Verified Plus: $20K–$50K\nPremium: Hasta $100K\nVIP: $100K–$250K\nElite: Más de $250K\nCada nivel ofrece acceso creciente a beneficios exclusivos como consultas privadas, opciones de inversión anticipada y estructuras de inversión personalizadas."),
        ("¿Están los fondos bloqueados?",
         "Sí, las inversiones están bloqueadas por el plazo elegido (6 o 12 meses). Tu capital e intereses se pagan al final del plazo."),
        ("¿Puedo invertir usando criptomonedas?",
         "Sí. Puedes fondear tu cuenta mediante billetera cripto. Nos encargamos de la conversión a fiat y depositamos los fondos por ti."),
        ("¿Hay alguna forma de rastrear o gestionar mi inversión?",
         "Recibirás comunicaciones seguras a través de nuestro canal de Telegram. Para soporte detallado de cuenta o consultas, usa nuestro chatbot de Telegram o solicita una cita directa."),
        ("¿Cómo verifico mi identidad?",
         "Usamos Verify.ai, un sistema de verificación confiable con IA. Simplemente inicia el proceso a través de nuestro chatbot de Telegram."),
        ("¿Es segura mi inversión?",
         "Tus fondos se depositan en un banco regulado y nunca se bloquean, aparte del plazo de inversión acordado. No usamos ni reinvertimos tus fondos."),
        ("¿Cómo empiezo?",
         "Únete a nuestro Canal de Telegram @vonartis, interactúa con nuestro chatbot, completa la verificación y elige tu plan de inversión."),
    ],
    'ru': [
        ("Что такое Vonartis Capital?",
         "Vonartis Capital — это бутик-сервис финансового консультирования, предлагающий высокодоходные депозитные счета для аккредитованных инвесторов и проверенных клиентов. Мы предоставляем альтернативные банковские решения с гибкими вариантами инвестиций, включая криптовалюты."),
        ("Кто может инвестировать с Vonartis Capital?",
         "Только аккредитованные инвесторы и проверенные клиенты могут инвестировать. Вы должны пройти проверку личности через Verify, нашу платформу для онбординга с ИИ."),
        ("Какова минимальная сумма инвестиций?",
         "Минимальная сумма инвестиций составляет $20,000 USD."),
        ("Какова максимальная инвестиция на один счет?",
         "Вы можете инвестировать до $250,000 USD на один счет. Разрешено несколько счетов."),
        ("Какие процентные ставки доступны?",
         "Процентные ставки зависят от суммы и срока инвестиции. Доходность достигает 20% годовых для клиентов Elite."),
        ("Какие уровни членства существуют?",
         "Verified Plus: $20K–$50K\nPremium: До $100K\nVIP: $100K–$250K\nElite: Свыше $250K\nКаждый уровень предлагает расширенный доступ к эксклюзивным преимуществам, таким как частные консультации, ранний доступ к инвестиционным возможностям и индивидуальные инвестиционные структуры."),
        ("Заблокированы ли средства?",
         "Да, инвестиции заблокированы на выбранный срок (6 или 12 месяцев). Ваш капитал и проценты выплачиваются в конце срока."),
        ("Могу ли я инвестировать с помощью криптовалюты?",
         "Да. Вы можете пополнить счет через криптокошелек. Мы конвертируем в фиат и депонируем средства за вас."),
        ("Есть ли способ отслеживать или управлять моими инвестициями?",
         "Вы будете получать безопасные сообщения через наш канал в Telegram. Для детальной поддержки счета или консультаций используйте нашего Telegram-бота или запросите прямое назначение."),
        ("Как я могу подтвердить свою личность?",
         "Мы используем Verify.ai, надежную систему проверки на основе ИИ. Просто начните процесс через нашего Telegram-бота."),
        ("Безопасны ли мои инвестиции?",
         "Ваши средства депонированы в регулируемом банке и никогда не блокируются, за исключением согласованного срока инвестирования. Мы не используем и не реинвестируем ваши средства."),
        ("Как начать?",
         "Присоединяйтесь к нашему Telegram-каналу @vonartis, взаимодействуйте с нашим ботом, завершите проверку и выберите свой инвестиционный план."),
    ],
    'ar': [
        ("ما هو Vonartis Capital؟",
         "Vonartis Capital هي خدمة استشارية مالية متخصصة تقدم حسابات إيداع عالية العائد للمستثمرين المعتمدين والعملاء الموثقين. نقدم حلول بنكية بديلة مع خيارات استثمارية مرنة، بما في ذلك العملات المشفرة."),
        ("من يمكنه الاستثمار مع Vonartis Capital؟",
         "فقط المستثمرون المعتمدون والعملاء الموثقون يمكنهم الاستثمار. يجب عليك إكمال التحقق من الهوية عبر Verify، منصة التوثيق المدعومة بالذكاء الاصطناعي."),
        ("ما هو الحد الأدنى لمبلغ الاستثمار؟",
         "الحد الأدنى لمبلغ الاستثمار هو $20,000 دولار أمريكي."),
        ("ما هو الحد الأقصى للاستثمار لكل حساب؟",
         "يمكنك الاستثمار حتى $250,000 دولار أمريكي لكل حساب. يُسمح بحسابات متعددة."),
        ("ما هي أسعار الفائدة المتاحة؟",
         "تعتمد أسعار الفائدة على مبلغ الاستثمار ومدة الاستثمار. تصل العوائد إلى 20٪ سنويًا لعملاء Elite."),
        ("ما هي مستويات العضوية؟",
         "Verified Plus: $20K–$50K\nPremium: حتى $100K\nVIP: $100K–$250K\nElite: أكثر من $250K\nكل مستوى يوفر وصولًا متزايدًا إلى مزايا حصرية مثل الاستشارات الخاصة، خيارات الاستثمار المبكرة، وهياكل استثمار مخصصة."),
        ("هل الأموال مقفلة؟",
         "نعم، الاستثمارات مقفلة للمدة المختارة (6 أو 12 شهرًا). يتم دفع رأس مالك وفائدتك في نهاية المدة."),
        ("هل يمكنني الاستثمار باستخدام العملات المشفرة؟",
         "نعم. يمكنك تمويل حسابك عبر محفظة العملات المشفرة. نحن نتعامل مع التحويل إلى العملات التقليدية وإيداع الأموال نيابة عنك."),
        ("هل هناك طريقة لتتبع أو إدارة استثماري؟",
         "ستتلقى اتصالات آمنة عبر قناتنا على Telegram. للحصول على دعم مفصل للحساب أو الاستشارات، استخدم بوت Telegram الخاص بنا أو اطلب موعدًا مباشرًا."),
        ("كيف يمكنني التحقق من هويتي؟",
         "نستخدم Verify.ai، نظام تحقق موثوق به يعمل بالذكاء الاصطناعي. ما عليك سوى بدء العملية عبر بوت Telegram الخاص بنا."),
        ("هل استثماري آمن؟",
         "يتم إيداع أموالك في بنك خاضع للتنظيم ولا يتم حظرها أبدًا، باستثناء مدة الاستثمار المتفق عليها. نحن لا نستخدم أو نعيد استثمار أموالك."),
        ("كيف أبدأ؟",
         "انضم إلى قناتنا على Telegram @vonartis، تفاعل مع بوتنا، أكمل التحقق واختر خطة الاستثمار الخاصة بك."),
    ],
    'zh': [
        ("Vonartis Capital是什么？",
         "Vonartis Capital是一家精品金融咨询服务公司，为合格投资者和验证客户提供高收益存款账户。我们提供灵活的替代银行解决方案，包括加密货币投资选项。"),
        ("谁可以在Vonartis Capital投资？",
         "只有合格投资者和验证客户可以投资。您必须通过我们的AI驱动的验证平台Verify完成身份验证。"),
        ("最低投资金额是多少？",
         "最低投资金额为20,000美元。"),
        ("每个账户的最高投资额是多少？",
         "每个账户最多可投资250,000美元。允许多个账户。"),
        ("有哪些可用的利率？",
         "利率取决于投资金额和期限。Elite客户的年回报率高达20%。"),
        ("有哪些会员等级？",
         "Verified Plus: $20K–$50K\nPremium: 最高$100K\nVIP: $100K–$250K\nElite: 超过$250K\n每个等级提供越来越多的独家福利，如私人咨询、早期投资选项和定制投资结构。"),
        ("资金是否被锁定？",
         "是的，投资在所选期限内（6或12个月）被锁定。您的本金和利息将在期限结束时支付。"),
        ("我可以用加密货币投资吗？",
         "可以。您可以通过加密钱包为账户注资。我们负责转换为法币并为您存入资金。"),
        ("有没有办法跟踪或管理我的投资？",
         "您将通过我们的Telegram频道接收安全通信。如需详细的账户支持或咨询，请使用我们的Telegram聊天机器人或请求直接预约。"),
        ("如何验证我的身份？",
         "我们使用Verify.ai，一个值得信赖的AI驱动验证系统。只需通过我们的Telegram聊天机器人开始流程。"),
        ("我的投资安全吗？",
         "您的资金存入受监管的银行，除了商定的投资期限外，永远不会被冻结。我们不会使用或重新投资您的资金。"),
        ("如何开始？",
         "加入我们的Telegram频道@vonartis，与我们的聊天机器人互动，完成验证并选择您的投资计划。"),
    ]
}

# Helper to send messages async in thread
def send_message_async(bot, chat_id: int, text: str):
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(bot.send_message(chat_id=chat_id, text=text), loop)

# Webhook endpoint for Veriff KYC updates
@app.route('/veriff/webhook', methods=['POST'])
def veriff_webhook():
    data = request.json
    action = data.get("action")
    vendor_data = data.get("vendorData", "")
    telegram_user_id = vendor_data.replace("TG:", "") if vendor_data.startswith("TG:") else None
    if telegram_user_id:
        status_messages = {
            "submitted": "✅ Your identity has been verified!",
            "declined": "❌ Your identity has been rejected.",
            "resubmission": "⚠️ Your KYC needs to be resubmitted."
        }
        message = status_messages.get(action)
        if message:
            bot = Bot(token=BOT_TOKEN)
            threading.Thread(target=send_message_async, args=(bot, int(telegram_user_id), message)).start()
    return jsonify({"message": "Processed"}), 200

# Keyboards
def language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Español", callback_data="lang_es"),
            InlineKeyboardButton("Русский", callback_data="lang_ru")
        ],
        [
            InlineKeyboardButton("العربية", callback_data="lang_ar"),
            InlineKeyboardButton("中文", callback_data="lang_zh")
        ]
    ])

def main_menu_keyboard(lang='en'):
    trans = translations[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(trans['faq'], callback_data="faq"),
         InlineKeyboardButton(trans['website'], url="https://www.vonartis.com")],
        [InlineKeyboardButton(trans['signup'], callback_data="signup"),
         InlineKeyboardButton(trans['verify_btn'], callback_data="verify")],
        [InlineKeyboardButton(trans['consult'], callback_data="consult"),
         InlineKeyboardButton(trans['ask_question_btn'], callback_data="ask_question")],
        [InlineKeyboardButton(trans['calendly'], url=CALENDLY_BASE_URL)]
    ])

def back_to_menu_keyboard(lang='en'):
    trans = translations[lang]
    return InlineKeyboardMarkup([[InlineKeyboardButton(trans['main_menu'], callback_data="main_menu")]])

def faq_navigation_keyboard(current_index: int, total: int, lang='en'):
    trans = translations[lang]
    buttons = []
    if current_index > 0:
        buttons.append(InlineKeyboardButton(trans['previous'], callback_data=f"faq_{current_index - 1}"))
    if current_index < total - 1:
        buttons.append(InlineKeyboardButton(trans['next'], callback_data=f"faq_{current_index + 1}"))
    buttons.append(InlineKeyboardButton(trans['main_menu'], callback_data="main_menu"))
    return InlineKeyboardMarkup([buttons])

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(translations['en']['welcome'], reply_markup=language_keyboard())
    return SELECT_LANGUAGE

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    context.user_data['lang'] = lang
    trans = translations[lang]
    await query.edit_message_text(trans['menu'], reply_markup=main_menu_keyboard(lang))
    return ConversationHandler.END

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]

    if data == "verify":
        try:
            telegram_user_id = update.effective_user.id
            headers = {
                "X-AUTH-CLIENT": VERIFF_API_KEY,
                "Content-Type": "application/json"
            }
            data_veriff = {"verification": {
                "callback": f"{BASE_URL}/veriff/webhook",
                "vendorData": f"TG:{telegram_user_id}"
            }}
            response = requests.post("https://stationapi.veriff.com/v1/sessions", json=data_veriff, headers=headers)
            url = response.json()['verification']['url']
            keyboard = InlineKeyboardMarkup([
                 [InlineKeyboardButton(trans['verify_now'], url=url)],
                 [InlineKeyboardButton(trans['main_menu'], callback_data="main_menu")]
            ])
            await query.message.delete()
            with open("verification.jpg", "rb") as photo:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo,
                    caption=trans['verify'],
                    reply_markup=keyboard
                )
        except Exception as e:
            await query.edit_message_text(trans['verification_error'].format(str(e)), reply_markup=main_menu_keyboard(lang))
        return ConversationHandler.END

    elif data == "signup":
        await query.edit_message_text(trans['signup_name'], reply_markup=back_to_menu_keyboard(lang))
        return SIGNUP_NAME

    elif data == "consult":
        await query.edit_message_text(trans['consult_name'], reply_markup=back_to_menu_keyboard(lang))
        return CONSULT_NAME

    elif data.startswith("faq"):
        if data == "faq":
            idx = 0
        else:
            idx = int(data.split("_")[1])
        faqs = faq_translations[lang]
        question, answer = faqs[idx]
        text = f"*Q{idx+1}: {question}*\n\n💬 {answer}"
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=faq_navigation_keyboard(idx, len(faqs), lang)
        )
        return FAQ_Q

    elif data == "ask_question":
        await query.edit_message_text(trans['ask_question'], reply_markup=back_to_menu_keyboard(lang))
        return ASK_QUESTION

    elif data == "main_menu":
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Could not delete message: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=trans['back_to_menu'],
            reply_markup=main_menu_keyboard(lang)
        )
        return ConversationHandler.END

# --- SIGNUP flow ---

async def signup_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]
    
    if update.message.text == "/cancel":
        await update.message.reply_text(trans['cancel'], reply_markup=main_menu_keyboard(lang))
        return ConversationHandler.END
    context.user_data['signup_name'] = update.message.text.strip()
    await update.message.reply_text(trans['signup_email'])
    return SIGNUP_EMAIL

async def signup_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]
    
    email = update.message.text.strip()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        await update.message.reply_text(trans['invalid_email'])
        return SIGNUP_EMAIL
    context.user_data['signup_email'] = email
    await update.message.reply_text(trans['signup_service'])
    return SIGNUP_SERVICE

async def signup_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]
    
    service = update.message.text.strip()
    context.user_data['signup_service'] = service
    data = context.user_data
    summary = trans['signup_summary'].format(
        data.get('signup_name'),
        data.get('signup_email'),
        service
    )
    await update.message.reply_text(summary, reply_markup=main_menu_keyboard(lang))

    # Notify admin
    admin_message = f"New signup:\nName: {data.get('signup_name')}\nEmail: {data.get('signup_email')}\nService: {service}"
    bot = context.bot
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    return ConversationHandler.END

# --- CONSULTATION flow ---

async def consult_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]
    
    context.user_data['consult_name'] = update.message.text.strip()
    await update.message.reply_text(trans['consult_email'])
    return CONSULT_EMAIL

async def consult_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]
    
    email = update.message.text.strip()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        await update.message.reply_text(trans['invalid_email'])
        return CONSULT_EMAIL
    context.user_data['consult_email'] = email
    await update.message.reply_text(trans['consult_date'])
    return CONSULT_DATE

async def consult_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]
    
    date_text = update.message.text.strip()
    context.user_data['consult_date'] = date_text
    await update.message.reply_text(trans['consult_topic'])
    return CONSULT_TOPIC

async def consult_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]
    
    topic = update.message.text.strip()
    context.user_data['consult_topic'] = topic
    data = context.user_data
    summary = trans['consult_summary'].format(
        data.get('consult_name'),
        data.get('consult_email'),
        data.get('consult_date'),
        topic
    )
    await update.message.reply_text(summary, reply_markup=main_menu_keyboard(lang))

    # Notify admin
    admin_message = (
        f"New consultation request:\n"
        f"Name: {data.get('consult_name')}\n"
        f"Email: {data.get('consult_email')}\n"
        f"Date: {data.get('consult_date')}\n"
        f"Topic: {topic}"
    )
    bot = context.bot
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    return ConversationHandler.END

# --- ASK QUESTION flow ---

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]
    
    question = update.message.text.strip()
    user = update.effective_user
    # Forward question to admin
    admin_message = f"Question from {user.first_name} (@{user.username}):\n{question}"
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    await update.message.reply_text(trans['question_thanks'], reply_markup=main_menu_keyboard(lang))
    return ConversationHandler.END

# --- FAQ navigation ---

async def faq_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]
    faqs = faq_translations[lang]
    
    if data.startswith("faq_"):
        idx = int(data.split("_")[1])
        question, answer = faqs[idx]
        text = f"*Q{idx+1}: {question}*\n\n💬 {answer}"
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=faq_navigation_keyboard(idx, len(faqs), lang)
        )
        return FAQ_Q
    elif data == "main_menu":
        await query.edit_message_text(trans['back_to_menu'], reply_markup=main_menu_keyboard(lang))
        return ConversationHandler.END

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    trans = translations[lang]
    
    await update.message.reply_text(trans['cancel'], reply_markup=main_menu_keyboard(lang))
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start), 
            CallbackQueryHandler(select_language, pattern=r"^lang_"),
            CallbackQueryHandler(main_menu_handler)
        ],
        states={
            SELECT_LANGUAGE: [CallbackQueryHandler(select_language, pattern=r"^lang_")],
            SIGNUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, signup_name)],
            SIGNUP_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, signup_email)],
            SIGNUP_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, signup_service)],

            CONSULT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, consult_name)],
            CONSULT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, consult_email)],
            CONSULT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, consult_date)],
            CONSULT_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, consult_topic)],

            ASK_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_question)],

            FAQ_Q: [CallbackQueryHandler(faq_navigation, pattern=r"^faq_?\d*$")]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)

    # Start Flask in a thread because Flask runs blocking
    def run_flask():
        app.run(port=5000)

    threading.Thread(target=run_flask).start()

    application.run_polling()

if __name__ == '__main__':
    main()