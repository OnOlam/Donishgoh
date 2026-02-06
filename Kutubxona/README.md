# 📚 Donishgoh - Kitobхona

> Elektron materiallar (kitoblar, ilovalar, rasmlar, videolar) boshqaruv tizimi

## 🎯 Loyiha haqida

**Donishgoh** - bu Flask asosida yaratilgan web-ilova bo'lib, foydalanuvchilarga elektron materiallarni yuklash, boshqarish va almashish imkonini beradi. Sistema 3 darajali admin tizimi, bildirishnomalar va statistika funksiyalariga ega.

### Asosiy imkoniyatlar:
- 📖 **Kitoblar** (PDF, EPUB, MOBI, DJVU, ...)
- 📱 **Ilovalar** (APK, EXE, MSI, DMG, ...)
- 🖼️ **Rasmlar** (JPG, PNG, GIF, SVG, ...)
- 🎬 **Videolar** (MP4, AVI, MKV, MOV, ...)
- 👥 **3 darajali admin tizimi**
- 📊 **Statistika va ko'rish tarixi**
- 🔔 **Bildirishnomalar tizimi**

---

## 🚀 Railway Deployment

Bu loyiha **Railway hosting** uchun tayyor qilingan!

### Tezkor deploy:

1. **GitHub'ga push qiling:**
```bash
git clone https://github.com/OnOlam/Donishgoh.git
cd Donishgoh
git add .
git commit -m "Railway ready"
git push origin main
```

2. **Railway'da deploy qiling:**
   - https://railway.app → New Project
   - Deploy from GitHub → Donishgoh
   - Environment Variables qo'shing:
     ```
     SECRET_KEY=your-random-secret-key-here
     FLASK_ENV=production
     ```

3. **Generate Domain** va ishga tushiring! ✅

**To'liq qo'llanma:** `DEPLOYMENT_QOLLANMA.md` faylini o'qing.

---

## 💻 Local Development

### 1. Repository ni clone qiling:
```bash
git clone https://github.com/OnOlam/Donishgoh.git
cd Donishgoh
```

### 2. Virtual environment yarating:
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Dependencies o'rnating:
```bash
pip install -r requirements.txt
```

### 4. Environment variables sozlang:
```bash
cp .env.example .env
# .env faylini tahrirlang
```

### 5. Serverni ishga tushiring:
```bash
python app.py
```

### 6. Brauzerda oching:
```
http://localhost:5050
```

**Default admin:**
- Email: `admin@local`
- Parol: `admin123`

---

## 🛠️ Texnologiyalar

- **Backend:** Flask 3.0.0
- **Database:** SQLite (development) / PostgreSQL (production)
- **Frontend:** HTML5, CSS3, JavaScript
- **Server:** Gunicorn
- **Deployment:** Railway

---

## 📋 Loyiha strukturasi

```
Donishgoh/
├── app.py                 # Asosiy Flask ilova
├── requirements.txt       # Python dependencies
├── Procfile              # Railway start command
├── runtime.txt           # Python version
├── railway.json          # Railway config
├── .env.example          # Environment variables namuna
├── .gitignore
├── README.md
├── static/
│   └── css/
│       └── style.css    # CSS uslublar
└── templates/           # Jinja2 templates
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── materials.html
    ├── material_detail.html
    ├── admin.html
    └── ...
```

---

## 🔧 Konfiguratsiya

### Environment Variables:

| Variable | Izoh | Default | Required |
|----------|------|---------|----------|
| `SECRET_KEY` | Flask session key | - | ✅ |
| `FLASK_ENV` | Environment (production/development) | development | ✅ |
| `PORT` | Server port | 5050 | ❌ |
| `HOST` | Server host | 0.0.0.0 | ❌ |
| `MAX_CONTENT_LENGTH` | Max file size (bytes) | 52428800 (50MB) | ❌ |
| `DATABASE_URL` | PostgreSQL URL | - | ❌ |
| `DB_PATH` | SQLite path | data.db | ❌ |

