import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this-in-production'

# Database Setup & Safe Migration
DB_FILE = 'database.db'  # Change if your DB uses another name like 'accounting.db'

def init_db():
    """Ensure schema tables and required columns exist on application start."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create Clients Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            contact_name TEXT,
            email TEXT,
            phone TEXT
        )
    ''')

    # Create Employees Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            role TEXT
        )
    ''')

    # Create Payroll Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            salary REAL DEFAULT 0.0,
            allowances REAL DEFAULT 0.0,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    # Safe Schema Migrations (Add missing columns if table already exists)
    try:
        cursor.execute("ALTER TABLE payroll ADD COLUMN allowances REAL DEFAULT 0.0;")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# Safe url_for Context Processor (Prevents 500 BuildErrors for missing routes)
@app.context_processor
def utility_processor():
    def safe_url_for(endpoint, **values):
        try:
            return url_for(endpoint, **values)
        except Exception:
            return "#"
    return dict(url_for=safe_url_for)

# Helper function for database queries
def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# Routes

@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/clients')
def clients_list():
    clients = query_db('SELECT * FROM clients')
    return render_template('clients.html', clients=clients)

@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        contact_name = request.form.get('contact_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO clients (company_name, contact_name, email, phone) VALUES (?, ?, ?, ?)',
            (company_name, contact_name, email, phone)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('clients_list'))
    return render_template('add_client.html')

@app.route('/edit_client/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    client = query_db('SELECT * FROM clients WHERE id = ?', [client_id], one=True)
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        contact_name = request.form.get('contact_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE clients SET company_name = ?, contact_name = ?, email = ?, phone = ? WHERE id = ?',
            (company_name, contact_name, email, phone, client_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('clients_list'))
    return render_template('edit_client.html', client=client)

@app.route('/delete_client/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('clients_list'))

@app.route('/employees')
def employees():
    emp_list = query_db('SELECT * FROM employees')
    return render_template('employees.html', employees=emp_list)

@app.route('/payroll')
def payroll_list():
    query = '''
        SELECT payroll.id, employees.first_name, employees.last_name, 
               payroll.salary, payroll.allowances
        FROM payroll
        LEFT JOIN employees ON payroll.employee_id = employees.id
        ORDER BY payroll.id DESC
    '''
    payroll_records = query_db(query)
    return render_template('payroll.html', payroll=payroll_records)

@app.route('/invoices')
def invoices():
    return render_template('invoices.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/expenses')
def expenses():
    return render_template('expenses.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
