from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_mysqldb import MySQL 
from werkzeug.utils import secure_filename 
import os 


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

                cur.execute("SELECT COUNT(*) FROM attendance WHERE status_in = 'On Time'")
                on_time_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM attendance WHERE status_in = 'Late'")
                late_count = cur.fetchone()[0]


                # Query para makuha ang mga recent attendees nga nag-check in sa last 20 minutes
                cur.execute("""
                    SELECT e.first_name, e.last_name, e.profile_picture,
                        IFNULL(DATE_FORMAT(a.check_in, '%h:%i %p'), 'Not Checked In') as check_in,
                        IFNULL(DATE_FORMAT(a.check_out, '%h:%i %p'), 'Not Checked Out') as check_out
                    FROM attendance a
                    LEFT JOIN employees e ON a.employee_id = e.id
                    WHERE TIMESTAMPDIFF(MINUTE, a.check_in, NOW()) <= 20
                    ORDER BY a.date DESC, a.check_in DESC
                    LIMIT 20
                """)
                recent_attendees = cur.fetchall()  # Ginakuha naton ang recent attendees

                # Query to count male and female employees
                cur.execute("SELECT COUNT(*) FROM employees WHERE gender = 'Male'")
                male_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM employees WHERE gender = 'Female'")
                female_count = cur.fetchone()[0]

                # Query to get details of male and female employees
                cur.execute("SELECT first_name, last_name FROM employees WHERE gender = 'Male'")
                male_employees = cur.fetchall()

                cur.execute("SELECT first_name, last_name FROM employees WHERE gender = 'Female'")
                female_employees = cur.fetchall()

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
                                    male_count=male_count,
                                    female_count=female_count,
                                    male_employees=male_employees,
                                    female_employees=female_employees,
                                    user_name=user_name,
                                    user_profile_picture=user_profile_picture,
                                    user_data=user_data)
            else:
                return redirect('/login')


