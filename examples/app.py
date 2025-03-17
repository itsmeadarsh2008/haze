from flask import Flask, request, redirect, session, render_template_string
import secrets
import sys
import os

# Add the parent directory to the path so we can import the haze module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import haze

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)

# Configure Haze
haze.use(
    base_url="http://localhost:5000",  # For local development
    magic_link_path="/auth/verify",
    secret_key=app.secret_key,
)

# Simple in-memory storage for demo purposes
token_store = {}


@haze.storage
def store_token(token_id, data=None):
    if data is None:
        return token_store.get(token_id)
    token_store[token_id] = data
    return data


LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Haze Demo - Login</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
        .container { border: 1px solid #ddd; padding: 20px; border-radius: 5px; }
        input, button { padding: 10px; margin: 10px 0; width: 100%; }
        button { background: #4CAF50; color: white; border: none; cursor: pointer; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Haze Magic Link Authentication Demo</h1>
        <form method="POST" action="/login">
            <input type="email" name="email" placeholder="Enter your email" required>
            <button type="submit">Send Magic Link</button>
        </form>
        {% if error %}
            <p class="error">{{ error }}</p>
        {% endif %}
        {% if link %}
            <div class="success">
                <p>Magic link generated:</p>
                <p><a href="{{ link }}">{{ link }}</a></p>
                <p><small>(In a real app, this would be sent via email)</small></p>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Haze Demo - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
        .container { border: 1px solid #ddd; padding: 20px; border-radius: 5px; }
        button { padding: 10px; margin: 10px 0; background: #f44336; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome, {{ user_id }}!</h1>
        <p>You have been successfully authenticated with Haze magic link.</p>
        <form action="/logout" method="POST">
            <button type="submit">Logout</button>
        </form>
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    if session.get("authenticated"):
        return redirect("/dashboard")
    return render_template_string(LOGIN_TEMPLATE)


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    if not email:
        return render_template_string(LOGIN_TEMPLATE, error="Email is required")

    # Generate magic link
    link = haze.generate(user_id=email, metadata={"email": email})

    # In a real app, send this link via email
    # For demo, we'll display it on the page
    return render_template_string(LOGIN_TEMPLATE, link=link)


@app.route("/auth/verify")
def verify():
    token_id = request.args.get("token_id")
    signature = request.args.get("signature")

    if not token_id or not signature:
        return render_template_string(LOGIN_TEMPLATE, error="Invalid magic link")

    try:
        user_data = haze.verify(token_id, signature)
        # Set session
        session["user_id"] = user_data["user_id"]
        session["authenticated"] = True

        # Redirect to dashboard
        return redirect("/dashboard")
    except Exception as e:
        return render_template_string(LOGIN_TEMPLATE, error=str(e))


@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect("/")

    return render_template_string(DASHBOARD_TEMPLATE, user_id=session.get("user_id"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
