from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

IS_PRODUCTION = any([
    os.environ.get('RAILWAY_ENVIRONMENT'),
    os.environ.get('DYNO'),
    os.environ.get('PORT') and os.environ.get('FLASK_ENV') != 'development'
])

if IS_PRODUCTION:
    DB_PATH = '/tmp/data.db'
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    DB_PATH = os.path.join(BASE_DIR, 'data.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=86400
)

ALLOWED_EXTENSIONS = {
    'book': {'pdf', 'epub', 'mobi', 'djvu', 'fb2', 'doc', 'docx', 'txt'},
    'app': {'apk', 'exe', 'msi', 'dmg', 'deb', 'rpm', 'zip'},
    'image': {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'},
    'video': {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'mpeg'}
}

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        db = get_db()
        cur = db.cursor()
        
        cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            admin_level INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
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
        
        try:
            cur.execute(
                "INSERT INTO users (name, email, password, admin_level) VALUES (?,?,?,?)",
                ("Сардори админ", "admin@local", generate_password_hash("admin123"), 2)
            )
            db.commit()
            print(f"✅ Admin yaratildi! DB: {DB_PATH}")
        except sqlite3.IntegrityError:
            pass
        
        db.close()
        print(f"✅ Database tayyor: {DB_PATH}")
        return True
    except Exception as e:
        print(f"❌ Database xatosi: {str(e)} | Yo'l: {DB_PATH}")
        logging.error(f"init_db failed: {e}", exc_info=True)
        return False

print(f"🌍 Muhit: {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'}")
print(f"📁 DB: {DB_PATH}")
if not init_db():
    print("⚠️  OGHLANISH: Database ishga tushirilmadi!")

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
            flash("⚠️ Илтимос аввал тизимба дароид!")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

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

def allowed_file(filename, material_type):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS.get(material_type, set())

@app.route("/")
def index():
    try:
        db = get_db()
        cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='materials'")
        if not cur.fetchone():
            db.close()
            init_db()
            db = get_db()
        
        stats = {
            'books': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='book'").fetchone()['c'],
            'apps': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='app'").fetchone()['c'],
            'images': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='image'").fetchone()['c'],
            'videos': db.execute("SELECT COUNT(*) as c FROM materials WHERE material_type='video'").fetchone()['c'],
        }
        db.close()
        return render_template("index.html", stats=stats)
    except Exception as e:
        logging.error(f"Index xatosi: {e}")
        flash("⚠️ Tizimda vaqtinchalik muammo. Iltimos, sahifani yangilang.")
        return render_template("index.html", stats={'books':0, 'apps':0, 'images':0, 'videos':0})

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
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
            flash(f"✅ Ҳуш омадед, {user['name']}!")
            return redirect(url_for('index'))
        else:
            flash("❌ Почтаи электронӣ ё пароли нодуруст")
            return redirect(url_for('login'))
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Аз система бромадид")
    return redirect(url_for('index'))

@app.route("/materials")
@app.route("/materials/<material_type>")
def materials(material_type=None):
    db = get_db()
    if material_type and material_type in ['book', 'app', 'image', 'video']:
        rows = db.execute("SELECT * FROM materials WHERE material_type=? ORDER BY id DESC", (material_type,)).fetchall()
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
    return render_template("material_detail.html", material=material, uploader=uploader)

@app.route("/download/<path:filename>")
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        flash(f"❌ Хатогии зеркашӣ кардани файл: {str(e)}")
        return redirect(url_for('materials'))

@app.route("/admin")
@admin_required
def admin():
    user = current_user()
    db = get_db()
    if user['admin_level'] == 1:
        materials = db.execute("SELECT * FROM materials WHERE uploaded_by=? ORDER BY id DESC", (user['id'],)).fetchall()
        users = []
    else:
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
    
    if user['admin_level'] == 1 and material_type not in ['book', 'app']:
        flash("⚠️ Шумо метавонед танҳо китобҳо ва барномаҳоро зеркашӣ кунед")
        return redirect(url_for('admin'))
    
    if not title:
        flash("❌ Унвон лозим аст")
        return redirect(url_for('admin'))
    
    filename = None
    if uploaded_file and uploaded_file.filename:
        if allowed_file(uploaded_file.filename, material_type):
            filename = secure_filename(uploaded_file.filename)
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
    
    db = get_db()
    db.execute("INSERT INTO materials (title, author, description, filename, material_type, created_at, uploaded_by) VALUES (?,?,?,?,?,?,?)",
               (title, author, description, filename, material_type, datetime.datetime.utcnow().isoformat(), user['id']))
    db.commit()
    db.close()
    flash("✅ Мавод муваффақияти қӯш шуд")
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
        
        if uploaded_file and uploaded_file.filename:
            if allowed_file(uploaded_file.filename, material['material_type']):
                if material['filename']:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], material['filename'])
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                        except Exception:
                            pass
                filename = secure_filename(uploaded_file.filename)
                base_name = filename
                counter = 1
                while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                    name, ext = os.path.splitext(base_name)
                    filename = f"{name}_{counter}{ext}"
                    counter += 1
                saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                uploaded_file.save(saved_path)
                db.execute("UPDATE materials SET title=?, author=?, description=?, filename=? WHERE id=?",
                           (title, author, description, filename, material_id))
            else:
                flash("❌ Навъи мавод дуруст не")
                db.close()
                return redirect(url_for('admin_edit_material', material_id=material_id))
        else:
            db.execute("UPDATE materials SET title=?, author=?, description=? WHERE id=?",
                       (title, author, description, material_id))
        
        db.commit()
        db.close()
        flash("✅ Мавод муваффақияти таҳрир шуд")
        return redirect(url_for('admin'))
    
    db.close()
    return render_template("admin_edit_material.html", material=material)

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
        flash("⚠️ Шумо фақат танҳо маводи худатонро нест карда метавонед")
        db.close()
        return redirect(url_for('admin'))
    
    if material['filename']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], material['filename'])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    
    db.execute("DELETE FROM materials WHERE id=?", (material_id,))
    db.execute("DELETE FROM view_history WHERE material_id=?", (material_id,))
    db.commit()
    db.close()
    flash("✅ Мавод муваффақияти нест карда шуд")
    return redirect(url_for('admin'))

