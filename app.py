# Import sang Flask para magamit ang mga functionalities like route handling, templates, and session management
from flask import Flask, render_template, request, redirect, session, flash, url_for 
from flask_mysqldb import MySQL # Import sang MySQL module para maka-connect sa MySQL database using Flask
from werkzeug.utils import secure_filename # Import sang secure_filename halin sa werkzeug para mag-handle sang uploaded files safely
# import random
import os # Import os module para ma-handle ang file paths kag operating system functions

# Define sang EmployeeAttendance class
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
        
        # Ginaset ang directory sa diin ibutang ang uploaded files
        self.app.config['UPLOAD_FOLDER'] = 'static/uploads'
        
        # Ginaset naton ang mga routes para sa application
        self.setup_routes()
        
    # Function para iset up ang mga routes sang app
    def setup_routes(self):
        # Route para sa home page
        @self.app.route('/')
        def home():
            return render_template('layout/home.html')
        
        # Route para sa login page
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                # Ginakuha ang username kag password halin sa form inputs
                username = request.form['username']
                password = request.form['password']
                
                # Query para macheck ang credentials sang user (username kag password)
                cur = self.mysql.connection.cursor()
                cur.execute("SELECT role FROM users WHERE username=%s AND password=%s", (username, password))
                user = cur.fetchone()
                cur.close()
                
                # Kung may nakuha nga user
                if user:
                    session['username'] = username
                    session['role'] = user[0]
                    
                    # Gacheck kung ang role sang user admin or employee, kag ginaredirect naton sila accordingly
                    if user[0] == 'admin':
                        return redirect('/admin/dashboard')
                    elif user[0] == 'employee':
                        return redirect('/employee/attendance')
                else:
                    # Kung sala ang credentials, balik sa login page kag show sang error message
                    return render_template('layout/login.html', error="Invalid credentials. Please try again.")

            return render_template('layout/login.html')
        
        # Route para sa logout
        @self.app.route('/logout')
        def logout():
            session.pop('username', None)
            session.pop('role', None)
            return redirect('/')

