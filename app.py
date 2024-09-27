from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import random
# import string
# import datetime
import os

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


        # Configure Upload folder
        self.app.config['UPLOAD_FOLDER'] = 'static/uploads'

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


#------------------------------------------------------------------------------------

        # Admin Dashboard Route
        @self.app.route('/admin/dashboard')
        def admin_dashboard():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Fetch user details for the top bar based on logged-in admin
                cur.execute("""
                    SELECT e.first_name, e.last_name, e.profile_picture
                    FROM users u
                    LEFT JOIN employees e ON u.employee_id = e.id
                    WHERE u.username = %s
                """, [session['username']])
                user_data = cur.fetchone()

                # Prepare data for user profile
                if user_data:
                    user_name = f"{user_data[0]} {user_data[1]}"
                    # Check if profile picture exists and handle None case
                    user_profile_picture = url_for('static', filename='uploads/' + user_data[2]) if user_data[2] else url_for('static', filename='uploads/default_profile.png')
                else:
                    user_name = 'Unknown'
                    user_profile_picture = url_for('static', filename='uploads/default_profile.png')

                # Count total employees
                cur.execute("SELECT COUNT(*) FROM employees")
                employee_count = cur.fetchone()[0]

                # Count total shifts
                cur.execute("SELECT COUNT(*) FROM shifts")
                shift_count = cur.fetchone()[0]

                # Count total attendance records
                cur.execute("SELECT COUNT(*) FROM attendance")
                attendance_count = cur.fetchone()[0]

                # Count total users
                cur.execute("SELECT COUNT(*) FROM users")
                user_count = cur.fetchone()[0]

                # Count on-time attendance
                cur.execute("SELECT COUNT(*) FROM attendance WHERE status = 'On Time'")
                on_time_count = cur.fetchone()[0]

                # Count late attendance
                cur.execute("SELECT COUNT(*) FROM attendance WHERE status = 'Late'")
                late_count = cur.fetchone()[0]

                # Fetch recent attendees who have checked in within the last 20 minutes
                cur.execute("""
                    SELECT e.first_name, e.last_name, e.profile_picture,
                        IFNULL(DATE_FORMAT(a.check_in, '%h:%i %p'), 'Not Checked In') as check_in,
                        IFNULL(DATE_FORMAT(a.check_out, '%h:%i %p'), 'Not Checked Out') as check_out
                    FROM attendance a
                    LEFT JOIN employees e ON a.employee_id = e.id
                    WHERE TIMESTAMPDIFF(MINUTE, a.check_in, NOW()) <= 5
                    ORDER BY a.date DESC, a.check_in DESC
                    LIMIT 5
                """)
                recent_attendees = cur.fetchall()

                cur.close()

                # Pass the counts and user details to the template
                return render_template('admin/dashboard.html',
                                    employee_count=employee_count,
                                    shift_count=shift_count,
                                    attendance_count=attendance_count,
                                    user_count=user_count,
                                    on_time_count=on_time_count,
                                    late_count=late_count,
                                    recent_attendees=recent_attendees,
                                    user_name=user_name,
                                    user_profile_picture=user_profile_picture,
                                    user_data=user_data)
            else:
                return redirect('/login')





