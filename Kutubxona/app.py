from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import datetime
import logging

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ========================
# KONFIGURATSIYA
# ========================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_PATH = os.path.join(BASE_DIR, 'data.db')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))  # 50MB default
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')

# Session xavfsizligi
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=86400  # 24 soat
)

# Fayl turlari uchun ruxsat etilgan kengaytmalar
ALLOWED_EXTENSIONS = {
    'book': {'pdf', 'epub', 'mobi', 'djvu', 'fb2', 'doc', 'docx', 'txt'},
    'app': {'apk', 'exe', 'msi', 'dmg', 'deb', 'rpm', 'zip'},
    'image': {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'},
    'video': {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'mpeg'}
}

# ========================
# DATABASE FUNKSIYALARI
# ========================
def get_db():
    """Ma'lumotlar bazasiga ulanish"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Ma'lumotlar bazasini yaratish va boshlang'ich ma'lumotlarni qo'shish"""
    db = get_db()
    cur = db.cursor()
    
    # Users jadval - admin_level qo'shildi (0=oddiy, 1=oddiy admin, 2=bosh admin)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL, 
      email TEXT UNIQUE NOT NULL, 
      password TEXT NOT NULL, 
      admin_level INTEGER DEFAULT 0,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Materials jadval (books o'rniga)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS materials (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL, 
      author TEXT, 
      description TEXT, 
      filename TEXT, 
      material_type TEXT NOT NULL,
      created_at TEXT NOT NULL,
      uploaded_by INTEGER NOT NULL,
      view_count INTEGER DEFAULT 0,
      FOREIGN KEY (uploaded_by) REFERENCES users(id)
    )''')
    
    # Notifications jadval
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
    
    # View history jadval - statistika uchun
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
    
    # Bosh adminni yaratish (agar mavjud bo'lmasa)
    cur.execute("SELECT id FROM users WHERE email=?", ('admin@local',))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (name, email, password, admin_level) VALUES (?,?,?,?)",
                    ("Сардори админ", "admin@local", generate_password_hash("admin123"), 2))
        db.commit()
        print("✅ Сардори маъмурӣ: admin@local / admin123")
    
    db.close()

# ========================
# HELPER FUNKSIYALAR
# ========================
def current_user():
    """Hozirgi foydalanuvchini olish"""
    if not session.get('user_id'):
        return None
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    db.close()
    return user

def login_required(f):
    """Faqat kirgan foydalanuvchilar uchun"""
    from functools import wraps
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get('user_id'):
            flash("⚠️ Илтимос аввал тизимба дароид!")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    """Faqat adminlar uchun (oddiy yoki bosh)"""
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
    """Faqat bosh admin uchun"""
    from functools import wraps
    @wraps(f)
    def wrap(*args, **kwargs):
        user = current_user()
        if not user or user['admin_level'] < 2:
            flash("⚠️ Танҳо барои мудири асосӣ")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrap

def allowed_file(filename, material_type):
    """Faylni tekshirish"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS.get(material_type, set())

# ========================
# UMUMIY SAHIFALAR
# ========================
@app.route("/")
def index():
    """Bosh sahifa - statistika bilan"""
    db = get_db()
    stats = {
        'books': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='book'").fetchone()['c'],
        'apps': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='app'").fetchone()['c'],
        'images': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='image'").fetchone()['c'],
        'videos': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='video'").fetchone()['c'],
    }
    db.close()
    return render_template("index.html", stats=stats)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Ro'yxatdan o'tish"""
    if request.method == "POST":
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Validatsiya
        if not name or len(name) < 3:
            flash("❌ Ном бояд ҳадди аққал 3 аломат дошта бошад.")
            return redirect(url_for('register'))
        
        if not email or '@' not in email:
            flash("❌ Лутфан, суроғаи почтаи электронии дурустро ворид кунед.")
            return redirect(url_for('register'))
        
        if not password or len(password) < 6:
            flash("❌ Парол бояд ҳадди аққал 6 аломат дароз бошад")
            return redirect(url_for('register'))
        
        db = get_db()
        try:
            db.execute("INSERT INTO users (name, email, password, admin_level) VALUES (?,?,?,?)",
                       (name, email, generate_password_hash(password), 0))
            db.commit()
            flash("✅ Шумо бомуваффақият сабти ном шудед! Акнун шумо метавонед ворид шавед.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("❌ Ин имэйл аллакай қайд карда шуда аст.")
            return redirect(url_for('register'))
        finally:
            db.close()
    
    return render_template("register.html")

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

# ========================
# MATERIALLAR SAHIFALARI
# ========================
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
    """Material tafsilotlari"""
    db = get_db()
    
    # Materialni olish
    material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    
    if not material:
        db.close()
        abort(404)
    
    # Ko'rish sonini oshirish
    db.execute("UPDATE materials SET view_count = view_count + 1 WHERE id=?", (material_id,))
    
    # Agar foydalanuvchi kirgan bo'lsa, tarixga qo'shish
    if session.get('user_id'):
        db.execute(
            "INSERT INTO view_history (material_id, user_id, viewed_at) VALUES (?,?,?)",
            (material_id, session['user_id'], datetime.datetime.utcnow().isoformat())
        )
    else:
        # Mehmon foydalanuvchi uchun ham saqlaymiz (user_id = NULL)
        db.execute(
            "INSERT INTO view_history (material_id, user_id, viewed_at) VALUES (?,?,?)",
            (material_id, None, datetime.datetime.utcnow().isoformat())
        )
    
    db.commit()
    
    # Yuklagan foydalanuvchi ma'lumotini olish
    uploader = None
    if material['uploaded_by']:
        uploader = db.execute(
            "SELECT name FROM users WHERE id=?", 
            (material['uploaded_by'],)
        ).fetchone()
    
    db.close()
    
    return render_template("material_detail.html", material=material, uploader=uploader)

@app.route("/download/<path:filename>")
def download_file(filename):
    """Faylni yuklab olish"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        flash(f"❌ Хатогии зеркашӣ кардани файл: {str(e)}")
        return redirect(url_for('materials'))

# ========================
# ADMIN PANELI
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
    """Yangi material qo'shish"""
    user = current_user()
    
    material_type = request.form.get('material_type', 'book')
    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()
    description = request.form.get('description', '').strip()
    uploaded_file = request.files.get('file')
    
    # Oddiy admin faqat book va app yuklashi mumkin
    if user['admin_level'] == 1 and material_type not in ['book', 'app']:
        flash("⚠️ Шумо метавонед танҳо китобҳо ва барномаҳоро зеркашӣ кунед")
        return redirect(url_for('admin'))
    
    # Validatsiya
    if not title:
        flash("❌ Унвон лозим аст")
        return redirect(url_for('admin'))
    
    # Fayl saqlash
    filename = None
    if uploaded_file and uploaded_file.filename:
        if allowed_file(uploaded_file.filename, material_type):
            filename = secure_filename(uploaded_file.filename)
            # Agar bir xil nomli fayl bo'lsa, yangi nom berish
            base_name = filename
            counter = 1
            while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                name, ext = os.path.splitext(base_name)
                filename = f"{name}_{counter}{ext}"
                counter += 1
            
            saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(saved_path)
        else:
            flash(f"❌ Навъи файл барои '{material_type}' мувофиқ нест")
            return redirect(url_for('admin'))
    
    # Ma'lumotlar bazasiga qo'shish
    db = get_db()
    db.execute(
        "INSERT INTO materials (title, author, description, filename, material_type, created_at, uploaded_by) VALUES (?,?,?,?,?,?,?)",
        (title, author, description, filename, material_type, datetime.datetime.utcnow().isoformat(), user['id'])
    )
    db.commit()
    db.close()
    
    flash("✅ Мавод муваффақияти қӯш шуд")
    return redirect(url_for('admin'))

@app.route("/admin/material/<int:material_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_material(material_id):
    """Materialni tahrirlash"""
    user = current_user()
    db = get_db()
    
    material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    
    if not material:
        db.close()
        abort(404)
    
    # Oddiy admin faqat o'z materialini tahrirlaydi
    if user['admin_level'] == 1 and material['uploaded_by'] != user['id']:
        flash("⚠️ Шумо фақат маводи ҳудатонро таҳрир карда метавонид")
        db.close()
        return redirect(url_for('admin'))
    
    if request.method == "POST":
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        description = request.form.get('description', '').strip()
        uploaded_file = request.files.get('file')
        
        if not title:
            flash("❌ Унвон лозим аст")
            return redirect(url_for('admin_edit_material', material_id=material_id))
        
        # Yangi fayl yuklangan bo'lsa
        if uploaded_file and uploaded_file.filename:
            if allowed_file(uploaded_file.filename, material['material_type']):
                # Eski faylni o'chirish
                if material['filename']:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], material['filename'])
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                        except Exception:
                            pass
                
                # Yangi faylni saqlash
                filename = secure_filename(uploaded_file.filename)
                base_name = filename
                counter = 1
                while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                    name, ext = os.path.splitext(base_name)
                    filename = f"{name}_{counter}{ext}"
                    counter += 1
                
                saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                uploaded_file.save(saved_path)
                
                db.execute(
                    "UPDATE materials SET title=?, author=?, description=?, filename=? WHERE id=?",
                    (title, author, description, filename, material_id)
                )
            else:
                flash("❌ Навъи мавод дуруст не")
                db.close()
                return redirect(url_for('admin_edit_material', material_id=material_id))
        else:
            # Fayl yuklanmagan, faqat ma'lumotlarni yangilash
            db.execute(
                "UPDATE materials SET title=?, author=?, description=? WHERE id=?",
                (title, author, description, material_id)
            )
        
        db.commit()
        db.close()
        flash("✅ Мавод муваффақияти таҳрир шуд")
        return redirect(url_for('admin'))
    
    db.close()
    return render_template("admin_edit_material.html", material=material)

@app.route("/admin/material/<int:material_id>/delete")
@admin_required
def admin_delete_material(material_id):
    """Materialni o'chirish"""
    user = current_user()
    db = get_db()
    
    material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    
    if not material:
        db.close()
        abort(404)
    
    # Oddiy admin faqat o'z materialini o'chiradi
    if user['admin_level'] == 1 and material['uploaded_by'] != user['id']:
        flash("⚠️ Шумо фақат танҳо маводи худатонро нест карда метавонед")
        db.close()
        return redirect(url_for('admin'))
    
    # Faylni o'chirish
    if material['filename']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], material['filename'])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    
    # Bazadan o'chirish
    db.execute("DELETE FROM materials WHERE id=?", (material_id,))
    db.execute("DELETE FROM view_history WHERE material_id=?", (material_id,))
    db.commit()
    db.close()
    
    flash("✅ Мавод муваффақияти нест карда шуд")
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

# ========================
# BILDIRISHNOMALAR
# ========================
@app.route("/notifications")
@login_required
def notifications():
    """Foydalanuvchi bildirishnomalarini ko'rish"""
    db = get_db()
    notes = db.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC", 
        (session['user_id'],)
    ).fetchall()
    db.close()
    return render_template("notifications.html", notes=notes)

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
        (1, f"Javob: {session.get('user_name')}", text, datetime.datetime.utcnow().isoformat())
    )
    db.commit()
    db.close()
    
    flash("✅ Ҷавоб фиристода шуд")
    return redirect(url_for('notifications'))

# ========================
# API ENDPOINTLAR
# ========================
@app.route("/api/tutorial-seen", methods=["POST"])
def tutorial_seen():
    """Tutorial ko'rilganini belgilash"""
    return jsonify({"status": "ok"})

@app.route("/health")
def health_check():
    """Railway health check endpoint"""
    try:
        # Database tekshirish
        db = get_db()
        db.execute("SELECT 1").fetchone()
        db.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# ========================
# BACKWARD COMPATIBILITY (Eski linklar uchun)
# ========================
@app.route("/books")
def books():
    """Eski /books linki -> yangi materials/book ga yo'naltirish"""
    return redirect(url_for('materials', material_type='book'))

@app.route("/book/<int:book_id>")
def book_detail(book_id):
    """Eski /book/<id> linki -> yangi material/<id> ga yo'naltirish"""
    return redirect(url_for('material_detail', material_id=book_id))

# ========================
# XATOLIK SAHIFALARI
# ========================
@app.errorhandler(404)
def page_not_found(e):
    """404 sahifa topilmadi"""
    flash("❌ Саҳифа ёфт нашуд")
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(e):
    """500 server xatosi"""
    logging.error(f"Server error: {e}", exc_info=True)
    flash("❌ Хатогии сервер рух дод")
    return redirect(url_for('index'))

# ========================
# DASTURNI ISHGA TUSHIRISH
# ========================
if __name__ == '__main__':
    # Development
    port = int(os.environ.get("PORT", 8090))
    app.run(host="0.0.0.0", port=port)
