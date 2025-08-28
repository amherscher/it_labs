from flask import Flask, request, jsonify
import psycopg2, os

DB_DSN = os.getenv("DB_DSN", "dbname=lawnstore user=lawnuser password=REPLACE_ME host=127.0.0.1")

app = Flask(__name__)

def db():
    return psycopg2.connect(DB_DSN)

@app.get("/items")
def list_items():
    q = request.args.get("q", "")
    with db() as conn, conn.cursor() as cur:
        if q:
            cur.execute("""
                SELECT id, sku, name, quantity, price_cents
                FROM items
                WHERE to_tsvector('english', name) @@ plainto_tsquery(%s)
                ORDER BY name
            """, (q,))
        else:
            cur.execute("SELECT id, sku, name, quantity, price_cents FROM items ORDER BY name")
        rows = cur.fetchall()
    return jsonify([dict(id=r[0], sku=r[1], name=r[2], quantity=r[3], price_cents=r[4]) for r in rows])

@app.post("/items")
def create_item():
    data = request.get_json(force=True)
    for field in ("sku","name"):
        if not data.get(field):
            return {"error": f"'{field}' required"}, 400
    qty = int(data.get("quantity", 0))
    price = int(data.get("price_cents", 0))
    with db() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO items (sku, name, quantity, price_cents)
            VALUES (%s,%s,%s,%s) RETURNING id
        """, (data["sku"], data["name"], qty, price))
        new_id = cur.fetchone()[0]
    return {"id": new_id}, 201

if __name__ == "__main__":
    app.run(debug=True)