#----------------------------------------------------------

       # Route for managing departments
        @self.app.route('/admin/departments', methods=['GET', 'POST'])
        def manage_departments():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Fetch user data for the admin dashboard top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Default values if no user data is found
                if not user_data:
                    user_data = ('Unknown', 'User', 'default_profile.png')
                
                if request.method == 'POST':
                    department_id = request.form.get('department_id')  
                    department_name = request.form['department_name'].strip()  # Strip whitespace

                    if department_id:  # If department_id exists, update existing department
                        cur.execute("UPDATE departments SET name = %s WHERE id = %s", (department_name, department_id))
                    else:  # Otherwise, insert new department
                        # Check if department name already exists
                        cur.execute("SELECT id FROM departments WHERE name = %s", [department_name])
                        existing_department = cur.fetchone()

                        if existing_department:
                            # Do nothing if department already exists
                            pass
                        else:
                            # Insert the new department
                            cur.execute("INSERT INTO departments (name) VALUES (%s)", [department_name])

                    # Commit changes to the database
                    self.mysql.connection.commit()
                    return redirect('/admin/departments')

                # Fetch departments to display on the page
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()
                cur.close()
                
                return render_template('admin/departments.html', departments=departments, user_data=user_data)
            else:
                return redirect('/login')

        # Route for deleting a department
        @self.app.route('/admin/departments/delete/<int:department_id>', methods=['POST'])
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
        
        # Route for managing employees (GET for display, POST for add/update)
        @self.app.route('/admin/employees', methods=['GET', 'POST'])
        def manage_employees():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Fetch user data for the top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Handle POST request to add or update employee details
                if request.method == 'POST':
                    # Extracting data from the form
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
                        profile_picture.save(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
                        profile_picture_filename = filename

                    # Update existing employee
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
                        # Insert new employee
                        cur.execute(
                            "INSERT INTO employees (first_name, last_name, department, shift, gender, profile_picture) VALUES (%s, %s, %s, %s, %s, %s)",
                            (first_name, last_name, department, shift, gender, profile_picture_filename)
                        )

                        cur.execute("SELECT LAST_INSERT_ID()")
                        new_employee_id = cur.fetchone()[0]

                        # Automatically create user account for the new employee
                        username = request.form['username']
                        password = request.form['password']
                        cur.execute("INSERT INTO users (username, password, role, employee_id) VALUES (%s, %s, 'employee', %s)",
                                    (username, password, new_employee_id))

                    self.mysql.connection.commit()
                    return redirect('/admin/employees')

                # Fetch employee data (excluding admin users)
                cur.execute("""
                    SELECT e.id, e.first_name, e.last_name, d.name, s.lab_name, s.days, 
                        DATE_FORMAT(s.start_time, '%h:%i %p') AS start_time, 
                        DATE_FORMAT(s.end_time, '%h:%i %p') AS end_time, 
                        e.gender, e.profile_picture
                    FROM employees e
                    LEFT JOIN departments d ON e.department = d.id
                    LEFT JOIN shifts s ON e.shift = s.id
                    LEFT JOIN users u ON u.employee_id = e.id
                    WHERE u.role = 'employee'
                """)
                employees = cur.fetchall()

                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                cur.execute("SELECT id, start_time, end_time, days, lab_name FROM shifts")
                shifts = cur.fetchall()

                cur.close()

                # Return employee management page with employees, departments, and shifts data
                return render_template('admin/employees.html', employees=employees, departments=departments, shifts=shifts, user_data=user_data)
            else:
                return redirect('/login')



        # Route for deleting employee and associated data
        @self.app.route('/admin/employees/delete/<int:employee_id>', methods=['POST'])
        def delete_employee(employee_id):
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()
                try:
                    # Delete attendance records related to the employee
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
                flash("Unauthorized action", "danger")
                return redirect('/login')


#----------------------------------------------------------------------------------

        @self.app.route('/admin/shifts/getshift', methods=['GET'])
        def get_shifts_by_lab():
            lab_name = request.args.get('lab_name')  # Get the lab_name from query parameters
            
            # Ensure lab_name is not None or empty
            if not lab_name:
                return jsonify([]), 400  # Return empty list and status 400 if lab_name is not provided

            # Query the shifts table to get shifts based on the selected lab
            cur = self.mysql.connection.cursor()
            cur.execute("SELECT id, days, start_time, end_time FROM shifts WHERE lab_name = %s ORDER BY days", [lab_name])
            shifts = cur.fetchall()
            cur.close()

            # Convert the result into a JSON-compatible format
            shifts_data = [{'id': shift[0], 'days': shift[1], 'start_time': str(shift[2]), 'end_time': str(shift[3])} for shift in shifts]
            
            return jsonify(shifts_data), 200  # Return JSON data and status 200 OK



        @self.app.route('/admin/user', methods=['GET', 'POST'])
        def manage_users():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Fetch user data for the current logged-in admin (top bar details)
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Fetch all users for displaying in the table
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

                # Fetch department details for dropdown
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                # Fetch lab details for dropdown
                cur.execute("SELECT DISTINCT lab_name FROM shifts")
                labs = [lab[0] for lab in cur.fetchall()]

                # Handle form submission and fetch shifts if lab is selected
                shifts = []
                lab_name = request.form.get('lab') or request.args.get('lab_name')
                if lab_name:
                    cur.execute("SELECT id, days, start_time, end_time FROM shifts WHERE lab_name = %s ORDER BY days", [lab_name])
                    shifts = cur.fetchall()

                error_message = None

                if request.method == 'POST':
                    # Handle form submission for adding/updating user
                    user_id = request.form.get('user_id')
                    first_name = request.form['first_name']
                    last_name = request.form['last_name']
                    department = request.form['department'] if request.form.get('role') == 'employee' else None
                    shift = request.form['shift'] if request.form.get('role') == 'employee' else None
                    gender = request.form['gender'] if request.form.get('role') == 'employee' else None
                    username = request.form['username']
                    role = request.form['role']
                    password = request.form['password']

                    # Check if the selected shift is already full
                    if role == 'employee' and shift:
                        cur.execute("SELECT COUNT(*) FROM employees WHERE shift = %s", [shift])
                        employee_count = cur.fetchone()[0]

                        if employee_count >= 2:
                            # If shift is full, show an error message
                            error_message = "Shift is already full. Please select a different shift."
                            cur.close()
                            return render_template('admin/user.html', users=users, departments=departments, labs=labs, shifts=shifts, user_data=user_data, error_message=error_message)

                    # Update existing user
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
                        # Add new user
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
                    cur.close()
                    return redirect('/admin/user')

                cur.close()
                return render_template('admin/user.html', users=users, departments=departments, labs=labs, shifts=shifts, selected_lab=lab_name, user_data=user_data, error_message=error_message)

            else:
                return redirect('/login')


        @self.app.route('/admin/shifts/check_shift_full', methods=['GET'])
        def check_shift_full():
            shift_id = request.args.get('shift_id')
            cur = self.mysql.connection.cursor()

            # Check if shift already has two employees assigned
            cur.execute("""
                SELECT COUNT(*) FROM employees WHERE shift = %s
            """, [shift_id])
            employee_count = cur.fetchone()[0]
            cur.close()

            is_full = employee_count >= 2
            return jsonify({'is_full': is_full})


            
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




        # Updated route for managing shifts
        @self.app.route('/admin/shifts', methods=['GET', 'POST'])
        def manage_shifts():
            if 'username' in session and session['role'] == 'admin':
                cur = self.mysql.connection.cursor()

                # Fetch user data
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
                    lab_name = request.form.get('lab_name')
                    new_lab_name = request.form.get('new_lab_name')
                    days = request.form.get('days')

                    # Use new_lab_name if provided, otherwise use the selected lab_name
                    if new_lab_name:
                        lab_name = new_lab_name

                    if shift_id:
                        # Update existing shift
                        cur.execute("UPDATE shifts SET start_time = %s, end_time = %s, lab_name = %s, days = %s WHERE id = %s", 
                                    (start_time, end_time, lab_name, days, shift_id))
                    else:
                        # Insert new shift
                        cur.execute("INSERT INTO shifts (start_time, end_time, lab_name, days) VALUES (%s, %s, %s, %s)", 
                                    (start_time, end_time, lab_name, days))

                    self.mysql.connection.commit()
                    return redirect('/admin/shifts')

                # Fetch shifts and group them by lab_name and days
                cur.execute("SELECT id, start_time, end_time, lab_name, days FROM shifts ORDER BY lab_name, days")
                shifts = cur.fetchall()

                # Fetch all unique lab names
                cur.execute("SELECT DISTINCT lab_name FROM shifts")
                lab_names = [row[0] for row in cur.fetchall()]
                cur.close()

                # Group shifts by lab and then by day
                shifts_by_lab = {}
                for shift in shifts:
                    lab = shift[3]  # Lab name
                    day = shift[4]  # Day of the week

                    if lab not in shifts_by_lab:
                        shifts_by_lab[lab] = {}
                    
                    if day not in shifts_by_lab[lab]:
                        shifts_by_lab[lab][day] = []

                    shifts_by_lab[lab][day].append(shift)

                return render_template('admin/shifts.html', shifts_by_lab=shifts_by_lab, user_data=user_data, lab_names=lab_names)
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
                    SELECT 
                        e.first_name, 
                        e.last_name, 
                        e.profile_picture, 
                        d.name,
                        DATE_FORMAT(a.check_in, '%%h:%%i %%p') as check_in,
                        DATE_FORMAT(a.check_out, '%%h:%%i %%p') as check_out,
                        a.status_in, 
                        a.status_out, 
                        a.id, 
                        DATE_FORMAT(a.date, '%%Y-%%m-%%d') as formatted_date
                    FROM 
                        attendance a
                    LEFT JOIN 
                        employees e ON a.employee_id = e.id
                    LEFT JOIN 
                        departments d ON e.department = d.id

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

                status_in = request.form['status_in']
                status_out = request.form['status_out']
                query = """
                    UPDATE attendance
                    SET check_in = %s, check_out = %s, status_in = %s, status_out = %s
                    WHERE id = %s
                """
                cur.execute(query, (check_in, check_out, status_in, status_out, attendance_id))

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
            
            
        from flask import request, jsonify
        from datetime import timedelta

        # Route to calculate total hours rendered by an employee
        @self.app.route('/admin/attendance/calculate', methods=['POST'])
        def calculate_hours():
            if 'username' in session and session['role'] == 'admin':
                employee_name = request.form.get('employee_name')
                employee_id = None

                # Split the name into first name and last name
                first_name, last_name = employee_name.split()

                # Get employee ID from the name
                cur = self.mysql.connection.cursor()
                cur.execute("""
                    SELECT id FROM employees WHERE first_name = %s AND last_name = %s
                """, (first_name, last_name))
                employee_id = cur.fetchone()

                if employee_id:
                    employee_id = employee_id[0]

                    # Calculate total hours for this employee
                    cur.execute("""
                        SELECT TIMEDIFF(check_out, check_in) as duty_hours
                        FROM attendance
                        WHERE employee_id = %s
                    """, (employee_id,))
                    hours_data = cur.fetchall()

                    total_hours = timedelta()
                    for row in hours_data:
                        duty_hours = row[0]
                        if duty_hours:
                            h, m, s = map(int, str(duty_hours).split(':'))
                            total_hours += timedelta(hours=h, minutes=m, seconds=s)

                    # Close the cursor
                    cur.close()

                    # Return the total hours as a response
                    return jsonify({
                        'total_hours': str(total_hours)
                    })
                else:
                    return jsonify({'error': 'Employee not found'}), 404
            else:
                return jsonify({'error': 'Unauthorized access'}), 403


#---------------------------------------------------------------------------

                
            
            
        from datetime import datetime, timedelta

        # Route para sa employee attendance (GET para sa display, POST para sa time-in/time-out)
        @self.app.route('/employee/attendance', methods=['GET', 'POST'])
        def employee_attendance():
            if 'username' in session and session['role'] == 'employee':
                cur = self.mysql.connection.cursor()

                # Fetch user data
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

                # Fetch assigned shift times for the employee
                cur.execute("""
                    SELECT s.start_time, s.end_time
                    FROM employees e
                    JOIN shifts s ON e.shift = s.id
                    WHERE e.id = %s
                """, [employee_id])
                shift = cur.fetchone()
                shift_start = shift[0]
                shift_end = shift[1]

                # Check if there's already an attendance record for today
                cur.execute("""
                    SELECT check_in, check_out, status_in, status_out, DATE(date)
                    FROM attendance
                    WHERE employee_id = %s AND DATE(date) = CURDATE()""", [employee_id])
                attendance_record = cur.fetchone()

                already_checked_in = False
                already_checked_out = False
                status_in = None
                status_out = None

                if attendance_record:
                    check_in_time, check_out_time, status_in, status_out, record_date = attendance_record
                    if check_in_time and not check_out_time:
                        already_checked_in = True
                    elif check_in_time and check_out_time:
                        already_checked_out = True

                if request.method == 'POST':
                    action = request.form['action']  # Determine if 'time_in' or 'time_out' action

                    if action == 'time_in':
                        if already_checked_out:
                            flash("Today, only one time in and time out allowed. See you tomorrow.", "warning")
                            return redirect('/employee/attendance')
                        elif already_checked_in:
                            flash("You are already checked in. Please check out when you finish.", "info")
                        else:
                            # Insert a new check-in record with the current time and calculate the status_in
                            cur.execute("""
                                INSERT INTO attendance (employee_id, check_in, date)
                                VALUES (%s, NOW(), NOW())""", [employee_id])
                            self.mysql.connection.commit()

                            # Fetch the check-in time and determine status_in
                            cur.execute("SELECT TIME(check_in) FROM attendance WHERE employee_id = %s AND DATE(date) = CURDATE()", [employee_id])
                            check_in_time = cur.fetchone()[0]
                            status_in = "Late" if check_in_time > shift_start else "On Time"

                            # Update the status_in for the newly created record
                            cur.execute("""
                                UPDATE attendance
                                SET status_in = %s
                                WHERE employee_id = %s AND DATE(date) = CURDATE()""", (status_in, employee_id))
                            self.mysql.connection.commit()

                            flash(f"Checked in successfully. Status: {status_in}", "success")
                            return redirect('/employee/attendance')

                    elif action == 'time_out':
                        if not already_checked_in:
                            flash("You haven't checked in yet!", "danger")
                            return redirect('/employee/attendance')
                        else:
                            # Update only the check-out time for the existing record
                            cur.execute("""
                                UPDATE attendance
                                SET check_out = NOW()
                                WHERE employee_id = %s AND DATE(date) = CURDATE()""", [employee_id])
                            self.mysql.connection.commit()

                            # Calculate status_out based on check-out time compared to shift end
                            cur.execute("SELECT TIME(check_out) FROM attendance WHERE employee_id = %s AND DATE(date) = CURDATE()", [employee_id])
                            check_out_time = cur.fetchone()[0]

                            # Set status_out based on the check-out conditions
                            status_out = "Early Out" if check_out_time < shift_end else ("On Time" if check_out_time <= (datetime.combine(datetime.today(), shift_end) + timedelta(minutes=20)).time() else "Overtime")

                            # Update the status_out in the record
                            cur.execute("""
                                UPDATE attendance
                                SET status_out = %s
                                WHERE employee_id = %s AND DATE(date) = CURDATE()""", (status_out, employee_id))
                            self.mysql.connection.commit()

                            flash(f"Checked out successfully. Status: {status_out}", "success")
                            return redirect('/employee/attendance')

                cur.close()
                return render_template('employee/attendance.html', already_checked_in=already_checked_in, already_checked_out=already_checked_out, user_data=user_data)
            else:
                return redirect('/login')



            
            
        @self.app.route('/admin/cleanup')
        def cleanup_attendance_records():
            cur = self.mysql.connection.cursor()

            # Delete records where check_out is not recorded within an hour of shift end time
            cur.execute("""
                DELETE a
                FROM attendance a
                JOIN employees e ON a.employee_id = e.id
                JOIN shifts s ON e.shift = s.id
                WHERE a.check_out IS NULL
                AND TIMESTAMPDIFF(HOUR, CONCAT(a.date, ' ', s.end_time), NOW()) >= 1
            """)
            self.mysql.connection.commit()
            cur.close()

            return jsonify({'message': 'Old incomplete records cleaned up successfully'}), 200

                            
                    

#-----------------------------------------------------------------------------------------------------------

        # Route para ipakita ang employee profile
        @self.app.route('/employee/profile', methods=['GET', 'POST'])
        def employee_profile():
            if 'username' in session and session['role'] == 'employee':
                cur = self.mysql.connection.cursor()

                # Fetch user details for the top bar
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
                
                # Fetching the employee details from the database, including shift details, lab, and day
                cur.execute("""
                    SELECT e.id, e.first_name, e.last_name, e.gender, d.name as department,
                        CONCAT(TIME_FORMAT(s.start_time, '%%h:%%i %%p'), ' - ', TIME_FORMAT(s.end_time, '%%h:%%i %%p')) as shift_time,
                        s.lab_name, s.days, e.profile_picture
                    FROM employees e
                    LEFT JOIN shifts s ON e.shift = s.id
                    LEFT JOIN departments d ON e.department = d.id
                    WHERE e.id = %s
                """, (employee_id,))
                employee_data = cur.fetchone()

                # Checking if employee data is found to avoid errors
                if employee_data:
                    employee = {
                        'employee_id': employee_data[0],
                        'first_name': employee_data[1],
                        'last_name': employee_data[2],
                        'gender': employee_data[3],
                        'department': employee_data[4],
                        'shift': employee_data[5],
                        'lab_name': employee_data[6],
                        'day': employee_data[7],
                        'profile_picture_url': url_for('static', filename='uploads/' + employee_data[8]) if employee_data[8] else None
                    }
                    
                    # Returning the employee profile page with the employee details
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
                        a.status_in, a.status_out
                    FROM attendance a
                    LEFT JOIN employees e ON a.employee_id = e.id
                    LEFT JOIN shifts s ON e.shift = s.id
                    WHERE a.employee_id = %s
                    ORDER BY a.date DESC
                """, (employee_id,))
                attendance_records = cur.fetchall()

                cur.close()

                # Ensure that each record includes a proper status for check-out display in the template
                # If any missing or specific status handling is required, handle it here

                # Ginabalik naton ang attendance history page upod ang list sang attendance records kag user data
                return render_template('employee/history.html', attendance_records=attendance_records, user_data=user_data)
            else:
                return redirect('/login')

    # Function para paandaron ang Flask application
    def run(self):
        self.app.run(debug=True) #host='',

# Main function para mag-instantiate sang EmployeeAttendance class kag i-run ang Flask app
if __name__ == "__main__":
    x = EmployeeAttendance(__name__)
    x.run()
