# ========================================================
# TO'LIQ YANGILANGAN app.py (BARCHA TALABLAR BO'YICHA)
# ========================================================
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import datetime
import logging
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ========================
# MUHIT VA KONFIGURATSIYA
# ========================
IS_PRODUCTION = any([
    os.environ.get('RAILWAY_ENVIRONMENT'),
    os.environ.get('DYNO'),
    os.environ.get('PORT') and os.environ.get('FLASK_ENV') != 'development'
])

if IS_PRODUCTION:
    DB_PATH = '/tmp/data.db'
    UPLOAD_FOLDER = '/tmp/uploads'
    COVER_FOLDER = '/tmp/covers'
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    COVER_FOLDER = os.path.join(BASE_DIR, 'covers')
    DB_PATH = os.path.join(BASE_DIR, 'data.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COVER_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['COVER_FOLDER'] = COVER_FOLDER
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=86400
)

# Email sozlamalari (Railway Variables da o'rnating)
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')

# Til sozlamalari
LANGUAGES = {
    'uz': '🇺🇿 Oʻzbek',
    'ru': '🇷🇺 Русский',
    'tg': '🇹🇯 Тоҷикӣ'
}
DEFAULT_LANG = 'uz'

ALLOWED_EXTENSIONS = {
    'book': {'pdf', 'epub', 'mobi', 'djvu', 'fb2', 'doc', 'docx', 'txt'},
    'app': {'apk', 'exe', 'msi', 'dmg', 'deb', 'rpm', 'zip'},
    'image': {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'},
    'video': {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'mpeg'}
}
ALLOWED_COVER_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

# ========================
# YORDAMCHI FUNKSIYALAR
# ========================
def get_locale():
    """Foydalanuvchi tilini olish"""
    return session.get('lang', request.accept_languages.best_match(LANGUAGES.keys()) or DEFAULT_LANG)

def _(text):
    """Oddiy tarjima funksiyasi (haqiqiy loyihada Flask-Babel ishlatish tavsiya etiladi)"""
    translations = {
        'uz': {
            'search_placeholder': 'Kitob nomi, muallif...',
            'no_results': 'Hech narsa topilmadi 😔',
            'login_to_download': 'Yuklab olish uchun tizimga kiring yoki ro\'yxatdan o\'ting',
            'read_online': 'Onlayn o\'qish',
            'download': 'Yuklab olish',
            'cover_upload': 'Muqova rasmini tanlang (faqat .jpg, .png)',
            'email_verified': 'Email tasdiqlandi! Endi tizimga kiring.',
            'verify_email': 'Iltimos, emailingizni tasdiqlang. Tasdiqlash uchun havola yuborildi.',
            'password_reset_sent': 'Parolni tiklash uchun havola emailingizga yuborildi.',
            'password_updated': 'Parol muvaffaqiyatli yangilandi!',
            'invalid_token': 'Noto\'g\'ri yoki eskirgan havola',
            'register_success': '✅ Ro\'yxatdan o\'tdingiz! Emailingizni tasdiqlang.',
            'cover_label': 'Muqova',
            'search_label': 'Qidiruv',
            'books_label': 'Kitoblar',
            'apps_label': 'Ilovalar',
            'images_label': 'Rasmlar',
            'videos_label': 'Videolar',
            'welcome': 'Xush kelibsiz',
            'about_site': 'Sayt haqida',
            'tutorial_step1': 'Ushbu platformada kitoblar, ilovalar, rasmlar va videolarni topishingiz mumkin. Har bir materialga statistik kartalardan foydalaning.',
            'materials_types': 'Material turlari',
            'how_to_use': 'Qanday foydalanish mumkin?',
            'more_details': 'Batafsil',
            'register_and_admin': 'Ro\'yxatdan o\'ting va admin bo\'ling',
            'back': 'Orqaga',
            'next': 'Keyingi',
            'close': 'Yopish',
            'welcome_library': 'Elektron kutubxonaga xush kelibsiz',
            'library_description': 'Kitoblar, ilovalar, rasmlar va videolarni bepul yuklab oling!',
            'how_to_use_site': 'Saytdan qanday foydalanish mumkin?',
            'site_statistics': 'Sayt statistikasi',
            'search_results': 'Qidiruv natijalari',
            'details': 'Tafsilotlar',
            'clear_search': 'Qidiruvni tozalash',
            'user_services': 'Foydalanuvchi xizmatlari',
            'all_materials_free': 'Barcha materiallar bepul yuklab olinadi',
            'register_and_upload': 'Ro\'yxatdan o\'ting va admin bo\'ling',
            'upload_your_materials': 'O\'z materiallaringizni yuklang',
            'track_statistics': 'Statistikani kuzatib boring',
            'author': 'Muallif',
            'uploaded_by': 'Yuklagan',
            'upload_date': 'Yuklangan sana',
            'views': 'Ko\'rishlar',
            'times': 'marta',
            'description': 'Tavsif',
            'no_description': 'Tavsif mavjud emas',
            'read_online': 'Onlayn o\'qish',
            'file_not_uploaded': 'Fayl yuklanmagan',
            'additional_info': 'Qo\'shimcha ma\'lumot',
            'file': 'Fayl',
            'type': 'Tur',
            'admin_actions': 'Admin amallari',
            'edit': 'Tahrirlash',
            'statistics': 'Statistika',
            'confirm_delete': 'Materialni o\'chirishni xohlaysizmi?',
            'delete': 'O\'chirish',
            'only_your_materials': 'Siz faqat o\'z materiallaringizni boshqarishingiz mumkin',
            'edit_material': 'Materialni tahrirlash',
            'title': 'Sarlavha',
            'optional': 'ixtiyoriy',
            'current_cover': 'Joriy muqova',
            'choose_cover': 'Muqovani tanlang',
            'new_file_optional': 'Yangi faylni yuklang (ixtiyoriy)',
            'current_file': 'Joriy fayl',
            'choose_new_file': 'Yangi faylni tanlang',
            'allowed': 'Ruxsat etilgan',
            'save_changes': 'O\'zgarishlarni saqlash',
            'cancel': 'Bekor qilish'
        },
        'ru': {
            'search_placeholder': 'Название книги, автор...',
            'no_results': 'Ничего не найдено 😔',
            'login_to_download': 'Войдите или зарегистрируйтесь для скачивания',
            'read_online': 'Читать онлайн',
            'download': 'Скачать',
            'cover_upload': 'Выберите обложку (только .jpg, .png)',
            'email_verified': 'Email подтвержден! Теперь войдите в систему.',
            'verify_email': 'Пожалуйста, подтвердите email. Ссылка для подтверждения отправлена.',
            'password_reset_sent': 'Ссылка для восстановления пароля отправлена на ваш email.',
            'password_updated': 'Пароль успешно обновлен!',
            'invalid_token': 'Неверная или просроченная ссылка',
            'register_success': '✅ Регистрация успешна! Подтвердите email.',
            'cover_label': 'Обложка',
            'search_label': 'Поиск',
            'books_label': 'Книги',
            'apps_label': 'Приложения',
            'images_label': 'Изображения',
            'videos_label': 'Видео'
        },
        'tg': {
            'search_placeholder': 'Номи китоб, муаллиф...',
            'no_results': 'Ҳеч чиз ёфт нашуд 😔',
            'login_to_download': 'Барои зеркашӣ кардан ба система ворид шавед ё сабти ном кунед',
            'read_online': 'Онлайн хондан',
            'download': 'Зеркашӣ кардан',
            'cover_upload': 'Тасвири муқоваро интихоб кунед (фақат .jpg, .png)',
            'email_verified': 'Почтаи электронӣ тасдиқ шуд! Акнун ворид шавед.',
            'verify_email': 'Лутфан, почтаи электронии худро тасдиқ кунед. Пайванд барои тасдиқ фиристода шуд.',
            'password_reset_sent': 'Пайванд барои барқарор кардани парол ба почтаи электронии шумо фиристода шуд.',
            'password_updated': 'Парол бо муваффақият навсозӣ шуд!',
            'invalid_token': 'Пайванди нодуруст ё кӯҳна',
            'register_success': '✅ Сабти ном муваффақият аст! Почтаи электрониро тасдиқ кунед.',
            'cover_label': 'Муқова',
            'search_label': 'Ҷустуҷӯ',
            'books_label': 'Китобҳо',
            'apps_label': 'Барномаҳо',
            'images_label': 'Тасвирҳо',
            'videos_label': 'Видеоҳо'
        }
    }
    return translations.get(get_locale(), translations[DEFAULT_LANG]).get(text, text)

def send_verification_email(email, token, is_reset=False):
    """Email yuborish (tasdiqlash yoki parol tiklash)"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = email
        if is_reset:
            msg['Subject'] = _("Parolni tiklash")
            body = f"""<html><body>
                <h2>Parolni tiklash</h2>
                <p>Quyidagi havolani bosing:</p>
                <a href="{request.url_root}reset-password/{token}">Parolni tiklash</a>
                <p>Havola 1 soat amal qiladi.</p>
                <p>Agar siz so'rov yubormagan bo'lsangiz, bu xabarni e'tiborsiz qoldiring.</p>
            </body></html>"""
        else:
            msg['Subject'] = _("Emailni tasdiqlash")
            body = f"""<html><body>
                <h2>Ro'yxatdan o'tishni tasdiqlang</h2>
                <p>Quyidagi havolani bosing:</p>
                <a href="{request.url_root}verify-email/{token}">Emailni tasdiqlash</a>
                <p>Agar siz ro'yxatdan o'tmagansiz, bu xabarni e'tiborsiz qoldiring.</p>
            </body></html>"""
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logging.error(f"Email yuborish xatosi: {e}")
        return False

def allowed_file(filename, allowed_set):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_set

# ========================
# DATABASE FUNKSIYALARI
# ========================
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        db = get_db()
        cur = db.cursor()
        
        # Users jadvaliga email_verified va reset_token qo'shildi
        cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            admin_level INTEGER DEFAULT 0,
            email_verified INTEGER DEFAULT 0,
            reset_token TEXT,
            reset_expires TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Materials jadvaliga cover_image qo'shildi
        cur.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            description TEXT,
            filename TEXT,
            cover_image TEXT,
            material_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            view_count INTEGER DEFAULT 0,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )''')
        
        cur.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        
        cur.execute('''
        CREATE TABLE IF NOT EXISTS view_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            user_id INTEGER,
            viewed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (material_id) REFERENCES materials(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        
        db.commit()
        
        # Bosh admin (agar mavjud bo'lsa, qayta yaratilmaydi)
        try:
            cur.execute(
                "INSERT INTO users (name, email, password, admin_level, email_verified) VALUES (?,?,?,?,?)",
                ("Сардори админ", "admin@local", generate_password_hash("admin123"), 2, 1)
            )
            db.commit()
            print(f"✅ Admin yaratildi! DB: {DB_PATH}")
        except sqlite3.IntegrityError:
            pass
        
        db.close()
        print(f"✅ Database tayyor: {DB_PATH} | Til: {DEFAULT_LANG}")
        return True
    except Exception as e:
        print(f"❌ Database xatosi: {str(e)}")
        logging.error(f"init_db failed: {e}", exc_info=True)
        return False

print(f"🌍 Muhit: {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'}")
print(f"📁 DB: {DB_PATH}")
init_db()

# ========================
# DECORATORLAR
# ========================
def current_user():
    if not session.get('user_id'):
        return None
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    db.close()
    return user

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get('user_id'):
            flash(_("login_to_download"))
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return wrap

# ... [admin_required, main_admin_required funksiyalari oldingidek qoladi] ...
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrap(*args, **kwargs):
        user = current_user()
        if not user or user['admin_level'] < 1:
            flash("⚠️ Ҳуқуқҳои маъмурӣ лозиманд")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrap

def main_admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrap(*args, **kwargs):
        user = current_user()
        if not user or user['admin_level'] < 2:
            flash("⚠️ Танҳо барои мудири асосӣ")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrap

# ========================
# TIL BOSHQARUVI
# ========================
@app.route('/set-language/<lang_code>')
def set_language(lang_code):
    if lang_code in LANGUAGES:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))

# ========================
# ASOSIY SAHIFALAR
# ========================
@app.route("/")
def index():
    db = get_db()
    # Qidiruv
    search_query = request.args.get('q', '').strip()
    if search_query:
        materials = db.execute("""
            SELECT * FROM materials 
            WHERE material_type='book' 
            AND (title LIKE ? OR author LIKE ?)
            ORDER BY id DESC
        """, (f'%{search_query}%', f'%{search_query}%')).fetchall()
        if not materials:
            flash(_("no_results"))
    else:
        materials = db.execute("""
            SELECT * FROM materials 
            WHERE material_type='book' 
            ORDER BY id DESC LIMIT 20
        """).fetchall()
    
    stats = {
        'books': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='book'").fetchone()['c'],
        'apps': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='app'").fetchone()['c'],
        'images': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='image'").fetchone()['c'],
        'videos': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='video'").fetchone()['c'],
    }
    db.close()
    return render_template(
        "index.html", 
        stats=stats, 
        materials=materials, 
        search_query=search_query,
        _=_
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Email format tekshiruvi
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash("❌ Email manzili noto'g'ri formatda")
            return redirect(url_for('register'))
        
        # Parol kuchli ekanligini tekshirish
        if len(password) < 8 or not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
            flash("❌ Parol kamida 8 belgidan iborat bo'lishi, harf va raqamni o'z ichiga olishi kerak")
            return redirect(url_for('register'))
        
        db = get_db()
        try:
            # Avval foydalanuvchini yaratamiz, lekin email tasdiqlanmaguncha faol emas
            token = secrets.token_urlsafe(32)
            db.execute("""
                INSERT INTO users (name, email, password, admin_level, email_verified, reset_token) 
                VALUES (?,?,?,?,?,?)
            """, (name, email, generate_password_hash(password), 0, 0, token))
            db.commit()
            
            # Email yuborish
            if send_verification_email(email, token):
                flash(_("register_success"))
            else:
                flash("⚠️ Ro'yxatdan o'tish muvaffaqiyatli amalga oshirildi, lekin email yuborilmadi. Keyinroq qayta urinib ko'ring.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("❌ Bu email allaqachon ro'yxatdan o'tgan")
            return redirect(url_for('register'))
        finally:
            db.close()
    
    return render_template("register.html", _=_)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Kirish"""
    if request.method == "POST":
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        db.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['admin_level'] = user['admin_level']
            
            if user['admin_level'] == 2:
                flash(f"✅ Ҳуш омадед, {user['name']}!")
            elif user['admin_level'] == 1:
                flash(f"✅ Ҳуш омадед, {user['name']}!")
            else:
                flash(f"✅ Ҳуш омадед, {user['name']}!")
            
            return redirect(url_for('index'))
        else:
            flash("❌ Почтаи электронӣ ё пароли нодуруст")
            return redirect(url_for('login'))
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Chiqish"""
    session.clear()
    flash("✅ Аз система бромадид")
    return redirect(url_for('index'))

@app.route("/verify-email/<token>")
def verify_email(token):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE reset_token=?", (token,)).fetchone()
    if user and user['email_verified'] == 0:
        db.execute("UPDATE users SET email_verified=1, reset_token=NULL WHERE id=?", (user['id'],))
        db.commit()
        flash(_("email_verified"))
        db.close()
        return redirect(url_for('login'))
    db.close()
    flash(_("invalid_token"))
    return redirect(url_for('register'))

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get('email', '').strip().lower()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and user['email_verified']:
            token = secrets.token_urlsafe(32)
            expires = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat()
            db.execute("UPDATE users SET reset_token=?, reset_expires=? WHERE id=?", (token, expires, user['id']))
            db.commit()
            db.close()
            
            if send_verification_email(email, token, is_reset=True):
                flash(_("password_reset_sent"))
            else:
                flash("⚠️ Xatolik yuz berdi. Keyinroq qayta urinib ko'ring.")
            return redirect(url_for('login'))
        db.close()
        flash("✅ Agar email mavjud bo'lsa, ko'rsatmalar yuborildi.")
        return redirect(url_for('forgot_password'))
    
    return render_template("forgot_password.html", _=_)

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE reset_token=?", (token,)).fetchone()
    
    if not user:
        db.close()
        flash(_("invalid_token"))
        return redirect(url_for('login'))
    
    # Token muddati o'tganmi?
    if user['reset_expires'] and datetime.datetime.fromisoformat(user['reset_expires']) < datetime.datetime.utcnow():
        db.execute("UPDATE users SET reset_token=NULL, reset_expires=NULL WHERE id=?", (user['id'],))
        db.commit()
        db.close()
        flash(_("invalid_token"))
        return redirect(url_for('forgot_password'))
    
    if request.method == "POST":
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        
        if password != confirm:
            flash("❌ Parollar mos kelmaydi")
            return redirect(url_for('reset_password', token=token))
        
        if len(password) < 8:
            flash("❌ Parol kamida 8 belgidan iborat bo'lishi kerak")
            return redirect(url_for('reset_password', token=token))
        
        db.execute("UPDATE users SET password=?, reset_token=NULL, reset_expires=NULL WHERE id=?", 
                  (generate_password_hash(password), user['id']))
        db.commit()
        db.close()
        flash(_("password_updated"))
        return redirect(url_for('login'))
    
    db.close()
    return render_template("reset_password.html", token=token, _=_)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        next_page = request.args.get('next')
        
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        db.close()
        
        if user and check_password_hash(user['password'], password):
            if user['email_verified'] == 0:
                flash(_("verify_email"))
                return redirect(url_for('login'))
            
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['admin_level'] = user['admin_level']
            session['lang'] = session.get('lang', DEFAULT_LANG)
            
            flash(f"✅ {_('welcome')}, {user['name']}!" if _('welcome') != 'welcome' else f"✅ Ҳуш омадед, {user['name']}!")
            return redirect(next_page or url_for('index'))
        else:
            flash("❌ Email yoki parol noto'g'ri")
            return redirect(url_for('login'))
    
    return render_template("login.html", _=_)

@app.route("/materials")
@app.route("/materials/<material_type>")
def materials(material_type=None):
    """Barcha materiallar yoki turga qarab"""
    db = get_db()
    
    if material_type and material_type in ['book', 'app', 'image', 'video']:
        rows = db.execute(
            "SELECT * FROM materials WHERE material_type=? ORDER BY id DESC", 
            (material_type,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM materials ORDER BY id DESC").fetchall()
    
    db.close()
    return render_template("materials.html", materials=rows, current_type=material_type)

@app.route("/material/<int:material_id>")
def material_detail(material_id):
    db = get_db()
    material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    if not material:
        db.close()
        abort(404)
    
    # Ko'rish sonini oshirish
    db.execute("UPDATE materials SET view_count = view_count + 1 WHERE id=?", (material_id,))
    
    if session.get('user_id'):
        db.execute("INSERT INTO view_history (material_id, user_id, viewed_at) VALUES (?,?,?)",
                   (material_id, session['user_id'], datetime.datetime.utcnow().isoformat()))
    else:
        db.execute("INSERT INTO view_history (material_id, user_id, viewed_at) VALUES (?,?,?)",
                   (material_id, None, datetime.datetime.utcnow().isoformat()))
    
    db.commit()
    
    uploader = None
    if material['uploaded_by']:
        uploader = db.execute("SELECT name FROM users WHERE id=?", (material['uploaded_by'],)).fetchone()
    
    db.close()
    return render_template("material_detail.html", material=material, uploader=uploader, _=_)

@app.route("/download/<path:filename>")
@login_required
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        flash(f"❌ Xatolik: {str(e)}")
        return redirect(url_for('index'))

@app.route("/view/<path:filename>")
@login_required
def view_file(filename):
    """PDFni brauzerda ochish uchun"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)
    except Exception as e:
        flash(f"❌ Xatolik: {str(e)}")
        return redirect(url_for('index'))

# ========================
# ADMIN FUNKSIYALARI (YANGILANGAN)
# ========================
@app.route("/admin")
@admin_required
def admin():
    """Admin paneli"""
    user = current_user()
    db = get_db()
    
    # Oddiy admin faqat o'z materiallarini ko'radi
    if user['admin_level'] == 1:
        materials = db.execute(
            "SELECT * FROM materials WHERE uploaded_by=? ORDER BY id DESC", 
            (user['id'],)
        ).fetchall()
        users = []
    else:
        # Bosh admin hamma narsani ko'radi
        materials = db.execute("SELECT * FROM materials ORDER BY id DESC").fetchall()
        users = db.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
    
    db.close()
    return render_template("admin.html", users=users, materials=materials, user=user)

@app.route("/admin/add", methods=["POST"])
@admin_required
def admin_add_material():
    user = current_user()
    material_type = request.form.get('material_type', 'book')
    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()
    description = request.form.get('description', '').strip()
    uploaded_file = request.files.get('file')
    cover_file = request.files.get('cover_image')
    
    if user['admin_level'] == 1 and material_type not in ['book', 'app']:
        flash("⚠️ Faqat kitob va ilova yuklashingiz mumkin")
        return redirect(url_for('admin'))
    
    if not title:
        flash("❌ Sarlavha majburiy")
        return redirect(url_for('admin'))
    
    # Asosiy faylni saqlash
    filename = None
    if uploaded_file and uploaded_file.filename:
        if allowed_file(uploaded_file.filename, ALLOWED_EXTENSIONS.get(material_type, set())):
            filename = secure_filename(uploaded_file.filename)
            counter = 1
            base, ext = os.path.splitext(filename)
            while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                filename = f"{base}_{counter}{ext}"
                counter += 1
            uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            flash(f"❌ Noto'g'ri fayl turi")
            return redirect(url_for('admin'))
    
    # Muqova rasmini saqlash
    cover_filename = None
    if cover_file and cover_file.filename:
        if allowed_file(cover_file.filename, ALLOWED_COVER_EXTENSIONS):
            cover_filename = secure_filename(cover_file.filename)
            counter = 1
            base, ext = os.path.splitext(cover_filename)
            while os.path.exists(os.path.join(app.config['COVER_FOLDER'], cover_filename)):
                cover_filename = f"{base}_{counter}{ext}"
                counter += 1
            cover_file.save(os.path.join(app.config['COVER_FOLDER'], cover_filename))
        else:
            flash(_("cover_upload"))
            return redirect(url_for('admin'))
    
    # Ma'lumotlar bazasiga qo'shish
    db = get_db()
    db.execute("""
        INSERT INTO materials (title, author, description, filename, cover_image, material_type, created_at, uploaded_by) 
        VALUES (?,?,?,?,?,?,?,?)
    """, (title, author, description, filename, cover_filename, material_type, 
          datetime.datetime.utcnow().isoformat(), user['id']))
    db.commit()
    db.close()
    
    flash("✅ Material qo'shildi")
    return redirect(url_for('admin'))

@app.route("/admin/material/<int:material_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_material(material_id):
    user = current_user()
    db = get_db()
    material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    if not material:
        db.close()
        abort(404)
    
    if user['admin_level'] == 1 and material['uploaded_by'] != user['id']:
        flash("⚠️ Faqat o'z materiallaringizni tahrirlaysiz")
        db.close()
        return redirect(url_for('admin'))
    
    if request.method == "POST":
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        description = request.form.get('description', '').strip()
        uploaded_file = request.files.get('file')
        cover_file = request.files.get('cover_image')
        
        if not title:
            flash("❌ Sarlavha majburiy")
            return redirect(url_for('admin_edit_material', material_id=material_id))
        
        # Yangi fayl yuklangan bo'lsa
        if uploaded_file and uploaded_file.filename:
            if allowed_file(uploaded_file.filename, ALLOWED_EXTENSIONS.get(material['material_type'], set())):
                # Eski faylni o'chirish
                if material['filename']:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], material['filename'])
                    if os.path.exists(old_path):
                        os.remove(old_path)
                # Yangi faylni saqlash
                filename = secure_filename(uploaded_file.filename)
                counter = 1
                base, ext = os.path.splitext(filename)
                while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                    filename = f"{base}_{counter}{ext}"
                    counter += 1
                uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                db.execute("UPDATE materials SET filename=? WHERE id=?", (filename, material_id))
            else:
                flash("❌ Noto'g'ri fayl turi")
                db.close()
                return redirect(url_for('admin_edit_material', material_id=material_id))
        
        # Yangi muqova yuklangan bo'lsa
        if cover_file and cover_file.filename:
            if allowed_file(cover_file.filename, ALLOWED_COVER_EXTENSIONS):
                # Eski muqovani o'chirish
                if material['cover_image']:
                    old_cover = os.path.join(app.config['COVER_FOLDER'], material['cover_image'])
                    if os.path.exists(old_cover):
                        os.remove(old_cover)
                # Yangi muqovani saqlash
                cover_filename = secure_filename(cover_file.filename)
                counter = 1
                base, ext = os.path.splitext(cover_filename)
                while os.path.exists(os.path.join(app.config['COVER_FOLDER'], cover_filename)):
                    cover_filename = f"{base}_{counter}{ext}"
                    counter += 1
                cover_file.save(os.path.join(app.config['COVER_FOLDER'], cover_filename))
                db.execute("UPDATE materials SET cover_image=? WHERE id=?", (cover_filename, material_id))
        
        # Ma'lumotlarni yangilash
        db.execute("""
            UPDATE materials SET title=?, author=?, description=? WHERE id=?
        """, (title, author, description, material_id))
        
        db.commit()
        db.close()
        flash("✅ Material tahrirlandi")
        return redirect(url_for('admin'))
    
    db.close()
    return render_template("admin_edit_material.html", material=material, _=_)

