from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_PATH = os.path.join(BASE_DIR, 'data.db')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "change_this_secret_to_safe_value"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT, email TEXT UNIQUE, password TEXT, is_admin INTEGER DEFAULT 0
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT, author TEXT, description TEXT, filename TEXT, created_at TEXT
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER, title TEXT, message TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    db.commit()
    # create default admin if not exists
    cur.execute("SELECT id FROM users WHERE email='admin@local'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (name,email,password,is_admin) VALUES (?,?,?,?)",
                    ("Admin","admin@local", generate_password_hash("admin123"),1))
        db.commit()
    db.close()

init_db()

# helpers
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
    def wrap(*a, **kw):
        if not session.get('user_id'):
            flash("Iltimos tizimga kiring")
            return redirect(url_for('login'))
        return f(*a, **kw)
    return wrap

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrap(*a, **kw):
        if not session.get('is_admin'):
            flash("Admin huquqi kerak")
            return redirect(url_for('index'))
        return f(*a, **kw)
    return wrap

# routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        if not name or not email or not password:
            flash("Barcha maydonlar to'ldirilishi shart")
            return redirect(url_for('register'))
        db = get_db()
        try:
            db.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                       (name,email, generate_password_hash(password)))
            db.commit()
            flash("Ro'yxatdan o'tdingiz. Endi kirishingiz mumkin")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Bu email bilan ro'yxatdan o'tilgan")
            return redirect(url_for('register'))
        finally:
            db.close()
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email = request.form['email'].strip().lower()
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id']=user['id']
            session['user_name']=user['name']
            session['is_admin']=bool(user['is_admin'])
            flash("Muvaffaqiyatli kirdingiz")
            return redirect(url_for('index'))
        else:
            flash("Email yoki parol xato")
            return redirect(url_for('login'))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Chiqdingiz")
    return redirect(url_for('index'))

@app.route("/books")
def books():
    db = get_db()
    rows = db.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    db.close()
    return render_template("books.html", books=rows)

@app.route("/book/<int:book_id>")
def book_detail(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    db.close()
    if not row:
        abort(404)
    return render_template("book_detail.html", book=row)

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Admin routes
@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    users = db.execute("SELECT * FROM users").fetchall()
    books = db.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    db.close()
    return render_template("admin.html", users=users, books=books)

@app.route("/admin/add", methods=["POST"])
@admin_required
def admin_add_book():
    title = request.form.get('title','').strip()
    author = request.form.get('author','').strip()
    description = request.form.get('description','').strip()
    f = request.files.get('file')
    filename = None
    if f and f.filename:
        filename = secure_filename(f.filename)
        saved = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(saved)
    db = get_db()
    db.execute("INSERT INTO books (title,author,description,filename,created_at) VALUES (?,?,?,?,?)",
               (title,author,description,filename, datetime.datetime.utcnow().isoformat()))
    db.commit()
    db.close()
    flash("Kitob qo'shildi")
    return redirect(url_for('admin'))

@app.route("/admin/book/<int:book_id>/edit", methods=["GET","POST"])
@admin_required
def admin_edit_book(book_id):
    db = get_db()
    if request.method=="POST":
        title = request.form.get('title','').strip()
        author = request.form.get('author','').strip()
        description = request.form.get('description','').strip()
        f = request.files.get('file')
        filename = None
        if f and f.filename:
            filename = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            db.execute("UPDATE books SET title=?,author=?,description=?,filename=? WHERE id=?",
                       (title,author,description,filename,book_id))
        else:
            db.execute("UPDATE books SET title=?,author=?,description=? WHERE id=?",
                       (title,author,description,book_id))
        db.commit()
        db.close()
        flash("O'zgartirildi")
        return redirect(url_for('admin'))
    book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    db.close()
    if not book:
        abort(404)
    return render_template("admin_edit_book.html", book=book)

@app.route("/admin/book/<int:book_id>/delete")
@admin_required
def admin_delete_book(book_id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if book and book['filename']:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], book['filename']))
        except Exception:
            pass
    db.execute("DELETE FROM books WHERE id=?", (book_id,))
    db.commit()
    db.close()
    flash("Kitob o'chirildi")
    return redirect(url_for('admin'))

@app.route("/admin/user/<int:user_id>/toggle")
@admin_required
def admin_toggle_user(user_id):
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if u:
        db.execute("UPDATE users SET is_admin=? WHERE id=?", (0 if u['is_admin'] else 1, user_id))
        db.commit()
    db.close()
    flash("Foydalanuvchi rol o'zgardi")
    return redirect(url_for('admin'))

@app.route("/admin/notify/<int:user_id>", methods=["GET","POST"])
@admin_required
def admin_notify_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if request.method=="POST":
        title = request.form.get('title','').strip()
        message = request.form.get('message','').strip()
        db.execute("INSERT INTO notifications (user_id,title,message,created_at) VALUES (?,?,?,?)",
                   (user_id,title,message, datetime.datetime.utcnow().isoformat()))
        db.commit()
        db.close()
        flash("Xabar yuborildi")
        return redirect(url_for('admin'))
    db.close()
    if not user:
        abort(404)
    return render_template("admin_notify.html", user=user)

# Notifications for current user
@app.route("/notifications")
@login_required
def notifications():
    db = get_db()
    rows = db.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC", (session['user_id'],)).fetchall()
    db.close()
    return render_template("notifications.html", notes=rows)

# simple API to reply (user can reply to admin in notification thread)
@app.route("/notify/reply", methods=["POST"])
@login_required
def notify_reply():
    nid = request.form.get('nid')
    text = request.form.get('text','').strip()
    db = get_db()
    # store as notification to admin user (id 1)
    db.execute("INSERT INTO notifications (user_id,title,message,created_at) VALUES (?,?,?,?)",
               (1, f"Reply from {session.get('user_name')}", text, datetime.datetime.utcnow().isoformat()))
    db.commit()
    db.close()
    flash("Javob yuborildi")
    return redirect(url_for('notifications'))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
