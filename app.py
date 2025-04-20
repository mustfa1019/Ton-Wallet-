
from flask import Flask, request, redirect, session, url_for, render_template_string
import stripe
from dotenv import load_dotenv
import os

# تحميل المفاتيح من ملف .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # استخدم قيمة عشوائية لحماية الجلسات

# تحميل مفاتيح Stripe من المتغيرات البيئية
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# تتبع المستخدمين في حالة عدم استخدام قاعدة بيانات
users = {}
user_ips = {}  # لتتبع الـ IP الخاص بكل مستخدم
user_count = 0  # لتتبع عدد الأشخاص الذين استفادوا من العرض

# HTML templates
base_style = """
<style>
    * { box-sizing: border-box; }
    body {
        margin: 0;
        font-family: 'Segoe UI', sans-serif;
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        color: white;
        text-align: center;
        padding: 20px;
        zoom: 1.5;
    }
    h1, h2, h3 { color: #00d2ff; margin: 10px 0; }
    .btn {
        background-color: #1e90ff;
        border: none;
        padding: 12px 25px;
        font-size: 1em;
        color: white;
        border-radius: 10px;
        margin: 10px;
        cursor: pointer;
    }
    .card {
        background: #1c1c1c;
        border-radius: 15px;
        padding: 20px;
        margin: 20px auto;
        width: 300px;
        box-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    input {
        padding: 10px;
        border-radius: 8px;
        border: none;
        width: 80%;
        margin: 10px 0;
    }
</style>
"""

@app.route("/")
def home():
    return render_template_string(base_style + """
    <h1>Welcome to Ton Wallet</h1>
    <div class="card">
        <h2>Your Digital Wallet</h2>
        <a href="/login"><button class="btn">Login</button></a>
        <a href="/register"><button class="btn">Create Account</button></a>
    </div>
    """)

@app.route("/register", methods=["GET", "POST"])
def register():
    global user_count
    ip_address = request.remote_addr
    if ip_address in user_ips:
        return "You already created an account from this IP."
    if user_count >= 4:
        return "The promotion has ended."
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users:
            return "User already exists, please login."
        users[username] = {"password": password, "balance": 0}
        session["user"] = username
        user_ips[ip_address] = username
        user_count += 1
        users[username]["balance"] += 0.01
        return redirect("/wallet")
    return render_template_string(base_style + """
    <h2>Create Account</h2>
    <form method="post" class="card">
        <input name="username" placeholder="Username" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button class="btn" type="submit">Register</button>
    </form>
    """)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username]["password"] == password:
            session["user"] = username
            return redirect("/wallet")
        return "Invalid credentials"
    return render_template_string(base_style + """
    <h2>Login</h2>
    <form method="post" class="card">
        <input name="username" placeholder="Username" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button class="btn" type="submit">Login</button>
    </form>
    """)

@app.route("/wallet")
def wallet():
    if "user" not in session:
        return redirect("/")
    username = session["user"]
    balance = users[username]["balance"]
    return render_template_string(base_style + f"""
    <h1>Ton Wallet</h1>
    <div class="card">
        <h2>Hello, {username}</h2>
        <h3>Balance: ${balance:.2f}</h3>
        <a href="/charge"><button class="btn">Charge Wallet</button></a>
        <a href="/transfer"><button class="btn">Transfer</button></a>
    </div>
    """)

@app.route("/charge", methods=["GET", "POST"])
def charge():
    if request.method == "POST":
        amount = int(float(request.form["amount"]) * 100)
        session["amount"] = amount
        session["username"] = session["user"]
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'Ton Wallet Balance'},
                    'unit_amount': amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('success', _external=True),
            cancel_url=url_for('wallet', _external=True),
        )
        return redirect(checkout_session.url)
    return render_template_string(base_style + """
    <h2>Charge Wallet</h2>
    <form method="post" class="card">
        <input name="amount" placeholder="Amount in USD" required><br>
        <button class="btn" type="submit">Charge with Stripe</button>
    </form>
    """)

@app.route("/success")
def success():
    username = session.get("username")
    amount = session.get("amount")
    if username and amount:
        users[username]["balance"] += amount / 100
    session.pop("amount", None)
    session.pop("username", None)
    return redirect("/wallet")

@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    if "user" not in session:
        return redirect("/")
    if request.method == "POST":
        from_user = session["user"]
        to_user = request.form["to"]
        amount = float(request.form["amount"])
        if to_user in users and users[from_user]["balance"] >= amount:
            users[from_user]["balance"] -= amount
            users[to_user]["balance"] += amount
            return redirect("/wallet")
        else:
            return "Invalid transfer."
    return render_template_string(base_style + """
    <h2>Transfer Balance</h2>
    <form method="post" class="card">
        <input name="to" placeholder="Receiver Username" required><br>
        <input name="amount" placeholder="Amount" required><br>
        <button class="btn" type="submit">Transfer</button>
    </form>
    """)

if __name__ == "__main__":
    app.run(debug=True)
