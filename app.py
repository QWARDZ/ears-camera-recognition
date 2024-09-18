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
                        return redirect('/employee/attendance')
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

                # Count departments
                cur.execute("SELECT COUNT(*) as department_count FROM departments")
                department_count = cur.fetchone()[0]

                # Count employees
                cur.execute("SELECT COUNT(*) as employee_count FROM employees")
                employee_count = cur.fetchone()[0]

                # Count shifts
                cur.execute("SELECT COUNT(*) as shift_count FROM shifts")
                shift_count = cur.fetchone()[0]

                # Count users
                cur.execute("SELECT COUNT(*) as user_count FROM users")
                user_count = cur.fetchone()[0]

                cur.close()

                # Pass the counts to the template
                return render_template('admin/dashboard.html', department_count=department_count, 
                                    employee_count=employee_count, shift_count=shift_count, 
                                    user_count=user_count)
            else:
                return redirect('/login')

            
#----------------------------------------------------------
            

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

                    self.mysql.connection.commit()
                    return redirect('/admin/employees')

                # Fetch employees with departments and shifts
                cur.execute("""
                    SELECT e.id, e.first_name, e.last_name, d.name, CONCAT(s.start_time, ' - ', s.end_time) AS shift_time, e.gender
                    FROM employees e
                    LEFT JOIN departments d ON e.department = d.id
                    LEFT JOIN shifts s ON e.shift = s.id
                """)
                employees = cur.fetchall()


                # Fetch the list of departments for the dropdown
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                # Fetch the list of shifts for the dropdown
                cur.execute("SELECT id, start_time, end_time FROM shifts")
                shifts = cur.fetchall()

                cur.close()

                # Render the employee management page with employees, departments, and shifts data
                return render_template('admin/employees.html', employees=employees, departments=departments, shifts=shifts)
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
        # User Management Route
        @self.app.route('/admin/user', methods=['GET', 'POST'])
        def manage_users():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                if request.method == 'POST':
                    user_id = request.form.get('user_id')
                    first_name = request.form['first_name']
                    last_name = request.form['last_name']
                    department = request.form['department']
                    shift = request.form['shift']  # Shift selected from dropdown
                    gender = request.form['gender']
                    username = request.form['username']
                    role = request.form['role']
                    password = request.form['password']

                    if user_id:
                        # Update employee and user details
                        cur.execute("UPDATE employees SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s WHERE id=%s", 
                                    (first_name, last_name, department, shift, gender, user_id))
                        cur.execute("UPDATE users SET username=%s, password=%s, role=%s WHERE id=%s", 
                                    (username, password, role, user_id))
                    else:
                        # Insert new employee and user
                        cur.execute("INSERT INTO employees (first_name, last_name, department, shift, gender) VALUES (%s, %s, %s, %s, %s)", 
                                    (first_name, last_name, department, shift, gender))
                        cur.execute("SELECT LAST_INSERT_ID()")
                        new_employee_id = cur.fetchone()[0]

                        cur.execute("INSERT INTO users (username, password, role, employee_id) VALUES (%s, %s, %s, %s)", 
                                    (username, password, role, new_employee_id))

                    self.mysql.connection.commit()
                    return redirect('/admin/user')

                # Fetch all users with employee details
                cur.execute("""
                    SELECT u.id, CONCAT(e.first_name, ' ', e.last_name) AS full_name, u.username, u.role, u.password, s.start_time, s.end_time
                    FROM users u
                    LEFT JOIN employees e ON u.employee_id = e.id
                    LEFT JOIN shifts s ON e.shift = s.id
                """)
                users = cur.fetchall()

                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                cur.execute("SELECT id, start_time, end_time FROM shifts")
                shifts = cur.fetchall()

                cur.close()

                return render_template('admin/user.html', users=users, departments=departments, shifts=shifts)
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
        # Shift Management Routes
        @self.app.route('/admin/shifts', methods=['GET', 'POST'])
        def manage_shifts():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                if request.method == 'POST':
                    shift_id = request.form.get('shift_id')
                    start_time = request.form.get('start_time')
                    end_time = request.form.get('end_time')

                    # If shift_id is present, update the shift, otherwise insert a new shift
                    if shift_id:
                        cur.execute("UPDATE shifts SET start_time = %s, end_time = %s WHERE id = %s", (start_time, end_time, shift_id))
                    else:
                        cur.execute("INSERT INTO shifts (start_time, end_time) VALUES (%s, %s)", (start_time, end_time))

                    self.mysql.connection.commit()
                    return redirect('/admin/shifts')

                # Fetch all shifts from the database
                cur.execute("SELECT id, start_time, end_time FROM shifts")
                shifts = cur.fetchall()
                cur.close()

                return render_template('admin/shifts.html', shifts=shifts)
            else:
                return redirect('/login')

        # Route to delete a shift
        @self.app.route('/admin/shifts/delete/<int:shift_id>', methods=['POST'])
        def delete_shift(shift_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                cur.execute("DELETE FROM shifts WHERE id = %s", [shift_id])
                self.mysql.connection.commit()
                cur.close()
                flash("Shift deleted successfully", "success")
                return redirect('/admin/shifts')
            else:
                flash("Unauthorized action", "danger")
                return redirect('/login')
            
            
#---------------------------------------------------------------------------
        # Route to view all attendance records (filtered by department and date range)
        @self.app.route('/admin/attendance', methods=['GET'])
        def attendance_report():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Get department list for filtering
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                # Get filtering parameters (start_date, end_date, department)
                start_date = request.args.get('start_date')
                end_date = request.args.get('end_date')
                department = request.args.get('department')

                attendance_records = []
                if start_date and end_date and department:
                    # Fetch attendance records based on filters
                    query = """
                        SELECT e.first_name, e.last_name, d.name, a.check_in, a.check_out, a.date, a.status, a.id
                        FROM attendance a
                        JOIN employees e ON a.employee_id = e.id
                        JOIN departments d ON e.department = d.id
                        WHERE a.date BETWEEN %s AND %s AND e.department = %s
                    """
                    cur.execute(query, (start_date, end_date, department))
                    attendance_records = cur.fetchall()

                cur.close()

                return render_template('/admin/attendance.html', departments=departments, attendance_records=attendance_records)
            else:
                return redirect('/login')

        # Route to update attendance record
        @self.app.route('/admin/attendance/update', methods=['POST'])
        def update_attendance():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Get data from form
                attendance_id = request.form['attendance_id']
                check_in = request.form['check_in']
                check_out = request.form['check_out']
                status = request.form['status']

                # Update the attendance record in the database
                query = """
                    UPDATE attendance
                    SET check_in = %s, check_out = %s, status = %s
                    WHERE id = %s
                """
                cur.execute(query, (check_in, check_out, status, attendance_id))
                self.mysql.connection.commit()

                cur.close()

                flash('Attendance record updated successfully!', 'success')
                return redirect('/admin/attendance')
            else:
                return redirect('/login')

        # Route to delete attendance record
        @self.app.route('/admin/attendance/delete/<int:attendance_id>', methods=['POST'])
        def delete_attendance(attendance_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Delete the attendance record
                query = "DELETE FROM attendance WHERE id = %s"
                cur.execute(query, [attendance_id])
                self.mysql.connection.commit()

                cur.close()

                flash('Attendance record deleted successfully!', 'success')
                return redirect('/admin/attendance')
            else:
                return redirect('/login')




#---------------------------------------------------------------------------
        @self.app.route('/employee/attendance', methods=['GET', 'POST'])
        def employee_attendance():
            if 'username' in session and session['role'] == 'employee':
                cur = self.mysql.connection.cursor()

                # Get the employee ID from the users table using the logged-in username
                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    return redirect('/login')

                employee_id = result[0]

                # Fetch employee's assigned shift times
                cur.execute("""
                    SELECT s.start_time, s.end_time 
                    FROM employees e 
                    JOIN shifts s ON e.shift = s.id 
                    WHERE e.id = %s
                """, [employee_id])
                shift = cur.fetchone()
                shift_start = shift[0]
                shift_end = shift[1]

                # Check if the employee has already checked in today
                cur.execute("""
                    SELECT check_in, check_out 
                    FROM attendance 
                    WHERE employee_id = %s AND DATE(date) = CURDATE()""", [employee_id])
                attendance_record = cur.fetchone()

                already_checked_in = False

                if attendance_record:
                    # If checked in but not checked out, show the check-out button
                    if attendance_record[1] is None:
                        already_checked_in = True

                if request.method == 'POST':
                    action = request.form['action']

                    if action == 'time_in' and not already_checked_in:
                        # Insert new check-in record
                        cur.execute("""
                            INSERT INTO attendance (employee_id, check_in, date) 
                            VALUES (%s, NOW(), NOW())""", [employee_id])
                        self.mysql.connection.commit()

                        # Calculate the status (Late/On Time)
                        cur.execute("SELECT TIME(check_in) FROM attendance WHERE employee_id = %s AND DATE(date) = CURDATE()", [employee_id])
                        check_in_time = cur.fetchone()[0]

                        if check_in_time > shift_start:
                            status = "Late"
                        elif check_in_time == shift_start:
                            status = "On Time"
                        else:
                            status = "Early"

                        # Update the status in the attendance table
                        cur.execute("""
                            UPDATE attendance 
                            SET status = %s 
                            WHERE employee_id = %s AND DATE(date) = CURDATE()""", (status, employee_id))
                        self.mysql.connection.commit()

                        flash(f"Checked in successfully. Status: {status}", "success")
                        return redirect('/employee/attendance')

                    elif action == 'time_out' and already_checked_in:
                        # Update the check-out time
                        cur.execute("""
                            UPDATE attendance 
                            SET check_out = NOW() 
                            WHERE employee_id = %s AND DATE(date) = CURDATE()""", [employee_id])
                        self.mysql.connection.commit()

                        # Calculate Overtime
                        cur.execute("SELECT TIME(check_out) FROM attendance WHERE employee_id = %s AND DATE(date) = CURDATE()", [employee_id])
                        check_out_time = cur.fetchone()[0]

                        if check_out_time > shift_end:
                            status = "Overtime"
                        else:
                            status = "On Time"

                        # Update the status
                        cur.execute("""
                            UPDATE attendance 
                            SET status = %s 
                            WHERE employee_id = %s AND DATE(date) = CURDATE()""", (status, employee_id))
                        self.mysql.connection.commit()

                        flash(f"Checked out successfully. Status: {status}", "success")
                        return redirect('/employee/attendance')

                cur.close()
                return render_template('employee/attendance.html', already_checked_in=already_checked_in)

            else:
                return redirect('/login')





            
            
            

    def run(self):
        self.app.run(debug=True, port=3000)

if __name__ == "__main__":
    app_instance = EmployeeAttendance(__name__)
    app_instance.run()