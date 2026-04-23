# Deploy ke Railway

## 1. Buat project dan service
1. Masuk ke Railway.
2. New Project -> Deploy from GitHub Repo.
3. Pilih repository ini.

Railway akan build otomatis menggunakan `requirements.txt`.

## 2. Tambahkan PostgreSQL di Railway
1. Di project Railway, klik `+ New` -> `Database` -> `PostgreSQL`.
2. Buka PostgreSQL service -> tab `Variables`.
3. Salin `DATABASE_URL` dari PostgreSQL service.

## 3. Set environment variables di service app
Buka service app (bukan database), lalu tambahkan variable berikut:

- `DATABASE_URL` = URL PostgreSQL dari service database Railway
- `SECRET_KEY` = secret random yang kuat
- `GROQ_API_KEY` = API key Groq
- `PLANTID_API_KEY` = API key Plant.id
- `MAX_CONTENT_LENGTH` = `16777216`
- `UPLOAD_FOLDER` = `app/static/uploads`

Opsional:
- `FLASK_ENV` = `production`

## 4. Deploy
Setelah variables disimpan, Railway akan redeploy otomatis.

## 5. Verifikasi
1. Buka URL deploy dari Railway.
2. Coba register/login.
3. Coba fitur chat dan upload analisis.

## Catatan penting
- Jangan commit file `.env` ke repository.
- Untuk local dev, tetap pakai `.env` lokal.
- App sudah membaca `PORT` dari Railway lewat `run.py` dan `gunicorn` start command.
