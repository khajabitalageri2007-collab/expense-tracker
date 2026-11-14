from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "expense_tracker_secret_key"

def connect_db():
    conn = sqlite3.connect("expenses.db")
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = connect_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            amount REAL,
            type TEXT,
            category TEXT,
            date TEXT
        )
    """)

    conn.commit()
    conn.close()

create_tables()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = connect_db()

        try:
            conn.execute(
                "INSERT INTO users(name,email,password) VALUES(?,?,?)",
                (name, email, generate_password_hash(password))
            )
            conn.commit()
            return redirect("/login")
        except sqlite3.IntegrityError:
            return "Email already registered"
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = connect_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect("/dashboard")

        return "Invalid email or password"

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("index.html", name=session["name"])

@app.route("/add", methods=["POST"])
@login_required
def add_transaction():
    data = request.get_json()

    conn = connect_db()
    conn.execute("""
        INSERT INTO transactions
        (user_id,title,amount,type,category,date)
        VALUES(?,?,?,?,?,?)
    """, (
        session["user_id"],
        data["title"],
        float(data["amount"]),
        data["type"],
        data["category"],
        data["date"]
    ))
    conn.commit()
    conn.close()

    return jsonify({"message": "Transaction added successfully"})

@app.route("/transactions")
@login_required
def transactions():
    conn = connect_db()

    rows = conn.execute("""
        SELECT * FROM transactions
        WHERE user_id=?
        ORDER BY date DESC, id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/delete/<int:id>", methods=["DELETE"])
@login_required
def delete_transaction(id):
    conn = connect_db()

    conn.execute("""
        DELETE FROM transactions
        WHERE id=? AND user_id=?
    """, (id, session["user_id"]))

    conn.commit()
    conn.close()

    return jsonify({"message": "Deleted successfully"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)