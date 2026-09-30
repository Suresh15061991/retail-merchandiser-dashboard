# Retail Merchandiser LIVE System

## Run locally
1. Install Python 3.11+.
2. Open terminal in this folder.
3. `pip install -r requirements.txt`
4. `uvicorn app:app --reload`
5. Open `http://localhost:8000/docs` for API testing.
6. Open `index.html` in a browser.

## Production
Deploy `app.py` with PostgreSQL (replace SQLite), HTTPS, authentication, object storage for uploads, and a hosted frontend. The API is already separated so the frontend can be hosted independently.

## Data
Upload Excel or CSV. The API maps common retail column names automatically. For your MASTER RAW DATA, the mapping can be finalized after seeing the real headers.
