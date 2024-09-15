from flask import Flask, render_template, request, redirect, session, flash
from flask_mysqldb import MySQL
import random
import string

class EmployeeAttendance:
    def __init__(self, name):
        self.app = Flask(name)
        self.app.secret_key = 'your_secret_key'
        
        # Connection to Database
        self.app.config['MYSQL_HOST'] = "localhost"
        self.app.config['MYSQL_USER'] = "root"
        self.app.config['MYSQL_PASSWORD'] = ""
        self.app.config['MYSQL_DB'] = "ears_db"
        self.mysql = MySQL(self.app)

        # Setup routes
        self.setup_routes()
        
    

    def setup_routes(self):
        @self.app.route('/')
        def home():
            # Render the home.html when visiting the root route
            return render_template('home.html')
        

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                
                # Query to check the user's credentials and role
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
            return redirect('/')

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
            
            
            
#-------------------------------------------------------            
           
        # Employee Management Routes
        @self.app.route('/admin/employees', methods=['GET', 'POST'])
        def manage_employees():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                if request.method == 'POST':
                    employee_id = request.form.get('employee_id')
                    first_name = request.form['first_name']
                    last_name = request.form['last_name']
                    department = request.form['department']
                    shift = request.form['shift']
                    gender = request.form['gender']

                    if employee_id:
                        # Update existing employee
                        cur.execute(
                            "UPDATE employees SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s WHERE id=%s",
                            (first_name, last_name, department, shift, gender, employee_id)
                        )
                    else:
                        # Insert new employee
                        cur.execute(
                            "INSERT INTO employees (first_name, last_name, department, shift, gender) VALUES (%s, %s, %s, %s, %s)",
                            (first_name, last_name, department, shift, gender)
                        )
                        # Get the new employee ID
                        cur.execute("SELECT LAST_INSERT_ID()")
                        new_employee_id = cur.fetchone()[0]

                    self.mysql.connection.commit()
                    return redirect('/admin/employees')
                


                # Fetch the list of departments from the database
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                cur.execute("SELECT id, first_name, last_name, department, shift, gender FROM employees")
                employees = cur.fetchall()
                cur.close()
                
                return render_template('admin/employees.html', employees=employees, departments=departments)
            else:
                return redirect('/login')

        @self.app.route('/admin/employees/delete/<string:employee_id>', methods=['POST'])
        def delete_employee(employee_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                cur.execute("DELETE FROM employees WHERE id = %s", [employee_id])
                self.mysql.connection.commit()
                cur.close()
                return redirect('/admin/employees')
            else:
                return redirect('/login')
            

#----------------------------------------------------------------------------------

#   user.html

        @self.app.route('/admin/user', methods=['GET', 'POST'])
        def manage_users():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                
                if request.method == 'POST':
                    user_id = request.form.get('user_id')
                    first_name = request.form['first_name']
                    last_name = request.form['last_name']
                    department = request.form['department']
                    shift = request.form['shift']
                    gender = request.form['gender']
                    username = request.form['username']
                    role = request.form['role']
                    password = request.form['password']

                    if user_id:
                        # Update employee details
                        cur.execute(
                            "UPDATE employees SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s WHERE id=%s",
                            (first_name, last_name, department, shift, gender, user_id)
                        )

                        # Update user details
                        cur.execute(
                            "UPDATE users SET username=%s, password=%s, role=%s WHERE id=%s",
                            (username, password, role, user_id)
                        )
                    else:
                        # Insert new employee
                        cur.execute(
                            "INSERT INTO employees (first_name, last_name, department, shift, gender) VALUES (%s, %s, %s, %s, %s)",
                            (first_name, last_name, department, shift, gender)
                        )
                        cur.execute("SELECT LAST_INSERT_ID()")
                        new_employee_id = cur.fetchone()[0]

                        # Insert new user
                        cur.execute(
                            "INSERT INTO users (username, password, role, employee_id) VALUES (%s, %s, %s, %s)",
                            (username, password, role, new_employee_id)
                        )

                    self.mysql.connection.commit()
                    return redirect('/admin/user')

                # Fetch all users and join with employees using employee_id
                cur.execute("""
                    SELECT u.id, CONCAT(e.first_name, ' ', e.last_name) AS full_name, u.username, u.role, u.password
                    FROM users u
                    LEFT JOIN employees e ON u.employee_id = e.id
                """)
                users = cur.fetchall()
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()
                cur.close()

                return render_template('admin/user.html', users=users, departments=departments)
            else:
                return redirect('/login')



        # Route for deleting a user
        @self.app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
        def delete_user(user_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                try:
                    cur.execute("DELETE FROM users WHERE id = %s", [user_id])
                    self.mysql.connection.commit()
                    flash("User deleted successfully", "success")
                except Exception as e:
                    flash(f"Error deleting user: {e}", "danger")
                finally:
                    cur.close()
                return redirect('/admin/user')
            else:
                flash("Unauthorized action", "danger")
                return redirect('/login')

        
        
#----------------------------------------------------------------------


        # Employee Dashboard Route
        @self.app.route('/employee/dashboard')
        def employee_dashboard():
            if 'username' in session and session['role'] == 'employee':
                return render_template('employee/dashboard.html')
            else:
                return redirect('/login')
            
            
            

    def run(self):
        self.app.run(debug=True, port=3000)

if __name__ == "__main__":
    app_instance = EmployeeAttendance(__name__)
    app_instance.run()