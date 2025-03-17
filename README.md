<div align="center">
<img src="https://gist.githubusercontent.com/itsmeadarsh2008/a8b8598c207f00e2795238012d2c5e61/raw/2eeff30b77fff86c12e1a01a60016f0b5d709216/haze.svg" width="200" height="200">
<h1>Haze - Lightning-Fast Magic Link Authentication</h1>
</div>

Haze is a high-performance, easy-to-use Magic Link Authentication service for Python applications. Generate secure authentication links that work across devices with minimal setup.

## Features

- ⚡ **Fast & Efficient** - Optimized core with minimal overhead
- 🔒 **Ultra Secure** - Modern cryptography with JWT
- 🔧 **Highly Configurable** - Like Neovim, but for authentication
- 🧩 **Zero Daemon** - No background processes required
- 📦 **Minimal Dependencies** - Lightweight core with optional extras
- 📱 **Cross-Device Auth** - Click on phone, authenticate on desktop
- 💾 **Pluggable Storage** - Use any database system
- 🦄 **Modern Defaults** - NanoID, JWT, MsgPack by default

## Installation

Since Haze is not available on PyPI, you can install it directly from GitHub:

```bash
# Basic installation (install jwt later, with different package version)
pip install git+https://github.com/itsmeadarsh2008/haze.git@main

# With JWT support (Recommended)
pip install "haze[jwt] @ git+https://github.com/itsmeadarsh2008/haze.git@main"

# With all optional dependencies
pip install "haze [full] @ git+https://github.com/itsmeadarsh2008/haze.git@main"
```

You can also specify individual extra dependencies:

```bash
# Pick and choose what you need
pip install "haze[<optional deps>] git+https://github.com/itsmeadarsh2008/haze.git"
```

## Quick Start

```python
import haze
import secrets

# Configure Haze
haze.use(
    base_url="https://myapp.com",
    magic_link_path="/auth/verify",
    secret_key=secrets.token_urlsafe(32)
)

# Simple in-memory storage for demo purposes
token_store = {}

# Define storage handler
@haze.storage
def store_token(token_id, data=None):
    if data is None:
        return token_store.get(token_id)
    token_store[token_id] = data
    return data

# Generate a magic link for a user
link = haze.generate(
    user_id="user123",
    metadata={"name": "John Doe", "email": "john@example.com"}
)
print(f"Magic Link: {link}")

# Verify the magic link
# This is typically done in your web endpoint
@app.route("/auth/verify")
def verify_link():
    token_id = request.args.get("token_id")
    signature = request.args.get("signature")

    try:
        user_data = haze.verify(token_id, signature)
        # Authentication successful
        # Set session, JWT, etc.
        return {"success": True, "user": user_data}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Advanced Usage

### Custom Configuration

```python
haze.use(
    # Base settings
    base_url="https://myapp.com",
    magic_link_path="/auth/magic",
    link_expiry=3600,  # 1 hour
    allow_reuse=False,  # One-time use by default

    # Token settings
    token_provider="jwt",
    jwt_algorithm="HS256",  # or RS256, ES256
    
    # ID generation
    id_generator="nanoid",  # or "uuid"
    nanoid_size=21,

    # Format settings
    serialization_format="msgpack"  # or "json"
)
```

### Using with JWT

```python
import secrets

# Generate a secure key
secret_key = secrets.token_urlsafe(32)

# Configure Haze to use JWT with HMAC
haze.use(
    token_provider="jwt",
    jwt_algorithm="HS256",
    secret_key=secret_key
)
```

### Using with Asymmetric Keys (JWT)

```python
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Generate key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()

# Configure Haze
haze.use(
    token_provider="jwt",
    jwt_algorithm="RS256",
    private_key=private_key,
    public_key=public_key
)
```

### Database Integration Examples

#### With SQLAlchemy

```python
from sqlalchemy import create_engine, Column, String, Integer, Boolean, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Setup database
Base = declarative_base()
engine = create_engine("sqlite:///haze_tokens.db")
Session = sessionmaker(bind=engine)

class Token(Base):
    __tablename__ = "tokens"

    token_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    exp = Column(Integer, nullable=False)
    created_at = Column(Integer, nullable=False)
    metadata = Column(JSON, nullable=True)
    consumed = Column(Boolean, default=False)

Base.metadata.create_all(engine)

# Setup Haze storage handler
@haze.storage
def store_token(token_id, data=None):
    session = Session()
    try:
        if data is None:
            # Retrieve token
            token = session.query(Token).filter_by(token_id=token_id).first()
            if not token:
                return None
            return {
                "user_id": token.user_id,
                "exp": token.exp,
                "created_at": token.created_at,
                "metadata": token.metadata,
                "consumed": token.consumed
            }
        else:
            # Create or update token
            token = session.query(Token).filter_by(token_id=token_id).first()
            if token:
                # Update existing token
                token.user_id = data["user_id"]
                token.exp = data["exp"]
                token.created_at = data.get("created_at")
                token.metadata = data.get("metadata")
                token.consumed = data.get("consumed", False)
            else:
                # Create new token
                token = Token(
                    token_id=token_id,
                    user_id=data["user_id"],
                    exp=data["exp"],
                    created_at=data.get("created_at"),
                    metadata=data.get("metadata"),
                    consumed=data.get("consumed", False)
                )
                session.add(token)

            session.commit()
            return data
    finally:
        session.close()
