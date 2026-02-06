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

## 🛠️ Texnologiyalar

- **Backend:** Flask 3.0.0
- **Database:** SQLite (development) / PostgreSQL (production)
- **Frontend:** HTML5, CSS3, JavaScript

---

## 🔧 Konfiguratsiya

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

**Halimjon**

- GitHub: [@OnOlam](https://github.com/OnOlam)
- Loyiha: [Donishgoh](https://github.com/OnOlam/Donishgoh)
