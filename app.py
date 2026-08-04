import os
import sqlite3
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, 
    url_for, flash, session
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_accounting_key'

# Upload configuration for user avatars
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('abc_accounting.db')
    conn.row_factory = sqlite3.Row
    return conn

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Context processor to make current logged-in user details available in ALL templates
@app.context_processor
def inject_user():
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        return dict(current_user=user)
    return dict(current_user=None)

# ----------------------------
# AUTHENTICATION ROUTES
# ----------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['user'] = user['username']
            session['profile_pic'] = user['profile_pic'] if user['profile_pic'] else 'default.png'
            session['theme'] = user['theme'] if user['theme'] else 'light'
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ----------------------------
# DASHBOARD ROUTE
# ----------------------------

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()

    rev = conn.execute("SELECT SUM(amount) FROM invoices WHERE status = 'Paid'").fetchone()[0]
    total_revenue = rev if rev else 0.0

    pend = conn.execute("SELECT SUM(amount) FROM invoices WHERE status = 'Unpaid'").fetchone()[0]
    total_pending = pend if pend else 0.0

    exp = conn.execute("SELECT SUM(amount) FROM expenses").fetchone()[0]
    total_expenses = exp if exp else 0.0

    pay = conn.execute("SELECT SUM(net_salary) FROM payroll").fetchone()[0]
    total_payroll = pay if pay else 0.0

    recent_invoices = conn.execute('''
        SELECT invoices.invoice_number, clients.company_name, invoices.amount, invoices.status, invoices.issue_date
        FROM invoices
        JOIN clients ON invoices.client_id = clients.id
        ORDER BY invoices.id DESC LIMIT 5
    ''').fetchall()

    emp_count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    client_count = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]

    conn.close()

    net_profit = total_revenue - (total_payroll + total_expenses)

    return render_template(
        'dashboard.html',
        total_revenue=total_revenue,
        total_pending=total_pending,
        total_expenses=total_expenses,
        total_payroll=total_payroll,
        net_profit=net_profit,
        recent_invoices=recent_invoices,
        emp_count=emp_count,
        client_count=client_count
    )

# ----------------------------
# EMPLOYEES ROUTES
# ----------------------------

@app.route('/employees')
@login_required
def employees_list():
    conn = get_db_connection()
    employees = conn.execute('SELECT * FROM employees').fetchall()
    conn.close()
    return render_template('employees.html', employees=employees)

@app.route('/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        department = request.form['department']
        role = request.form['role']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO employees (first_name, last_name, email, department, role) VALUES (?, ?, ?, ?, ?)',
            (first_name, last_name, email, department, role)
        )
        conn.commit()
        conn.close()
        flash('Employee added successfully!', 'success')
        return redirect(url_for('employees_list'))

    return render_template('add_employee.html')

# ----------------------------
# PAYROLL ROUTES
# ----------------------------

@app.route('/payroll')
@login_required
def payroll_list():
    conn = get_db_connection()
    payroll_records = conn.execute('''
        SELECT payroll.id, employees.first_name, employees.last_name, 
               payroll.basic_salary, payroll.allowances, payroll.deductions, 
               payroll.net_salary, payroll.payment_date
        FROM payroll
        JOIN employees ON payroll.employee_id = employees.id
        ORDER BY payroll.id DESC
    ''').fetchall()
    conn.close()
    return render_template('payroll.html', payroll_records=payroll_records)

