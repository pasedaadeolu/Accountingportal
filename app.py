from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accounting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Models ---
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    company = db.Column(db.String(100), nullable=True)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.Float, nullable=False, default=0.0)

# --- Routes ---

@app.route('/')
def dashboard():
    # Example metrics for the dashboard cards
    total_clients = Client.query.count()
    employees = Employee.query.all()
    total_payroll = sum(emp.salary for emp in employees) if employees else 0.0
    
    return render_template('dashboard.html', 
                           total_revenue=0.0, 
                           total_pending=0.0, 
                           total_payroll=total_payroll, 
                           total_clients=total_clients)

@app.route('/employees')
def employees_list():
    employees = Employee.query.all()
    return render_template('employees.html', employees=employees)

@app.route('/payroll')
def payroll_list():
    employees = Employee.query.all()
    return render_template('payroll.html', employees=employees)

@app.route('/clients')
def clients_list():
    clients = Client.query.all()
    return render_template('clients.html', clients=clients)

@app.route('/invoices')
def invoices_list():
    return render_template('invoices.html')

@app.route('/expenses')
def expenses_list():
    return render_template('expenses.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('dashboard'))

# --- Helper Action Routes ---
@app.route('/clients/add', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        new_client = Client(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            company=request.form.get('company')
        )
        db.session.add(new_client)
        db.session.commit()
        flash('Client added successfully!', 'success')
        return redirect(url_for('clients_list'))
    return render_template('add_client.html')

@app.route('/employees/add', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        new_emp = Employee(
            name=request.form.get('name'),
            position=request.form.get('position'),
            department=request.form.get('department'),
            salary=float(request.form.get('salary', 0))
        )
        db.session.add(new_emp)
        db.session.commit()
        flash('Employee added successfully!', 'success')
        return redirect(url_for('employees_list'))
    return render_template('add_employee.html')

@app.route('/invoices/add')
def add_invoice():
    return render_template('add_invoice.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