@app.route("/admin/material/<int:material_id>/delete")
@admin_required
def admin_delete_material(material_id):
    user = current_user()
    db = get_db()
    material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    if not material:
        db.close()
        abort(404)
    
    if user['admin_level'] == 1 and material['uploaded_by'] != user['id']:
        flash("⚠️ Faqat o'z materiallaringizni o'chirish mumkin")
        db.close()
        return redirect(url_for('admin'))
    
    # Faylni o'chirish
    if material['filename']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], material['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # Muqovani o'chirish
    if material['cover_image']:
        cover_path = os.path.join(app.config['COVER_FOLDER'], material['cover_image'])
        if os.path.exists(cover_path):
            os.remove(cover_path)
    
    db.execute("DELETE FROM materials WHERE id=?", (material_id,))
    db.execute("DELETE FROM view_history WHERE material_id=?", (material_id,))
    db.commit()
    db.close()
    
    flash("✅ Material o'chirildi")
    return redirect(url_for('admin'))

@app.route("/admin/material/<int:material_id>/stats")
@admin_required
def admin_material_stats(material_id):
    """Material statistikasi"""
    user = current_user()
    db = get_db()
    
    material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    
    if not material:
        db.close()
        abort(404)
    
    # Oddiy admin faqat o'z statistikasini ko'radi
    if user['admin_level'] == 1 and material['uploaded_by'] != user['id']:
        flash("⚠️ Шумо фақат омори маводи худатонро дида метавонед")
        db.close()
        return redirect(url_for('admin'))
    
    # Ko'rishlar tarixini olish
    views = db.execute("""
        SELECT view_history.*, users.name 
        FROM view_history 
        LEFT JOIN users ON view_history.user_id = users.id
        WHERE material_id=? 
        ORDER BY viewed_at DESC
    """, (material_id,)).fetchall()
    
    db.close()
    return render_template("admin_material_stats.html", material=material, views=views)

# ========================
# FOYDALANUVCHILARNI BOSHQARISH (FAQAT BOSH ADMIN)
# ========================
@app.route("/admin/user/<int:user_id>/toggle")
@main_admin_required
def admin_toggle_user(user_id):
    """Foydalanuvchini admin qilish yoki adminlikni olish"""
    db = get_db()
    target_user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    
    if not target_user:
        db.close()
        flash("❌ Корбар ёфт нашуд")
        return redirect(url_for('admin'))
    
    # O'zini o'zgartira olmaydi
    if target_user['id'] == session['user_id']:
        db.close()
        flash("⚠️ Шумо наметавонед худро тағир диҳед")
        return redirect(url_for('admin'))
    
    # Boshqa bosh adminni o'zgartira olmaydi
    if target_user['admin_level'] == 2:
        db.close()
        flash("⚠️ Шумо дигар администратори асосиро иваз карда наметавонед")
        return redirect(url_for('admin'))
    
    # Toggle admin status (0 <-> 1)
    new_level = 1 if target_user['admin_level'] == 0 else 0
    db.execute("UPDATE users SET admin_level=? WHERE id=?", (new_level, user_id))
    db.commit()
    db.close()
    
    if new_level == 1:
        flash(f"✅ {target_user['name']} администратори оддӣ анҷом дода шуд")
    else:
        flash(f"✅ {target_user['name']} истифодабарандаи доимӣ гардид")
    
    return redirect(url_for('admin'))

@app.route("/admin/notify/<int:user_id>", methods=["GET", "POST"])
@main_admin_required
def admin_notify_user(user_id):
    """Foydalanuvchiga xabar yuborish"""
    db = get_db()
    target_user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    
    if not target_user:
        db.close()
        abort(404)
    
    if request.method == "POST":
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        
        if not title or not message:
            flash("❌ Сарлавҳа ва паём лозим аст")
            return redirect(url_for('admin_notify_user', user_id=user_id))
        
        db.execute(
            "INSERT INTO notifications (user_id, title, message, created_at) VALUES (?,?,?,?)",
            (user_id, title, message, datetime.datetime.utcnow().isoformat())
        )
        db.commit()
        db.close()
        
        flash(f"✅ {target_user['name']}ga xabar yuborildi")
        return redirect(url_for('admin'))
    
    db.close()
    return render_template("admin_notify.html", user=target_user)

@app.route("/notifications")
@login_required
def notifications():
    db = get_db()
    notes = db.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC", (session['user_id'],)).fetchall()
    db.close()
    return render_template("notifications.html", notes=notes, _=_)

@app.route("/notify/reply", methods=["POST"])
@login_required
def notify_reply():
    """Adminga javob yuborish (hozircha ishlatilmaydi)"""
    text = request.form.get('text', '').strip()
    
    if not text:
        flash("❌ Матни хабар бояд ворид карда шавад")
        return redirect(url_for('notifications'))
    
    db = get_db()
    # Bosh adminga xabar yuborish (user_id=1)
    db.execute(
        "INSERT INTO notifications (user_id, title, message, created_at) VALUES (?,?,?,?)",
        (1, f"Javоб: {session.get('user_name')}", text, datetime.datetime.utcnow().isoformat())
    )
    db.commit()
    db.close()
    
    flash("✅ Ҷавоб фиристода шуд")
    return redirect(url_for('notifications'))

@app.route("/api/tutorial-seen", methods=["POST"])
def tutorial_seen():
    """Tutorial ko'rilganini belgilash"""
    return jsonify({"status": "ok"})

@app.route("/health")
def health_check():
    try:
        db = get_db()
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='materials'").fetchone()
        db.close()
        if tables:
            return jsonify({"status": "healthy", "db_path": DB_PATH, "lang": get_locale()}), 200
        init_db()
        return jsonify({"status": "reinitialized"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# app.py ga qo'shing (material_detail.html va index.html uchun)
@app.route('/cover/<path:filename>')
def cover_image(filename):
    try:
        return send_from_directory(app.config['COVER_FOLDER'], filename)
    except Exception as e:
        # Agar rasm yo'q bo'lsa, placeholder qaytarish
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'placeholder.jpg')


# ... [Boshqa routelar (books, book_detail, error handlers) oldingidek] ...
@app.route("/books")
def books():
    return redirect(url_for('materials', material_type='book'))

@app.route("/book/<int:book_id>")
def book_detail(book_id):
    return redirect(url_for('material_detail', material_id=book_id))

@app.errorhandler(404)
def page_not_found(e):
    flash("❌ Sahifa topilmadi")
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(e):
    logging.error(f"Server xatosi: {e}", exc_info=True)
    flash("❌ Server xatosi")
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5050))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = not IS_PRODUCTION
    logging.info(f"🚀 Server {host}:{port} da ishga tushdi (debug={debug})")
    app.run(host=host, port=port, debug=debug)
