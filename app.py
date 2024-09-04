from flask import Flask, render_template, request, redirect, session
from flask_mysqldb import MySQL

class EmployeeAttendance:
    def __init__(self, name):
        self.app = Flask(name)
        self.app.secret_key = 'your_secret_key'
        
        # Connection to Database
        self.app.config['MYSQL_HOST'] = "localhost"
        self.app.config['MYSQL_USER'] = "root"
        self.app.config['MYSQL_PASSWORD'] = ""
        self.app.config['MYSQL_DB'] = "employee_db"
        self.mysql = MySQL(self.app)

        # Setup routes
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            return redirect('/login')

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                
                
                cur = self.mysql.connection.cursor()
                cur.execute("SELECT role FROM users WHERE username=%s AND password=%s", (username, password))
                user = cur.fetchone()
                cur.close()
                
                if user:
                    session['username'] = username
                    session['role'] = user[0]
                    
                    if user[0] == 'admin':
                        return redirect('/admin/dashboard')
                    elif user[0] == 'employee':
                        return redirect('/employee/dashboard')
                else:
                    return render_template('login.html', error="Invalid credentials. Please try again.")
            
            return render_template('login.html')

        @self.app.route('/logout')
        def logout():
            session.pop('username', None)
            session.pop('role', None)
            return redirect('/login')

        # Admin Dashboard Route
        @self.app.route('/admin/dashboard')
        def admin_dashboard():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                cur.execute("SELECT COUNT(*) as department_count FROM departments")
                department_count = cur.fetchone()[0]
                cur.close()
                return render_template('admin/dashboard.html', department_count=department_count)
            else:
                return redirect('/login')

        # Department Management Routes
        @self.app.route('/admin/departments', methods=['GET', 'POST'])
        def manage_departments():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                if request.method == 'POST':
                    department_id = request.form.get('department_id') 
                    department_name = request.form['department_name']

                    if department_id:  
                        cur.execute("UPDATE departments SET name = %s WHERE id = %s", (department_name, department_id))
                    else:  

                        department_id = ''.join([word[0].upper() for word in department_name.split()])

                        
                        cur.execute("SELECT id FROM departments WHERE id = %s", [department_id])
                        existing_department = cur.fetchone()

                        if existing_department:
                            return render_template('admin/departments.html', error="Department ID already exists")

                        
                        cur.execute("INSERT INTO departments (id, name) VALUES (%s, %s)", (department_id, department_name))

                    self.mysql.connection.commit()
                    return redirect('/admin/departments')

                
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()
                cur.close()
                return render_template('admin/departments.html', departments=departments)
            else:
                return redirect('/login')

        @self.app.route('/admin/departments/delete/<string:department_id>', methods=['POST'])
        def delete_department(department_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                cur.execute("DELETE FROM departments WHERE id = %s", [department_id])
                self.mysql.connection.commit()
                cur.close()
                return redirect('/admin/departments')
            else:
                return redirect('/login')

        # Employee Dashboard Route
        @self.app.route('/employee/dashboard')
        def employee_dashboard():
            if 'username' in session and session['role'] == 'employee':
                return render_template('employee/dashboard.html')
            else:
                return redirect('/login')

    def run(self):
        self.app.run(debug=True, port=3300)

if __name__ == "__main__":
    app_instance = EmployeeAttendance(__name__)
    app_instance.run()