@app.route("/admin/material/<int:material_id>/stats")
@admin_required
def admin_material_stats(material_id):
    user = current_user()
    db = get_db()
    material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    if not material:
        db.close()
        abort(404)
    
    if user['admin_level'] == 1 and material['uploaded_by'] != user['id']:
        flash("⚠️ Шумо фақат омори маводи худатонро дида метавонед")
        db.close()
        return redirect(url_for('admin'))
    
    views = db.execute("""
        SELECT view_history.*, users.name 
        FROM view_history 
        LEFT JOIN users ON view_history.user_id = users.id
        WHERE material_id=? 
        ORDER BY viewed_at DESC
    """, (material_id,)).fetchall()
    
    db.close()
    return render_template("admin_material_stats.html", material=material, views=views)

@app.route("/admin/user/<int:user_id>/toggle")
@main_admin_required
def admin_toggle_user(user_id):
    db = get_db()
    target_user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not target_user:
        db.close()
        flash("❌ Корбар ёфт нашуд")
        return redirect(url_for('admin'))
    
    if target_user['id'] == session['user_id']:
        db.close()
        flash("⚠️ Шумо наметавонед худро тағир диҳед")
        return redirect(url_for('admin'))
    
    if target_user['admin_level'] == 2:
        db.close()
        flash("⚠️ Шумо дигар администратори асосиро иваз карда наметавонед")
        return redirect(url_for('admin'))
    
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
        
        db.execute("INSERT INTO notifications (user_id, title, message, created_at) VALUES (?,?,?,?)",
                   (user_id, title, message, datetime.datetime.utcnow().isoformat()))
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
    return render_template("notifications.html", notes=notes)

@app.route("/notify/reply", methods=["POST"])
@login_required
def notify_reply():
    text = request.form.get('text', '').strip()
    if not text:
        flash("❌ Матни хабар бояд ворид карда шавад")
        return redirect(url_for('notifications'))
    
    db = get_db()
    db.execute("INSERT INTO notifications (user_id, title, message, created_at) VALUES (?,?,?,?)",
               (1, f"Javоб: {session.get('user_name')}", text, datetime.datetime.utcnow().isoformat()))
    db.commit()
    db.close()
    flash("✅ Ҷавоб фиристода шуд")
    return redirect(url_for('notifications'))

@app.route("/api/tutorial-seen", methods=["POST"])
def tutorial_seen():
    return jsonify({"status": "ok"})

@app.route("/health")
def health_check():
    try:
        db = get_db()
        tables = db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('users', 'materials')
        """).fetchall()
        db.close()
        if len(tables) < 2:
            init_db()
            return jsonify({"status": "reinitialized"}), 200
        return jsonify({"status": "healthy", "db_path": DB_PATH}), 200
    except Exception as e:
        logging.error(f"Health check xatosi: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route("/books")
def books():
    return redirect(url_for('materials', material_type='book'))

@app.route("/book/<int:book_id>")
def book_detail(book_id):
    return redirect(url_for('material_detail', material_id=book_id))

@app.errorhandler(404)
def page_not_found(e):
    flash("❌ Саҳифа ёфт нашуд")
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(e):
    logging.error(f"Server xatosi: {e}", exc_info=True)
    flash("❌ Хатогии сервер рух дод")
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5050))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = not IS_PRODUCTION
    logging.info(f"🚀 Server {host}:{port} da ishga tushdi (debug={debug})")
    app.run(host=host, port=port, debug=debug)
