# PostgreSQL + Flask (“LawnStore”)

./dbapp.py


**Objective**  
Build a tiny inventory app to practice DB schema design, CRUD operations, simple search, and validation.

---

## Stack
- **PostgreSQL** 14+
- **Python** 3.10+
- **Flask** + `psycopg2-binary` (or `asyncpg` if you prefer)
- Optional: `venv`, `pip-tools`

---

## Setup

### 1) Database
```bash
sudo -u postgres psql -c "CREATE DATABASE lawnstore;"
sudo -u postgres psql -c "CREATE USER lawnuser WITH PASSWORD 'REPLACE_ME';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE lawnstore TO lawnuser;"

#CREATE TABLE IF NOT EXISTS items (
  id SERIAL PRIMARY KEY,
  sku TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 0,
  price_cents INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_items_name ON items USING gin (to_tsvector('english', name));

#Load
psql -U lawnuser -d lawnstore -h localhost -f schema/lawnstore.sql

#App Env
python3 -m venv .venv
source .venv/bin/activate
pip install flask psycopg2-binary


#Run
export DB_DSN="dbname=lawnstore user=lawnuser password=REPLACE_ME host=127.0.0.1"
python app.py