```

#### With Redis

```python
import redis
import json
import time

# Setup Redis connection
r = redis.Redis(host='localhost', port=6379, db=0)

@haze.storage
def store_token(token_id, data=None):
    key = f"haze:token:{token_id}"
    if data is None:
        # Retrieve token
        token_data = r.get(key)
        if not token_data:
            return None
        return json.loads(token_data)
    else:
        # Store token with expiration
        ttl = data["exp"] - int(time.time())
        r.setex(key, ttl, json.dumps(data))
        return data
```

### Event Handlers

Haze provides hooks for various authentication events:

```python
# Called when a link is verified
@haze.verification
def on_verification(user_id, token_data):
    print(f"User {user_id} verified with token: {token_data['jti']}")
    # Update last login time, etc.

# Called when a magic link is clicked
@haze.onclick
def on_link_clicked(user_id, user_data):
    print(f"User {user_id} clicked magic link")
    # Track analytics, etc.
```

### Using with Popular Web Frameworks

#### Flask Example

```python
from flask import Flask, request, redirect, session
import haze
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)

# Configure Haze
haze.use(
    base_url="http://localhost:5000",  # For local development
    magic_link_path="/auth/verify",
    secret_key=app.secret_key
)

# Simple in-memory storage for demo purposes
token_store = {}

@haze.storage
def store_token(token_id, data=None):
    if data is None:
        return token_store.get(token_id)
    token_store[token_id] = data
    return data

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    if not email:
        return {"error": "Email required"}, 400

    # Generate magic link
    link = haze.generate(
        user_id=email,
        metadata={"email": email}
    )

    # In a real app, send this link via email
    # For demo, we'll just return it
    return {"link": link}

@app.route("/auth/verify")
def verify():
    token_id = request.args.get("token_id")
    signature = request.args.get("signature")

    try:
        user_data = haze.verify(token_id, signature)
        # Set session
        session["user_id"] = user_data["user_id"]
        session["authenticated"] = True

        # Redirect to dashboard
        return redirect("/dashboard")
    except Exception as e:
        return {"error": str(e)}, 400

@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect("/login")

    return f"Welcome, {session.get('user_id')}!"
```

#### FastAPI Example

```python
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
import secrets
import haze

app = FastAPI()

# Configure Haze
haze.use(
    base_url="http://localhost:8000",  # For local development
    magic_link_path="/auth/verify",
    secret_key=secrets.token_urlsafe(32)
)

# Simple in-memory storage
token_store = {}

@haze.storage
def store_token(token_id, data=None):
    if data is None:
        return token_store.get(token_id)
    token_store[token_id] = data
    return data

class LoginRequest(BaseModel):
    email: EmailStr

@app.post("/login")
async def login(request: LoginRequest):
    # Generate magic link
    link = haze.generate(
        user_id=request.email,
        metadata={"email": request.email}
    )

    # In a real app, send this link via email
    return {"link": link}

@app.get("/auth/verify")
async def verify(token_id: str, signature: str, response: Response):
    try:
        user_data = haze.verify(token_id, signature)

        # Set cookie for authentication
        response.set_cookie(
            key="session_token",
            value=user_data["user_id"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )

        return RedirectResponse(url="/dashboard")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/dashboard")
async def dashboard(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/login")

    return {"message": f"Welcome, {session_token}!"}
```

## Security Best Practices

1. **Always use HTTPS** for production environments
2. **Set appropriate token expiry times** - shorter is better
3. **Rotate your secret keys periodically**
4. **Use asymmetric cryptography** (JWT with RSA/ECDSA) for increased security
5. **Implement rate limiting** to prevent brute force attacks
6. **Store tokens securely** in a database with proper encryption
7. **Enable one-time use** for magic links by setting `allow_reuse=False`

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError" for optional dependencies

```bash
pip install "haze[full] @ git+https://github.com/itsmeadarsh2008/haze.git"
```

#### "ConfigurationError: secret_key must be set"

Ensure you've set a secure secret key with `haze.use(secret_key=...)`.

#### "ValidationError: Token expired"

The magic link has expired. Generate a new one or increase the `link_expiry` setting.

#### "ValidationError: Token not found"

The token doesn't exist in storage. Check your storage handler implementation.

#### "ValidationError: Invalid signature"

The signature verification failed. This could indicate a tampered link or configuration issues.