#----------------------------------------------------------


        # Department Management Routes
        @self.app.route('/admin/departments', methods=['GET', 'POST'])
        def manage_departments():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Fetch user data for top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Provide default user_data if not found
                if not user_data:
                    user_data = ('Unknown', 'User', 'default_profile.png')

                if request.method == 'POST':
                    department_id = request.form.get('department_id')
                    department_name = request.form['department_name']

                    if department_id:
                        cur.execute("UPDATE departments SET name = %s WHERE id = %s", (department_name, department_id))
                    else:
                        # Generate a department ID based on initials
                        department_id = ''.join([word[0].upper() for word in department_name.split()])

                        cur.execute("SELECT id FROM departments WHERE id = %s", [department_id])
                        existing_department = cur.fetchone()

                        if existing_department:
                            return render_template('admin/departments.html', error="Department ID already exists", departments=[], user_data=user_data)

                        cur.execute("INSERT INTO departments (id, name) VALUES (%s, %s)", (department_id, department_name))

                    self.mysql.connection.commit()
                    return redirect('/admin/departments')

                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()
                cur.close()
                return render_template('admin/departments.html', departments=departments, user_data=user_data)
            else:
                return redirect('/login')

        # Route to delete a department
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

        # Set up allowed extensions for the upload
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        @self.app.route('/admin/employees', methods=['GET', 'POST'])
        def manage_employees():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Fetch user data for top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Handle POST request for adding or updating employee details
                if request.method == 'POST':
                    employee_id = request.form.get('employee_id')
                    first_name = request.form['first_name']
                    last_name = request.form['last_name']
                    department = request.form['department']
                    shift = request.form['shift']
                    gender = request.form['gender']
                    profile_picture = request.files.get('profile_picture')

                    # Handling profile picture upload
                    profile_picture_filename = None
                    if profile_picture and allowed_file(profile_picture.filename):
                        filename = secure_filename(profile_picture.filename)
                        profile_picture.save(os.path.join('static/uploads', filename))
                        profile_picture_filename = filename

                    if employee_id:
                        # Update existing employee with or without profile picture
                        if profile_picture_filename:
                            cur.execute(
                                "UPDATE employees SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s, profile_picture=%s WHERE id=%s",
                                (first_name, last_name, department, shift, gender, profile_picture_filename, employee_id)
                            )
                        else:
                            cur.execute(
                                "UPDATE employees SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s WHERE id=%s",
                                (first_name, last_name, department, shift, gender, employee_id)
                            )
                    else:
                        # Insert new employee
                        cur.execute(
                            "INSERT INTO employees (first_name, last_name, department, shift, gender, profile_picture) VALUES (%s, %s, %s, %s, %s, %s)",
                            (first_name, last_name, department, shift, gender, profile_picture_filename)
                        )

                        # Get the new employee's ID
                        cur.execute("SELECT LAST_INSERT_ID()")
                        new_employee_id = cur.fetchone()[0]

                        # Automatically create a user for the new employee
                        username = request.form['username']
                        password = request.form['password']
                        cur.execute("INSERT INTO users (username, password, role, employee_id) VALUES (%s, %s, 'employee', %s)",
                                    (username, password, new_employee_id))

                    self.mysql.connection.commit()
                    return redirect('/admin/employees')

                # Fetch only employee data (excluding admin users)
                cur.execute("""
                    SELECT e.id, e.first_name, e.last_name, d.name, CONCAT(s.start_time, ' - ', s.end_time) AS shift_time, e.gender, e.profile_picture
                    FROM employees e
                    LEFT JOIN departments d ON e.department = d.id
                    LEFT JOIN shifts s ON e.shift = s.id
                    LEFT JOIN users u ON u.employee_id = e.id
                    WHERE u.role = 'employee'
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
                return render_template('admin/employees.html', employees=employees, departments=departments, shifts=shifts, user_data=user_data)
            else:
                return redirect('/login')

        # Route for deleting an employee and associated data
        @self.app.route('/admin/employees/delete/<int:employee_id>', methods=['POST'])
        def delete_employee(employee_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                try:
                    # Delete attendance records associated with the employee
                    cur.execute("DELETE FROM attendance WHERE employee_id = %s", [employee_id])

                    # Delete user associated with the employee
                    cur.execute("DELETE FROM users WHERE employee_id = %s", [employee_id])

                    # Delete the employee record itself
                    cur.execute("DELETE FROM employees WHERE id = %s", [employee_id])
                    self.mysql.connection.commit()

                    flash("Employee and associated records deleted successfully.", "success")
                except Exception as e:
                    flash(f"Error deleting employee: {e}", "danger")
                finally:
                    cur.close()
                return redirect('/admin/employees')
            else:
                flash("Unauthorized action", "danger")
                return redirect('/login')




#----------------------------------------------------------------------------------

        @self.app.route('/admin/user', methods=['GET', 'POST'])
        def manage_users():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Fetch user data for top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                if request.method == 'POST':
                    user_id = request.form.get('user_id')
                    first_name = request.form['first_name']
                    last_name = request.form['last_name']
                    department = request.form['department'] if request.form.get('role') == 'employee' else None
                    shift = request.form['shift'] if request.form.get('role') == 'employee' else None
                    gender = request.form['gender'] if request.form.get('role') == 'employee' else None
                    username = request.form['username']
                    role = request.form['role']
                    password = request.form['password']

                    if user_id:
                        # Update employee and user details
                        cur.execute("""
                            UPDATE employees SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s
                            WHERE id=%s
                        """, (first_name, last_name, department, shift, gender, user_id))
                        cur.execute("""
                            UPDATE users SET username=%s, password=%s, role=%s
                            WHERE id=%s
                        """, (username, password, role, user_id))
                    else:
                        # Insert new employee and user
                        cur.execute("""
                            INSERT INTO employees (first_name, last_name, department, shift, gender)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (first_name, last_name, department, shift, gender))
                        cur.execute("SELECT LAST_INSERT_ID()")
                        new_employee_id = cur.fetchone()[0]

                        cur.execute("""
                            INSERT INTO users (username, password, role, employee_id)
                            VALUES (%s, %s, %s, %s)
                        """, (username, password, role, new_employee_id))

                    self.mysql.connection.commit()
                    return redirect('/admin/user')

                cur.execute("""
                    SELECT u.id,
                        CONCAT(COALESCE(e.first_name, 'None'), ' ', COALESCE(e.last_name, '')) AS full_name,
                        u.username,
                        u.role,
                        u.password,
                        CASE WHEN u.role = 'employee' THEN COALESCE(s.start_time, '---') ELSE '---' END AS start_time,
                        CASE WHEN u.role = 'employee' THEN COALESCE(s.end_time, '---') ELSE '---' END AS end_time,
                        e.profile_picture
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

                return render_template('admin/user.html', users=users, departments=departments, shifts=shifts, user_data=user_data)
            else:
                return redirect('/login')




# Route for deleting a user
        @self.app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
        def delete_user(user_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                try:
                    # Retrieve the employee_id associated with this user
                    cur.execute("SELECT employee_id FROM users WHERE id = %s", [user_id])
                    employee_id_result = cur.fetchone()

                    # Check if an employee_id exists
                    if employee_id_result:
                        employee_id = employee_id_result[0]

                        # Delete associated attendance records
                        cur.execute("DELETE FROM attendance WHERE employee_id = %s", [employee_id])

                        # Delete employee record
                        cur.execute("DELETE FROM employees WHERE id = %s", [employee_id])

                    # Delete user record
                    cur.execute("DELETE FROM users WHERE id = %s", [user_id])

                    # Commit all changes
                    self.mysql.connection.commit()

                    flash("User and associated records deleted successfully", "success")
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


                # Fetch user data for top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()
                #-----------------------------------------------

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

                return render_template('admin/shifts.html', shifts=shifts, user_data=user_data)
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

        # Admin Attendance Report Route
        @self.app.route('/admin/attendance', methods=['GET'])
        def attendance_report():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Fetch user data for top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Get department list for filtering
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                # Get filtering parameter for department
                department = request.args.get('department')

                # Define the query and parameters
                query = """
                    SELECT e.first_name, e.last_name, e.profile_picture, d.name,
                        DATE_FORMAT(a.check_in, '%%h:%%i %%p') as check_in,
                        DATE_FORMAT(a.check_out, '%%h:%%i %%p') as check_out,
                        a.status, a.id, a.date
                    FROM attendance a
                    LEFT JOIN employees e ON a.employee_id = e.id
                    LEFT JOIN departments d ON e.department = d.id
                """
                params = []

                if department and department != 'all':
                    query += " WHERE d.id = %s"
                    params.append(department)

                cur.execute(query, params)

                attendance_records = cur.fetchall()
                cur.close()

                return render_template('/admin/attendance.html', departments=departments, attendance_records=attendance_records, user_data=user_data)
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

                # Fetch user data for top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

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

                # Check if the employee has any attendance record for today
                cur.execute("""
                    SELECT check_in, check_out, DATE(date)
                    FROM attendance
                    WHERE employee_id = %s AND DATE(date) = CURDATE()""", [employee_id])
                attendance_record = cur.fetchone()

                already_checked_in = False
                already_checked_out = False

                if attendance_record:
                    check_in_time, check_out_time, record_date = attendance_record
                    if check_in_time and not check_out_time:
                        already_checked_in = True
                    elif check_in_time and check_out_time:
                        already_checked_out = True

                if request.method == 'POST':
                    action = request.form['action']

                    if action == 'time_in':
                        if already_checked_out:
                            # Show message to the employee if they've already checked out today
                            flash("Today, only one time in and time out allowed. See you tomorrow.", "warning")
                            return redirect('/employee/attendance')
                        elif already_checked_in:
                            # If they've already checked in but not checked out, show the check-out option
                            flash("You are already checked in. Please check out when you finish.", "info")
                        else:
                            # Insert new check-in record if no check-in exists for today
                            cur.execute("""
                                INSERT INTO attendance (employee_id, check_in, date)
                                VALUES (%s, NOW(), NOW())""", [employee_id])
                            self.mysql.connection.commit()

                            # Calculate the status (Late/On Time)
                            cur.execute("SELECT TIME(check_in) FROM attendance WHERE employee_id = %s AND DATE(date) = CURDATE()", [employee_id])
                            check_in_time = cur.fetchone()[0]

                            if check_in_time > shift_start:
                                status = "Late"
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

                    elif action == 'time_out':
                        if not already_checked_in:
                            flash("You haven't checked in yet!", "danger")
                            return redirect('/employee/attendance')
                        else:
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
                return render_template('employee/attendance.html', already_checked_in=already_checked_in, already_checked_out=already_checked_out, user_data=user_data)

            else:
                return redirect('/login')






#-----------------------------------------------------------------------------------------------------------

# Route for displaying the employee profile
        @self.app.route('/employee/profile', methods=['GET', 'POST'])
        def employee_profile():
            if 'username' in session and session['role'] == 'employee':
                cur = self.mysql.connection.cursor()

                # Fetch user data for top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()
                #-----------------------------------------------

                # Get the employee ID from the users table using the logged-in username
                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    return redirect('/login')

                employee_id = result[0]

                # Fetch employee details from the database, including shift times
                cur.execute("""
                    SELECT e.id, e.first_name, e.last_name, e.gender, d.name as department,
                        CONCAT(TIME_FORMAT(s.start_time, '%%h:%%i %%p'), ' - ', TIME_FORMAT(s.end_time, '%%h:%%i %%p')) as shift_time,
                        e.profile_picture
                    FROM employees e
                    LEFT JOIN shifts s ON e.shift = s.id
                    LEFT JOIN departments d ON e.department = d.id
                    WHERE e.id = %s
                """, (employee_id,))
                employee_data = cur.fetchone()

                # Check if the employee data exists to avoid IndexError
                if employee_data:
                    # Map the employee details into a dictionary
                    employee = {
                        'employee_id': employee_data[0],
                        'first_name': employee_data[1],
                        'last_name': employee_data[2],
                        'gender': employee_data[3],
                        'department': employee_data[4],
                        'shift': employee_data[5],  # Now contains the shift time in AM/PM format
                        'profile_picture_url': url_for('static', filename='uploads/' + employee_data[6]) if employee_data[6] else None
                    }

                    return render_template('employee/profile.html', employee=employee, user_data=user_data)
                else:
                    # If no employee data is found, handle it gracefully
                    flash('Employee data not found.')
                    return redirect('/login')
            else:
                # Redirect to login if the session is not valid
                return redirect('/login')





            # Route for uploading profile picture
        @self.app.route('/employee/profile/upload', methods=['POST'])
        def upload_profile_picture():
            if 'username' in session and session['role'] == 'employee':
                cur = self.mysql.connection.cursor()

                # Get the employee ID from the users table using the logged-in username
                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    return redirect('/login')

                employee_id = result[0]

                # Check if the request has the file part
                if 'profile_picture' not in request.files:
                    flash('No file part')
                    return redirect(request.url)

                file = request.files['profile_picture']

                # Check if a file is selected
                if file.filename == '':
                    flash('No selected file')
                    return redirect(request.url)

                # Check if the file is allowed and process it
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(self.app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)

                    # Update the employee's profile picture in the database
                    cur.execute("""
                        UPDATE employees SET profile_picture = %s WHERE id = %s
                    """, (filename, employee_id))
                    self.mysql.connection.commit()

                    flash('Profile picture uploaded successfully!')
                    return redirect('/employee/profile')

            # Redirect to login if the session is not valid
            return redirect('/login')




        # Function to check allowed file types
        def allowed_file(filename):
            ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#---------------------------------------------------------------------------------

        @self.app.route('/employee/history', methods=['GET'])
        def employee_history():
            if 'username' in session and session['role'] == 'employee':
                cur = self.mysql.connection.cursor()

                # Fetch user data for top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Get the employee ID from the users table using the logged-in username
                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    return redirect('/login')

                employee_id = result[0]

                # Fetch attendance history for the employee with formatted check-in and check-out times
                cur.execute("""
                    SELECT
                        a.date,
                        DATE_FORMAT(a.check_in, '%%I:%%i %%p') AS check_in,
                        DATE_FORMAT(a.check_out, '%%I:%%i %%p') AS check_out,
                        e.profile_picture,
                        CONCAT(e.first_name, ' ', e.last_name) AS full_name,
                        CONCAT(DATE_FORMAT(s.start_time, '%%I:%%i %%p'), ' - ', DATE_FORMAT(s.end_time, '%%I:%%i %%p')) AS shift_time,
                        a.status
                    FROM attendance a
                    LEFT JOIN employees e ON a.employee_id = e.id
                    LEFT JOIN shifts s ON e.shift = s.id
                    WHERE a.employee_id = %s
                    ORDER BY a.date DESC
                """, (employee_id,))
                attendance_records = cur.fetchall()

                cur.close()

                return render_template('employee/history.html', attendance_records=attendance_records, user_data=user_data)
            else:
                return redirect('/login')










    def run(self):
        self.app.run(debug=True, port=3000)

if __name__ == "__main__":
    app_instance = EmployeeAttendance(__name__)
    app_instance.run()