---

## 🔒 Xavfsizlik

✅ **Qo'llaniladigan himoya:**
- Password hashing (Werkzeug)
- Parametrlangan SQL queries (SQL injection prevention)
- Session cookie xavfsizligi (HTTPOnly, Secure, SameSite)
- File extension validation
- Max file size limit

⚠️ **Tavsiya etiladigan qo'shimchalar:**
- CSRF protection (Flask-WTF)
- Rate limiting (Flask-Limiter)
- HTTPS redirect (Flask-Talisman)
- Email verification

---

## 📊 Database Schema

### Users
- `id` (INTEGER, PRIMARY KEY)
- `name` (TEXT)
- `email` (TEXT, UNIQUE)
- `password` (TEXT, hashed)
- `admin_level` (INTEGER: 0=user, 1=admin, 2=main_admin)
- `created_at` (TEXT)

### Materials
- `id` (INTEGER, PRIMARY KEY)
- `title` (TEXT)
- `author` (TEXT)
- `description` (TEXT)
- `filename` (TEXT)
- `material_type` (TEXT: book/app/image/video)
- `created_at` (TEXT)
- `uploaded_by` (INTEGER, FOREIGN KEY → users.id)
- `view_count` (INTEGER)

### Notifications
- `id` (INTEGER, PRIMARY KEY)
- `user_id` (INTEGER, FOREIGN KEY → users.id)
- `title` (TEXT)
- `message` (TEXT)
- `created_at` (TEXT)
- `is_read` (INTEGER)

### View History
- `id` (INTEGER, PRIMARY KEY)
- `material_id` (INTEGER, FOREIGN KEY → materials.id)
- `user_id` (INTEGER, FOREIGN KEY → users.id)
- `viewed_at` (TEXT)

---

## 🎨 Frontend

**CSS Framework:** Custom CSS (Dark theme)  
**Icons:** Emoji  
**Responsive:** Ha ✅

**Sahifalar:**
- Bosh sahifa (statistika)
- Materiallar ro'yxati
- Material detallari
- Admin panel
- Login / Register
- Bildirishnomalar

---

## 🐛 Muammolarni bartaraf qilish

### Muammo: "Module not found"
**Yechim:**
```bash
pip install -r requirements.txt
```

### Muammo: "Database is locked"
**Yechim:**
```bash
# SQLite file ni o'chiring va qayta yarating
rm data.db
python app.py
```

### Muammo: "Port already in use"
**Yechim:**
```bash
# Boshqa port ishlatish
export PORT=5051
python app.py
```

### Muammo: "500 Internal Server Error"
**Yechim:**
```bash
# Log-larni ko'ring
tail -f logs/app.log

# Yoki debug mode yoqing
export FLASK_ENV=development
python app.py
```

---

## 📝 TODO

- [ ] PostgreSQL migration
- [ ] Cloudinary integration (file storage)
- [ ] CSRF protection
- [ ] Rate limiting
- [ ] Email verification
- [ ] Password reset
- [ ] Search functionality
- [ ] Pagination
- [ ] Unit tests
- [ ] CI/CD pipeline

---

## 📄 License

Bu loyiha shaxsiy ta'lim maqsadlari uchun yaratilgan.

---

## 👤 Muallif

**Hasanov Halimjon**

- GitHub: [@OnOlam](https://github.com/OnOlam)
- Loyiha: [Donishgoh](https://github.com/OnOlam/Donishgoh)

---

## 🙏 Minnatdorchilik

- Flask framework
- Railway hosting
- Stack Overflow community

---

## 📞 Aloqa

Savollar yoki muammolar bo'lsa:
- GitHub Issues: https://github.com/OnOlam/Donishgoh/issues
- Telegram: @your_telegram

---

**🚀 Omad tilayman deploying uchun!**