@app.route('/payroll/add', methods=['GET', 'POST'])
@login_required
def add_payroll():
    conn = get_db_connection()
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        basic_salary = float(request.form['basic_salary'])
        allowances = float(request.form.get('allowances', 0))
        deductions = float(request.form.get('deductions', 0))
        payment_date = request.form['payment_date']

        net_salary = basic_salary + allowances - deductions

        conn.execute('''
            INSERT INTO payroll (employee_id, basic_salary, allowances, deductions, net_salary, payment_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (employee_id, basic_salary, allowances, deductions, net_salary, payment_date))
        conn.commit()
        conn.close()
        flash('Payroll record created successfully!', 'success')
        return redirect(url_for('payroll_list'))

    employees = conn.execute('SELECT id, first_name, last_name FROM employees').fetchall()
    conn.close()
    return render_template('add_payroll.html', employees=employees)

# ----------------------------
# CLIENTS ROUTES
# ----------------------------

@app.route('/clients')
@login_required
def clients_list():
    conn = get_db_connection()
    clients = conn.execute('SELECT * FROM clients').fetchall()
    conn.close()
    return render_template('clients.html', clients=clients)

@app.route('/clients/add', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        company_name = request.form['company_name']
        contact_person = request.form['contact_person']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form.get('address', '')

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO clients (company_name, contact_person, email, phone, address) VALUES (?, ?, ?, ?, ?)',
            (company_name, contact_person, email, phone, address)
        )
        conn.commit()
        conn.close()
        flash('Client added successfully!', 'success')
        return redirect(url_for('clients_list'))

    return render_template('add_client.html')

# ----------------------------
# INVOICES ROUTES
# ----------------------------

@app.route('/invoices')
@login_required
def invoices_list():
    conn = get_db_connection()
    invoices = conn.execute('''
        SELECT invoices.id, invoices.invoice_number, clients.company_name, 
               invoices.amount, invoices.status, invoices.issue_date, invoices.due_date
        FROM invoices
        JOIN clients ON invoices.client_id = clients.id
        ORDER BY invoices.id DESC
    ''').fetchall()
    conn.close()
    return render_template('invoices.html', invoices=invoices)

@app.route('/invoices/add', methods=['GET', 'POST'])
@login_required
def add_invoice():
    conn = get_db_connection()
    if request.method == 'POST':
        invoice_number = request.form['invoice_number']
        client_id = request.form['client_id']
        amount = float(request.form['amount'])
        status = request.form['status']
        issue_date = request.form['issue_date']
        due_date = request.form['due_date']

        conn.execute('''
            INSERT INTO invoices (invoice_number, client_id, amount, status, issue_date, due_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (invoice_number, client_id, amount, status, issue_date, due_date))
        conn.commit()
        conn.close()
        flash('Invoice created successfully!', 'success')
        return redirect(url_for('invoices_list'))

    clients = conn.execute('SELECT id, company_name FROM clients').fetchall()
    conn.close()
    return render_template('add_invoice.html', clients=clients)

# ----------------------------
# EXPENSES ROUTES
# ----------------------------

@app.route('/expenses')
@login_required
def expenses_list():
    conn = get_db_connection()
    expenses = conn.execute('SELECT * FROM expenses ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('expenses.html', expenses=expenses)

@app.route('/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        category = request.form['category']
        description = request.form.get('description', '')
        amount = float(request.form['amount'])
        date = request.form['date']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO expenses (category, description, amount, date) VALUES (?, ?, ?, ?)',
            (category, description, amount, date)
        )
        conn.commit()
        conn.close()
        flash('Expense recorded successfully!', 'success')
        return redirect(url_for('expenses_list'))

    return render_template('add_expense.html')

# ----------------------------
# REPORTS & ANALYTICS
# ----------------------------

@app.route('/reports')
@login_required
def reports():
    conn = get_db_connection()

    rev = conn.execute("SELECT SUM(amount) FROM invoices WHERE status = 'Paid'").fetchone()[0]
    total_revenue = rev if rev else 0.0

    exp = conn.execute("SELECT SUM(amount) FROM expenses").fetchone()[0]
    total_expenses = exp if exp else 0.0

    pay = conn.execute("SELECT SUM(net_salary) FROM payroll").fetchone()[0]
    total_payroll = pay if pay else 0.0

    conn.close()

    net_income = total_revenue - (total_expenses + total_payroll)

    return render_template(
        'reports.html',
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        total_payroll=total_payroll,
        net_income=net_income
    )

# ----------------------------
# SETTINGS & PROFILE MANAGEMENT
# ----------------------------

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    conn = get_db_connection()
    user_id = session.get('user_id')

    if request.method == 'POST':
        action = request.form.get('action')

        # 1. Update Profile Info & Avatar
        if action == 'update_profile':
            new_username = request.form.get('username')
            file = request.files.get('profile_pic')

            filename = None
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            if filename:
                conn.execute('UPDATE users SET username = ?, profile_pic = ? WHERE id = ?', (new_username, filename, user_id))
                session['profile_pic'] = filename
            else:
                conn.execute('UPDATE users SET username = ? WHERE id = ?', (new_username, user_id))
            
            conn.commit()
            session['user'] = new_username
            flash('Profile updated successfully!', 'success')

        # 2. Change Password
        elif action == 'change_password':
            old_pass = request.form.get('current_password')
            new_pass = request.form.get('new_password')
            
            user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
            if user and user['password'] == old_pass:
                conn.execute('UPDATE users SET password = ? WHERE id = ?', (new_pass, user_id))
                conn.commit()
                flash('Password changed successfully!', 'success')
            else:
                flash('Incorrect current password.', 'danger')

        # 3. Update Preferences (Theme)
        elif action == 'update_preferences':
            theme = request.form.get('theme', 'light')
            conn.execute('UPDATE users SET theme = ? WHERE id = ?', (theme, user_id))
            conn.commit()
            session['theme'] = theme
            flash('Theme preferences saved!', 'info')

        conn.close()
        return redirect(url_for('settings'))

    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return render_template('settings.html', user=user)

# ----------------------------
# MAIN ENTRY POINT
# ----------------------------

if __name__ == '__main__':
    app.run(debug=True, port=5000)