#------------------------------------------------------------------------------------

        # Route para sa Admin Dashboard
        @self.app.route('/admin/dashboard')
        def admin_dashboard():
            # Check naton kon ang user naka-login kag admin siya
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                
                # Query para makuha ang user details nga gamiton sa top bar base sa logged-in admin
                cur.execute("""
                    SELECT e.first_name, e.last_name, e.profile_picture
                    FROM users u
                    LEFT JOIN employees e ON u.employee_id = e.id
                    WHERE u.username = %s
                """, [session['username']])
                user_data = cur.fetchone()
                
                # Ginatipon naton ang data para sa user profile
                if user_data:
                    user_name = f"{user_data[0]} {user_data[1]}"
                    # Check naton kun may ara sang profile picture, kung wala default picture ang gamiton
                    user_profile_picture = url_for('static', filename='uploads/' + user_data[2]) if user_data[2] else url_for('static', filename='uploads/default_profile.png')
                else:
                    user_name = 'Unknown'
                    user_profile_picture = url_for('static', filename='uploads/default_profile.png')
                
                # Modify the query to count only employees (excluding admins)
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM employees e
                    JOIN users u ON e.id = u.employee_id
                    WHERE u.role = 'employee'
                """)
                employee_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM shifts")
                shift_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM attendance")
                attendance_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM users")
                user_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM attendance WHERE status = 'On Time'")
                on_time_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM attendance WHERE status = 'Late'")
                late_count = cur.fetchone()[0]

                # Query para makuha ang mga recent attendees nga nag-check in sa last 20 minutes
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
                recent_attendees = cur.fetchall() # Ginakuha naton ang recent attendees

                cur.close()
                # Ginapasa naton ang mga data sa template para ma-display sa admin dashboard
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

        # Routes para sa Department Management
        @self.app.route('/admin/departments', methods=['GET', 'POST'])
        def manage_departments():
            # Check naton kon ang user naka-login kag admin siya
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                
                # Gakuha kita sang user data para sa top bar sang admin dashboard
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Kon wala nakuha nga user data, may default values kita
                if not user_data:
                    user_data = ('Unknown', 'User', 'default_profile.png')
                    
                # Kon POST request (kung may form submission)
                if request.method == 'POST':
                    department_id = request.form.get('department_id')
                    department_name = request.form['department_name']

                    # Kung may department ID, ginaupdate naton ang existing department
                    if department_id:
                        cur.execute("UPDATE departments SET name = %s WHERE id = %s", (department_name, department_id))
                    else:
                        # Generate sang department ID base sa initials sang department name
                        department_id = ''.join([word[0].upper() for word in department_name.split()])

                        # Gacheck naton kun may ara existing nga department ID
                        cur.execute("SELECT id FROM departments WHERE id = %s", [department_id])
                        existing_department = cur.fetchone()

                        # Kung may existing na department, ginabalik naton ang page kag ginasend ang error message
                        if existing_department:
                            return render_template('admin/departments.html', error="Department ID already exists", departments=[], user_data=user_data)

                        # Kon wala pa, ginainsert naton ang bagong department
                        cur.execute("INSERT INTO departments (id, name) VALUES (%s, %s)", (department_id, department_name))

                    self.mysql.connection.commit()
                    return redirect('/admin/departments')

                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()
                cur.close()
                return render_template('admin/departments.html', departments=departments, user_data=user_data)
            else:
                return redirect('/login')

        # Route para mag-delete sang department
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

        # Set up sang allowed file extensions para sa uploads
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
        
        # Function para macheck kun ang file nga i-upload allowed
        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
        
        # Route para sa employee management (GET para sa display, POST para sa pag-add/update)
        @self.app.route('/admin/employees', methods=['GET', 'POST'])
        def manage_employees():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                
                # Gakuha naton ang user data para sa top bar sang page
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Handle POST request para sa pag-add or update sang employee details
                if request.method == 'POST':
                    # Ginakuha naton ang details and etc halin sa form
                    employee_id = request.form.get('employee_id')
                    first_name = request.form['first_name']
                    last_name = request.form['last_name']
                    department = request.form['department']
                    shift = request.form['shift']
                    gender = request.form['gender']
                    profile_picture = request.files.get('profile_picture')

                    # Handling sang profile picture upload
                    profile_picture_filename = None  # Default value kon wala sang profile picture
                    if profile_picture and allowed_file(profile_picture.filename):  # Ginacheck kun may profile picture kag allowed ang file type
                        filename = secure_filename(profile_picture.filename)  # Ginasanitize ang filename
                        profile_picture.save(os.path.join('static/uploads', filename))  # Ginastore naton ang file sa upload directory
                        profile_picture_filename = filename  # Ginaset naton ang filename para ma-store sa database

                    # Kung may employee ID, ginaupdate naton ang existing employee
                    if employee_id:
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
                        cur.execute(
                            "INSERT INTO employees (first_name, last_name, department, shift, gender, profile_picture) VALUES (%s, %s, %s, %s, %s, %s)",
                            (first_name, last_name, department, shift, gender, profile_picture_filename)
                        )

                        cur.execute("SELECT LAST_INSERT_ID()")
                        new_employee_id = cur.fetchone()[0]

                        # Automatically ginacrete naton ang user account para sa bagong employee
                        username = request.form['username']
                        password = request.form['password']
                        cur.execute("INSERT INTO users (username, password, role, employee_id) VALUES (%s, %s, 'employee', %s)",
                                    (username, password, new_employee_id))

                    self.mysql.connection.commit()
                    return redirect('/admin/employees')

                # Query para makuha ang employee data (excluding admin users)
                cur.execute("""
                    SELECT e.id, e.first_name, e.last_name, d.name, CONCAT(s.start_time, ' - ', s.end_time) AS shift_time, e.gender, e.profile_picture
                    FROM employees e
                    LEFT JOIN departments d ON e.department = d.id
                    LEFT JOIN shifts s ON e.shift = s.id
                    LEFT JOIN users u ON u.employee_id = e.id
                    WHERE u.role = 'employee'
                """)
                employees = cur.fetchall()

                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                cur.execute("SELECT id, start_time, end_time FROM shifts")
                shifts = cur.fetchall()

                cur.close()

                # Ginabalik naton ang employee management page upod ang data sang employees, departments, kag shifts
                return render_template('admin/employees.html', employees=employees, departments=departments, shifts=shifts, user_data=user_data)
            else:
                return redirect('/login')

        # Route para mag-delete sang employee kag associated data
        @self.app.route('/admin/employees/delete/<int:employee_id>', methods=['POST'])
        def delete_employee(employee_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                try:
                    # Gadelete kita sang attendance records nga related sa employee
                    cur.execute("DELETE FROM attendance WHERE employee_id = %s", [employee_id])
                    cur.execute("DELETE FROM users WHERE employee_id = %s", [employee_id])
                    cur.execute("DELETE FROM employees WHERE id = %s", [employee_id])
                    self.mysql.connection.commit()

                    flash("Employee and associated records deleted successfully.", "success")
                except Exception as e:
                    flash(f"Error deleting employee: {e}", "danger")
                finally:
                    cur.close()
                return redirect('/admin/employees')
            else:
                flash("Unauthorized action", "danger") # Error message kun indi authorized ang user
                return redirect('/login')

#----------------------------------------------------------------------------------

        # Route para sa user management (GET para sa display, POST para sa pag-add/update)
        @self.app.route('/admin/user', methods=['GET', 'POST'])
        def manage_users():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()
                
                # Handle POST request para sa pag-add or update sang user details
                if request.method == 'POST':
                     # Ginakuha naton ang details and etc halin sa form
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
                        cur.execute("""
                            UPDATE employees SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s
                            WHERE id=%s
                        """, (first_name, last_name, department, shift, gender, user_id))
                        cur.execute("""
                            UPDATE users SET username=%s, password=%s, role=%s
                            WHERE id=%s
                        """, (username, password, role, user_id))
                    else:
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
            
        # Route para mag-delete sang user
        @self.app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
        def delete_user(user_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                try:
                    cur.execute("SELECT employee_id FROM users WHERE id = %s", [user_id])
                    employee_id_result = cur.fetchone()

                    if employee_id_result:
                        employee_id = employee_id_result[0]

                        cur.execute("DELETE FROM attendance WHERE employee_id = %s", [employee_id])
                        cur.execute("DELETE FROM employees WHERE id = %s", [employee_id])

                    cur.execute("DELETE FROM users WHERE id = %s", [user_id])
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

        # Routes para sa Shift Management
        @self.app.route('/admin/shifts', methods=['GET', 'POST'])
        def manage_shifts():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                if request.method == 'POST':
                    shift_id = request.form.get('shift_id')
                    start_time = request.form.get('start_time')
                    end_time = request.form.get('end_time')

                    if shift_id:
                        cur.execute("UPDATE shifts SET start_time = %s, end_time = %s WHERE id = %s", (start_time, end_time, shift_id))
                    else:
                        cur.execute("INSERT INTO shifts (start_time, end_time) VALUES (%s, %s)", (start_time, end_time))

                    self.mysql.connection.commit()
                    return redirect('/admin/shifts')

                cur.execute("SELECT id, start_time, end_time FROM shifts")
                shifts = cur.fetchall()
                cur.close()

                return render_template('admin/shifts.html', shifts=shifts, user_data=user_data)
            else:
                return redirect('/login')

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

        # Route para sa Admin Attendance Report
        @self.app.route('/admin/attendance', methods=['GET'])
        def attendance_report():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                department = request.args.get('department')

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

        # Route para mag-update sang attendance record
        @self.app.route('/admin/attendance/update', methods=['POST'])
        def update_attendance():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                attendance_id = request.form['attendance_id']
                check_in = request.form['check_in']
                check_out = request.form['check_out']
                status = request.form['status']

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

        # Route para mag-delete sang attendance record
        @self.app.route('/admin/attendance/delete/<int:attendance_id>', methods=['POST'])
        def delete_attendance(attendance_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                query = "DELETE FROM attendance WHERE id = %s"
                cur.execute(query, [attendance_id])
                self.mysql.connection.commit()

                cur.close()

                flash('Attendance record deleted successfully!', 'success')
                return redirect('/admin/attendance')
            else:
                return redirect('/login')

#---------------------------------------------------------------------------

        # Route para sa employee attendance (GET para sa display, POST para sa time-in/time-out)
        @self.app.route('/employee/attendance', methods=['GET', 'POST'])
        def employee_attendance():
            if 'username' in session and session['role'] == 'employee':
                cur = self.mysql.connection.cursor()

                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    return redirect('/login')

                employee_id = result[0]
                
                # Gakuha naton ang assigned shift times sang employee
                cur.execute("""
                    SELECT s.start_time, s.end_time
                    FROM employees e
                    JOIN shifts s ON e.shift = s.id
                    WHERE e.id = %s
                """, [employee_id])
                shift = cur.fetchone()
                shift_start = shift[0]
                shift_end = shift[1]
                
                # Gacheck naton kun may attendance record na ang employee subong nga adlaw
                cur.execute("""
                    SELECT check_in, check_out, DATE(date)
                    FROM attendance
                    WHERE employee_id = %s AND DATE(date) = CURDATE()""", [employee_id])
                attendance_record = cur.fetchone()
                
                # Gacheck naton kun naka-check-in na or naka-check-out na ang employee
                already_checked_in = False
                already_checked_out = False

                if attendance_record:
                    check_in_time, check_out_time, record_date = attendance_record
                    if check_in_time and not check_out_time:
                        already_checked_in = True
                    elif check_in_time and check_out_time:
                        already_checked_out = True

                # Kung ang method POST, handle naton ang time-in or time-out action
                if request.method == 'POST':
                    action = request.form['action'] # Ginakuha naton kun 'time_in' or 'time_out' ang action

                    if action == 'time_in':
                        if already_checked_out:
                            # Kung naka-check-out na ang employee, ginasend naton ang warning
                            flash("Today, only one time in and time out allowed. See you tomorrow.", "warning")
                            return redirect('/employee/attendance')
                        elif already_checked_in:
                            # Kung naka-check-in na pero wala pa naka-check-out, ginasend ang info message
                            flash("You are already checked in. Please check out when you finish.", "info")
                        else:
                            # Kung wala pa sang check-in, gina-insert naton ang new check-in record
                            cur.execute("""
                                INSERT INTO attendance (employee_id, check_in, date)
                                VALUES (%s, NOW(), NOW())""", [employee_id])
                            self.mysql.connection.commit()

                            # Gina-calculate naton ang status (Late or On Time)
                            cur.execute("SELECT TIME(check_in) FROM attendance WHERE employee_id = %s AND DATE(date) = CURDATE()", [employee_id])
                            check_in_time = cur.fetchone()[0]

                            if check_in_time > shift_start:
                                status = "Late"
                            else:
                                status = "On Time"

                            # Gina-update naton ang status sang attendance
                            cur.execute("""
                                UPDATE attendance
                                SET status = %s
                                WHERE employee_id = %s AND DATE(date) = CURDATE()""", (status, employee_id))
                            self.mysql.connection.commit()

                            flash(f"Checked in successfully. Status: {status}", "success")
                            return redirect('/employee/attendance')

                    elif action == 'time_out':
                        if not already_checked_in:
                            # Kung wala pa naka-check-in ang employee, ginasend naton ang error message
                            flash("You haven't checked in yet!", "danger")
                            return redirect('/employee/attendance')
                        else:   
                            # Kung naka-check-in na, gina-update naton ang check-out time
                            cur.execute("""
                                UPDATE attendance
                                SET check_out = NOW()
                                WHERE employee_id = %s AND DATE(date) = CURDATE()""", [employee_id])
                            self.mysql.connection.commit()

                            # Gina-calculate naton kun may overtime
                            cur.execute("SELECT TIME(check_out) FROM attendance WHERE employee_id = %s AND DATE(date) = CURDATE()", [employee_id])
                            check_out_time = cur.fetchone()[0]

                            if check_out_time > shift_end:
                                status = "Overtime"
                            else:
                                status = "On Time"
                                
                            # Gina-update naton ang status sang attendance
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

        # Route para ipakita ang employee profile
        @self.app.route('/employee/profile', methods=['GET', 'POST'])
        def employee_profile():
            if 'username' in session and session['role'] == 'employee':
                cur = self.mysql.connection.cursor()

                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    return redirect('/login')

                employee_id = result[0]
                
                # Gakuha naton ang employee details halin sa database, upod ang shift times
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

                # Gacheck naton kun may data sang employee para malikawan ang error
                if employee_data:
                    employee = {
                        'employee_id': employee_data[0],
                        'first_name': employee_data[1],
                        'last_name': employee_data[2],
                        'gender': employee_data[3],
                        'department': employee_data[4],
                        'shift': employee_data[5],
                        'profile_picture_url': url_for('static', filename='uploads/' + employee_data[6]) if employee_data[6] else None
                    }
                    
                    # Ginabalik naton ang employee profile page kag ginapasa ang employee details
                    return render_template('employee/profile.html', employee=employee, user_data=user_data)
                else:
                    flash('Employee data not found.')
                    return redirect('/login')
            else:
                return redirect('/login')

        # Route para mag-upload sang profile picture sang employee
        @self.app.route('/employee/profile/upload', methods=['POST'])
        def upload_profile_picture():
            if 'username' in session and session['role'] == 'employee':
                cur = self.mysql.connection.cursor()

                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    return redirect('/login')

                employee_id = result[0]

                if 'profile_picture' not in request.files:
                    flash('No file part')
                    return redirect(request.url)

                file = request.files['profile_picture'] # Ginakuha naton ang uploaded file

                # Gacheck naton kun may file nga na-select
                if file.filename == '':
                    flash('No selected file')
                    return redirect(request.url)

                # Gacheck naton kun allowed ang file kag gina-process ini
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename) # Ginsecure naton ang file name
                    filepath = os.path.join(self.app.config['UPLOAD_FOLDER'], filename) # Ginstore naton sa upload folder
                    file.save(filepath)

                    cur.execute("""
                        UPDATE employees SET profile_picture = %s WHERE id = %s
                    """, (filename, employee_id))
                    self.mysql.connection.commit()

                    flash('Profile picture uploaded successfully!')
                    return redirect('/employee/profile')

            return redirect('/login')

        def allowed_file(filename):
            ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#---------------------------------------------------------------------------------

        # Route para ipakita ang attendance history sang employee
        @self.app.route('/employee/history', methods=['GET'])
        def employee_history():
            if 'username' in session and session['role'] == 'employee':
                cur = self.mysql.connection.cursor()

                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    return redirect('/login')

                employee_id = result[0]

                # Gakuha naton ang attendance history sang employee upod ang formatted check-in kag check-out times
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
                
                # Ginabalik naton ang attendance history page upod ang list sang attendance records kag user data
                return render_template('employee/history.html', attendance_records=attendance_records, user_data=user_data)
            else:
                return redirect('/login')

    # Function para paandaron ang Flask application
    def run(self):
        self.app.run(debug=True, port=3000)

# Main function para mag-instantiate sang EmployeeAttendance class kag i-run ang Flask app
if __name__ == "__main__":
    x = EmployeeAttendance(__name__)
    x.run()
