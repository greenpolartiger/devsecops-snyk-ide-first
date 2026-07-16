import sqlite3
import os
from flask import Flask, render_template_string, request, jsonify
import python_json_logger.json_log  # Vulnerable SCA dependency
import logging

app = Flask(__name__)

# VULN 1: Hardcoded secrets
API_KEY = "sk-1234567890abcdefghijklmnop"
DATABASE_PASSWORD = "admin123"
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Database setup
def init_db():
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, balance REAL)''')
    cursor.execute("INSERT INTO users VALUES (1, 'admin', 'password123', 1000.0)")
    cursor.execute("INSERT INTO users VALUES (2, 'user1', 'user123', 500.0)")
    conn.commit()
    return conn

db = init_db()

# VULN 2: XSS - Unsanitized user input reflected in response
@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html>
    <head><title>Vuln App</title></head>
    <body>
        <h1>Welcome</h1>
        <a href="/search">Search</a> | <a href="/login">Login</a> | <a href="/transfer">Transfer Money</a>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    # VULN: Direct XSS - query injected without sanitization
    html = f'''
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Search Results</h1>
        <p>You searched for: {query}</p>
        <a href="/">Back</a>
    </body>
    </html>
    '''
    return render_template_string(html)

# VULN 3: SQL Injection - Untrusted input in query
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # VULN: SQLi - Direct string concatenation in query
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        cursor = db.cursor()
        try:
            cursor.execute(query)
            user = cursor.fetchone()
            if user:
                return jsonify({'status': 'success', 'message': f'Welcome {user[1]}'})
            else:
                return jsonify({'status': 'error', 'message': 'Invalid credentials'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    
    html = '''
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Login</h1>
        <form method="POST">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <a href="/">Back</a>
    </body>
    </html>
    '''
    return render_template_string(html)

# VULN 4: Business Logic Flaw - Insufficient authorization on fund transfer
@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if request.method == 'POST':
        from_user = request.form.get('from_user', '')
        to_user = request.form.get('to_user', '')
        amount = float(request.form.get('amount', 0))
        
        # VULN: No authentication check - anyone can transfer from any account
        cursor = db.cursor()
        cursor.execute(f"UPDATE users SET balance = balance - {amount} WHERE username = '{from_user}'")
        cursor.execute(f"UPDATE users SET balance = balance + {amount} WHERE username = '{to_user}'")
        db.commit()
        
        return jsonify({'status': 'success', 'message': f'Transferred ${amount} from {from_user} to {to_user}'})
    
    html = '''
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Transfer Money</h1>
        <form method="POST">
            <input name="from_user" placeholder="From User" required>
            <input name="to_user" placeholder="To User" required>
            <input name="amount" type="number" placeholder="Amount" required>
            <button type="submit">Transfer</button>
        </form>
        <a href="/">Back</a>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/api/status')
def api_status():
    # VULN: Sensitive data exposure - API key in response
    return jsonify({'status': 'running', 'api_key': API_KEY, 'db_pass': DATABASE_PASSWORD})

if __name__ == '__main__':
    # VULN: Debug mode enabled in production
    app.run(debug=True, host='0.0.0.0', port=5000)