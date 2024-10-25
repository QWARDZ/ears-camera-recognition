from flask import Flask, render_template, request, jsonify, session, redirect, flash, url_for
import cv2
import numpy as np
import os
import base64
import pymysql
from werkzeug.utils import secure_filename
from flask_session import Session
import base64
import io
from flask import jsonify
import face_recognition
from datetime import timedelta


class EmployeeAttendance:
    def __init__(self, name):
        self.app = Flask(name)
        self.app.secret_key = 'your_secret_key'
        self.app.config['UPLOAD_FOLDER'] = 'static/uploads'

        # Flask-Session config for server-side sessions
        self.app.config['SESSION_TYPE'] = 'filesystem'  # Server-side sessions
        self.app.config['SESSION_PERMANENT'] = True
        self.app.config['SESSION_USE_SIGNER'] = True
        Session(self.app)  # Initialize Flask-Session

        # Initialize routes
        self.setup_routes()

    def ears_db (self):
        return pymysql.connect(
            host='localhost',
            user='root',
            password='',
            db='ears_db',
            ssl={'disabled': True}
        )

#-------------------------------------------------------------------------------------------------------

    # Define the `extract_face` method to handle face extraction.
    def extract_face(self, image):
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3)
        if len(faces) == 0:
            return None
        x, y, w, h = faces[0]
        return gray[y:y + h, x:x + w]
#-----------------------------------------------------------------------------------------------------
    # Function to set up the routes
    def setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('layout/login.html')
        
#---------------------------------------------------------------------------------------------------

        @self.app.route('/verify_face', methods=['POST'])
        def verify_face():
            if 'username' in session and session['role'] == 'employee':
                # Get the captured image from the request
                data = request.json
                image_data = data.get('image')

                # Process the image data
                if image_data:
                    try:
                        # Decode the base64 image data from the request
                        image_data = image_data.split(",")[1]
                        image_bytes = base64.b64decode(image_data)
                        image = face_recognition.load_image_file(io.BytesIO(image_bytes))

                        # Find face encodings in the captured image
                        captured_face_encodings = face_recognition.face_encodings(image)

                        if len(captured_face_encodings) > 0:
                            captured_face_encoding = captured_face_encodings[0]

                            # Fetch employee profile picture for comparison
                            conn = self.ears_db()
                            cur = conn.cursor()

                            cur.execute("""
                                SELECT profile_picture
                                FROM employees
                                WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                            """, [session['username']])

                            user_data = cur.fetchone()

                            if user_data and user_data[0]:
                                profile_picture_filename = user_data[0]
                                profile_picture_path = os.path.join('static/uploads/', profile_picture_filename)

                                # Load the employee's profile picture
                                employee_profile_picture = face_recognition.load_image_file(profile_picture_path)
                                employee_face_encodings = face_recognition.face_encodings(employee_profile_picture)

                                if len(employee_face_encodings) > 0:
                                    employee_face_encoding = employee_face_encodings[0]

                                    # Lower the tolerance to make the match stricter (default tolerance is 0.6)
                                    tolerance = 0.4  # Lower tolerance for stricter match

                                    # Compare the captured face with the employee's profile picture
                                    results = face_recognition.compare_faces([employee_face_encoding], captured_face_encoding, tolerance=tolerance)

                                    # Calculate face distance to see how close the match is
                                    face_distance = face_recognition.face_distance([employee_face_encoding], captured_face_encoding)

                                    if results[0]:
                                        return jsonify({
                                            "success": True,
                                            "message": "Face verified successfully",
                                            "face_distance": face_distance[0]  # Include the distance for more insights
                                        })
                                    else:
                                        return jsonify({
                                            "success": False,
                                            "message": "Face verification failed, no match",
                                            "face_distance": face_distance[0]  # Include the distance to understand the mismatch
                                        })
                                else:
                                    return jsonify({"success": False, "message": "No face found in profile picture"})
                            else:
                                return jsonify({"success": False, "message": "Profile picture not found"})

                        else:
                            return jsonify({"success": False, "message": "No face found in the captured image"})

                    except Exception as e:
                        # Handle any exceptions during face processing
                        return jsonify({"success": False, "message": str(e)})

            return jsonify({"success": False, "message": "Unauthorized access"})
        
        
#-------------------------------------------------------------------------------------------


        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                conn = self.ears_db()
                cur = conn.cursor()
                cur.execute("SELECT id, role, employee_id FROM users WHERE username=%s AND password=%s", (username, password))
                user = cur.fetchone()
                cur.close()
                conn.close()

                if user:
                    session['username'] = username
                    session['role'] = user[1]
                    session['employee_id'] = user[2]  # Make sure this is set to the correct employee_id

                    if user[1] == 'admin':
                        return redirect('/admin/dashboard')
                    elif user[1] == 'employee':
                        return redirect('/employee/attendance')
                else:
                    flash("Invalid username or password", "danger")
                    return render_template('layout/login.html')
            else:
                return render_template('layout/login.html')

        @self.app.route('/logout')
        def logout():
            # Clear the session data
            session.clear()
            # Redirect to the login page after logging out
            return redirect('/login')


#-----------------------------------------------------------

        @self.app.route('/admin/dashboard')
        def admin_dashboard():
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()
                cur = conn.cursor()

                cur.execute("""
                    SELECT e.first_name, e.last_name, e.profile_picture
                    FROM users u
                    LEFT JOIN employees e ON u.employee_id = e.id
                    WHERE u.username = %s
                """, [session['username']])
                user_data = cur.fetchone()

                user_name = f"{user_data[0]} {user_data[1]}" if user_data else 'Unknown'
                user_profile_picture = url_for('static', filename='uploads/' + user_data[2]) if user_data and user_data[2] else url_for('static', filename='uploads/default_profile.png')

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

                cur.execute("SELECT COUNT(*) FROM attendance WHERE status_out = 'Overtime'")
                overtime_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM attendance WHERE status_out = 'Early Out'")
                early_out_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM employees WHERE gender = 'Male'")
                male_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM employees WHERE gender = 'Female'")
                female_count = cur.fetchone()[0]

                cur.execute("SELECT first_name, last_name FROM employees WHERE gender = 'Male'")
                male_employees = cur.fetchall()

                cur.execute("SELECT first_name, last_name FROM employees WHERE gender = 'Female'")
                female_employees = cur.fetchall()

                cur.execute("""
                    SELECT e.first_name, e.last_name, 
                        CASE WHEN e.profile_picture IS NOT NULL THEN e.profile_picture ELSE 'default_profile.png' END AS profile_picture,
                        IFNULL(DATE_FORMAT(a.check_in, '%h:%i %p'), 'Not Checked In') as check_in,
                        IFNULL(DATE_FORMAT(a.check_out, '%h:%i %p'), 'Not Checked Out') as check_out
                    FROM attendance a
                    LEFT JOIN employees e ON a.employee_id = e.id
                    WHERE TIMESTAMPDIFF(MINUTE, a.check_in, NOW()) <= 20
                    ORDER BY a.date DESC, a.check_in DESC
                    LIMIT 20
                """)
                recent_attendees = cur.fetchall()

                cur.close()

                return render_template('admin/dashboard.html',
                                    employee_count=employee_count,
                                    shift_count=shift_count,
                                    attendance_count=attendance_count,
                                    user_count=user_count,
                                    on_time_count=on_time_count,
                                    late_count=late_count,
                                    overtime_count=overtime_count,
                                    early_out_count=early_out_count,
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


#-----------------------------------------------------------------------------------------------------------------------

        # Route for managing departments
        @self.app.route('/admin/departments', methods=['GET', 'POST'])
        def manage_departments():
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()  # Use the connection function
                cur = conn.cursor()

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
                    conn.commit()
                    cur.close()
                    conn.close()
                    return redirect('/admin/departments')

                # Fetch departments to display on the page
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()
                cur.close()
                conn.close()

                return render_template('admin/departments.html', departments=departments, user_data=user_data)
            else:
                return redirect('/login')

        # Route for deleting a department
        @self.app.route('/admin/departments/delete/<int:department_id>', methods=['POST'])
        def delete_department(department_id):
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM departments WHERE id = %s", [department_id])
                conn.commit()
                cur.close()
                conn.close()
                return redirect('/admin/departments')
            else:
                return redirect('/login')

#-----------------------------------------------------------------------------------------------------

        # Set up allowed file extensions for uploads
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

        # Function to check if the uploaded file is allowed
        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        # Route for managing employees (GET for display, POST for add/update)
        @self.app.route('/admin/employees', methods=['GET', 'POST'])
        def manage_employees():
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()
                cur = conn.cursor()

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
                            cur.execute("""
                                UPDATE employees 
                                SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s, profile_picture=%s 
                                WHERE id=%s
                            """, (first_name, last_name, department, shift, gender, profile_picture_filename, employee_id))
                        else:
                            cur.execute("""
                                UPDATE employees 
                                SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s 
                                WHERE id=%s
                            """, (first_name, last_name, department, shift, gender, employee_id))
                    else:
                        # Insert new employee
                        cur.execute("""
                            INSERT INTO employees (first_name, last_name, department, shift, gender, profile_picture) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (first_name, last_name, department, shift, gender, profile_picture_filename))

                        # Get the newly inserted employee's ID
                        cur.execute("SELECT LAST_INSERT_ID()")
                        new_employee_id = cur.fetchone()[0]

                        # Automatically create user account for the new employee
                        username = request.form['username']
                        password = request.form['password']
                        cur.execute("""
                            INSERT INTO users (username, password, role, employee_id) 
                            VALUES (%s, %s, 'employee', %s)
                        """, (username, password, new_employee_id))

                    conn.commit()  # Commit the changes
                    cur.close()
                    conn.close()

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
                conn.close()

                # Return employee management page with employees, departments, and shifts data
                return render_template('admin/employees.html', employees=employees, departments=departments, shifts=shifts, user_data=user_data)
            else:
                return redirect('/login')

        # Route for deleting employee and associated data
        @self.app.route('/admin/employees/delete/<int:employee_id>', methods=['POST'])
        def delete_employee(employee_id):
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()
                cur = conn.cursor()
                try:
                    # Delete attendance records related to the employee
                    cur.execute("DELETE FROM attendance WHERE employee_id = %s", [employee_id])
                    cur.execute("DELETE FROM users WHERE employee_id = %s", [employee_id])
                    cur.execute("DELETE FROM employees WHERE id = %s", [employee_id])
                    conn.commit()

                    flash("Employee and associated records deleted successfully.", "success")
                except Exception as e:
                    flash(f"Error deleting employee: {e}", "danger")
                finally:
                    cur.close()
                    conn.close()
                return redirect('/admin/employees')
            else:
                flash("Unauthorized action", "danger")
                return redirect('/login')



#--------------------------------------------------------------------------------------------------


        # Flask/Python Backend Code
        @self.app.route('/admin/shifts/getshift', methods=['GET'])
        def get_shifts_by_lab():
            lab_name = request.args.get('lab_name')  # Get the lab_name from query parameters
            
            # Ensure lab_name is not None or empty
            if not lab_name:
                return jsonify([]), 400  # Return empty list and status 400 if lab_name is not provided

            # Query the shifts table to get shifts based on the selected lab
            conn = self.ears_db()
            cur = conn.cursor()
            cur.execute("SELECT id, days, start_time, end_time FROM shifts WHERE lab_name = %s ORDER BY days", [lab_name])
            shifts = cur.fetchall()
            cur.close()
            conn.close()

            # Convert the result into a JSON-compatible format
            shifts_data = [{'id': shift[0], 'days': shift[1], 'start_time': str(shift[2]), 'end_time': str(shift[3])} for shift in shifts]
            
            return jsonify(shifts_data), 200  # Return JSON data and status 200 OK

        # Route for managing users
        @self.app.route('/admin/user', methods=['GET', 'POST'])
        def manage_users():
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()
                cur = conn.cursor()

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

                # Fetch department and lab details for dropdowns
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                cur.execute("SELECT DISTINCT lab_name FROM shifts")
                labs = [lab[0] for lab in cur.fetchall()]

                # Handle form submission
                error_message = None
                if request.method == 'POST':
                    user_id = request.form.get('user_id')
                    first_name = request.form['first_name']
                    last_name = request.form['last_name']
                    department = request.form.get('department') if request.form.get('role') == 'employee' else None
                    shift = request.form.get('shift') if request.form.get('role') == 'employee' else None
                    gender = request.form.get('gender') if request.form.get('role') == 'employee' else None
                    username = request.form['username']
                    role = request.form['role']
                    password = request.form['password']
                    profile_picture = request.files.get('profile_picture')

                    # Handling profile picture upload
                    profile_picture_filename = None
                    if profile_picture and allowed_file(profile_picture.filename):
                        filename = secure_filename(profile_picture.filename)
                        filepath = os.path.join(self.app.config['UPLOAD_FOLDER'], filename)
                        profile_picture.save(filepath)  # Save the file to the uploads directory
                        profile_picture_filename = filename

                    # Update existing user
                    if user_id:
                        if profile_picture_filename:
                            cur.execute("""
                                UPDATE employees 
                                SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s, profile_picture=%s 
                                WHERE id=%s
                            """, (first_name, last_name, department, shift, gender, profile_picture_filename, user_id))
                        else:
                            cur.execute("""
                                UPDATE employees 
                                SET first_name=%s, last_name=%s, department=%s, shift=%s, gender=%s 
                                WHERE id=%s
                            """, (first_name, last_name, department, shift, gender, user_id))
                        
                        # Also update user account
                        cur.execute("""
                            UPDATE users SET username=%s, password=%s, role=%s WHERE id=%s
                        """, (username, password, role, user_id))
                    else:
                        # Insert new employee
                        cur.execute("""
                            INSERT INTO employees (first_name, last_name, department, shift, gender, profile_picture)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (first_name, last_name, department, shift, gender, profile_picture_filename))

                        cur.execute("SELECT LAST_INSERT_ID()")
                        new_employee_id = cur.fetchone()[0]

                        # Insert new user
                        cur.execute("""
                            INSERT INTO users (username, password, role, employee_id) 
                            VALUES (%s, %s, %s, %s)
                        """, (username, password, role, new_employee_id))

                    conn.commit()
                    cur.close()
                    conn.close()

                    return redirect('/admin/user')

                cur.close()
                conn.close()
                return render_template('admin/user.html', users=users, departments=departments, labs=labs, user_data=user_data, error_message=error_message)

            else:
                return redirect('/login')

        def allowed_file(filename):
            ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



        # Route to check if the shift is full
        @self.app.route('/admin/shifts/check_shift_full', methods=['GET'])
        def check_shift_full():
            shift_id = request.args.get('shift_id')
            conn = self.ears_db()
            cur = conn.cursor()

            # Check if shift already has two employees assigned
            cur.execute("""
                SELECT COUNT(*) FROM employees WHERE shift = %s
            """, [shift_id])
            employee_count = cur.fetchone()[0]
            cur.close()
            conn.close()

            is_full = employee_count >= 2
            return jsonify({'is_full': is_full})

        # Route to delete a user
        @self.app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
        def delete_user(user_id):
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()
                cur = conn.cursor()
                try:
                    cur.execute("SELECT employee_id FROM users WHERE id = %s", [user_id])
                    employee_id_result = cur.fetchone()

                    if employee_id_result:
                        employee_id = employee_id_result[0]

                        cur.execute("DELETE FROM attendance WHERE employee_id = %s", [employee_id])
                        cur.execute("DELETE FROM employees WHERE id = %s", [employee_id])

                    cur.execute("DELETE FROM users WHERE id = %s", [user_id])
                    conn.commit()

                    flash("User and associated records deleted successfully", "success")
                except Exception as e:
                    flash(f"Error deleting user: {e}", "danger")
                finally:
                    cur.close()
                    conn.close()
                return redirect('/admin/user')
            else:
                flash("Unauthorized action", "danger")
                return redirect('/login')



#-------------------------------------------------------------------------------------------------

        # Updated route for managing shifts
        @self.app.route('/admin/shifts', methods=['GET', 'POST'])
        def manage_shifts():
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()  # Open connection to the database
                cur = conn.cursor()

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

                    conn.commit()  # Commit the changes to the database
                    cur.close()  # Close the cursor
                    conn.close()  # Close the database connection
                    return redirect('/admin/shifts')

                # Fetch shifts and group them by lab_name and days
                cur.execute("SELECT id, start_time, end_time, lab_name, days FROM shifts ORDER BY lab_name, days")
                shifts = cur.fetchall()

                # Fetch all unique lab names
                cur.execute("SELECT DISTINCT lab_name FROM shifts")
                lab_names = [row[0] for row in cur.fetchall()]
                cur.close()
                conn.close()  # Close the database connection after fetching data

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

        # Route to delete a shift
        @self.app.route('/admin/shifts/delete/<int:shift_id>', methods=['POST'])
        def delete_shift(shift_id):
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()  # Open the connection
                cur = conn.cursor()
                
                # Execute the deletion query
                cur.execute("DELETE FROM shifts WHERE id = %s", [shift_id])
                conn.commit()  # Commit the deletion

                cur.close()  # Close the cursor
                conn.close()  # Close the connection
                
                flash("Shift deleted successfully", "success")
                return redirect('/admin/shifts')
            else:
                flash("Unauthorized action", "danger")
                return redirect('/login')

#---------------------------------------------------------------------------------------------------

        # Route para sa Admin Attendance Report
        @self.app.route('/admin/attendance', methods=['GET'])
        def attendance_report():
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()  # Establish connection
                cur = conn.cursor()

                # Fetch user data for the top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Fetch all departments for the department filter
                cur.execute("SELECT id, name FROM departments")
                departments = cur.fetchall()

                department = request.args.get('department')  # Get selected department filter

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

                # Execute the attendance query
                cur.execute(query, params)
                attendance_records = cur.fetchall()

                cur.close()  # Close the cursor
                conn.close()  # Close the connection

                return render_template('/admin/attendance.html', 
                                    departments=departments, 
                                    attendance_records=attendance_records, 
                                    user_data=user_data)
            else:
                return redirect('/login')

        # Route to update attendance record
        @self.app.route('/admin/attendance/update', methods=['POST'])
        def update_attendance():
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()  # Establish connection
                cur = conn.cursor()

                attendance_id = request.form['attendance_id']
                check_in = request.form['check_in']
                check_out = request.form['check_out']
                status_in = request.form['status_in']
                status_out = request.form['status_out']

                # Update the attendance record in the database
                query = """
                    UPDATE attendance
                    SET check_in = %s, check_out = %s, status_in = %s, status_out = %s
                    WHERE id = %s
                """
                cur.execute(query, (check_in, check_out, status_in, status_out, attendance_id))
                conn.commit()  # Commit the changes

                cur.close()  # Close the cursor
                conn.close()  # Close the connection

                flash('Attendance record updated successfully!', 'success')
                return redirect('/admin/attendance')
            else:
                return redirect('/login')
            

        # Route to delete an attendance record
        @self.app.route('/admin/attendance/delete/<int:attendance_id>', methods=['POST'])
        def delete_attendance(attendance_id):
            if 'username' in session and session['role'] == 'admin':
                conn = self.ears_db()  # Establish connection
                cur = conn.cursor()

                # Execute delete query
                query = "DELETE FROM attendance WHERE id = %s"
                cur.execute(query, [attendance_id])
                conn.commit()  # Commit the changes

                cur.close()  # Close the cursor
                conn.close()  # Close the connection

                flash('Attendance record deleted successfully!', 'success')
                return redirect('/admin/attendance')
            else:
                return redirect('/login')
            

        # Route to calculate total hours rendered by an employee
        @self.app.route('/admin/attendance/calculate', methods=['POST'])
        def calculate_hours():
            if 'username' in session and session['role'] == 'admin':
                employee_name = request.form.get('employee_name')

                # Split the employee name into first name and last name
                first_name, last_name = employee_name.split()

                conn = self.ears_db()  # Establish connection
                cur = conn.cursor()

                # Get the employee ID based on the first and last name
                cur.execute("SELECT id FROM employees WHERE first_name = %s AND last_name = %s", (first_name, last_name))
                employee_id = cur.fetchone()

                if employee_id:
                    employee_id = employee_id[0]

                    # Calculate total hours for this employee
                    cur.execute("""
                        SELECT TIMEDIFF(check_out, check_in) as duty_hours
                        FROM attendance
                        WHERE employee_id = %s
                    """, [employee_id])
                    hours_data = cur.fetchall()

                    total_hours = timedelta()  # Initialize total hours
                    for row in hours_data:
                        duty_hours = row[0]
                        if duty_hours:
                            h, m, s = map(int, str(duty_hours).split(':'))
                            total_hours += timedelta(hours=h, minutes=m, seconds=s)

                    cur.close()  # Close the cursor
                    conn.close()  # Close the connection

                    # Return the total hours as a JSON response
                    return jsonify({'total_hours': str(total_hours)})
                else:
                    return jsonify({'error': 'Employee not found'}), 404
            else:
                return jsonify({'error': 'Unauthorized access'}), 403



#--------------------------------------------------------------------------------------------------------

        from datetime import datetime, time

        @self.app.route('/employee/attendance', methods=['GET', 'POST'])
        def employee_attendance():
            conn = self.ears_db()
            cur = conn.cursor()

            # Fetch employee data
            cur.execute("""
                SELECT first_name, last_name, profile_picture
                FROM employees
                WHERE id = %s
            """, [session.get('employee_id')])
            user_data = cur.fetchone()

            if not user_data:
                return jsonify({"success": False, "message": "User data not found. Please contact the administrator."}), 404

            # Fetch employee attendance status
            cur.execute("""
                SELECT check_in, check_out, status_in, status_out, DATE(date) 
                FROM attendance 
                WHERE employee_id = %s AND DATE(date) = CURDATE()
            """, [session['employee_id']])
            attendance_record = cur.fetchone()

            already_checked_in = False
            already_checked_out = False

            if attendance_record:
                check_in_time, check_out_time, status_in, status_out, record_date = attendance_record
                if check_in_time and not check_out_time:
                    already_checked_in = True
                elif check_in_time and check_out_time:
                    already_checked_out = True

            # Fetch employee's shift times for status calculation
            cur.execute("""
                SELECT start_time, end_time
                FROM shifts
                WHERE id = (SELECT shift FROM employees WHERE id = %s)
            """, [session['employee_id']])
            shift_data = cur.fetchone()

            if not shift_data:
                return jsonify({"success": False, "message": "Shift data not found for the employee."}), 404

            # Handle timedelta conversion to time
            try:
                shift_start_timedelta, shift_end_timedelta = shift_data

                if isinstance(shift_start_timedelta, time):
                    shift_start_time = shift_start_timedelta
                else:
                    # If it's a timedelta, extract the time component (hours, minutes)
                    shift_start_time = (datetime.min + shift_start_timedelta).time()

                if isinstance(shift_end_timedelta, time):
                    shift_end_time = shift_end_timedelta
                else:
                    # If it's a timedelta, extract the time component (hours, minutes)
                    shift_end_time = (datetime.min + shift_end_timedelta).time()

            except Exception as e:
                return jsonify({"success": False, "message": f"Error converting shift times: {e}"}), 500

            # Ensure the shift times are of type time
            today = datetime.now().date()  # Get today's date
            shift_start_time = datetime.combine(today, shift_start_time)  # Combine date with shift start time
            shift_end_time = datetime.combine(today, shift_end_time)  # Combine date with shift end time

            if request.method == 'POST':
                action = request.form['action']

                # Get the current datetime
                current_time = datetime.now()

                if action == 'time_in':
                    if already_checked_out:
                        return jsonify({"success": False, "message": "You have already checked in and out today."})
                    elif already_checked_in:
                        return jsonify({"success": False, "message": "You are already checked in."})
                    else:
                        # Calculate the status for check-in (On Time / Late)
                        if current_time <= shift_start_time:
                            status_in = "On Time"
                        else:
                            status_in = "Late"

                        # Insert the attendance record with check-in and status_in
                        cur.execute("""
                            INSERT INTO attendance (employee_id, check_in, date, status_in) 
                            VALUES (%s, NOW(), NOW(), %s)
                        """, [session['employee_id'], status_in])
                        conn.commit()
                        return jsonify({"success": True, "message": "Checked in successfully.", "next_action": "time_out"})

                elif action == 'time_out':
                    if not already_checked_in:
                        return jsonify({"success": False, "message": "You haven't checked in yet!"})
                    else:
                        # Calculate the status for check-out (Overtime / Early Out / On Time)
                        if current_time > shift_end_time:
                            status_out = "Overtime"
                        elif current_time < shift_end_time:
                            status_out = "Early Out"
                        else:
                            status_out = "On Time"

                        # Update the attendance record with check-out and status_out
                        cur.execute("""
                            UPDATE attendance SET check_out = NOW(), status_out = %s 
                            WHERE employee_id = %s AND DATE(date) = CURDATE()
                        """, [status_out, session['employee_id']])
                        conn.commit()
                        return jsonify({"success": True, "message": "Checked out successfully.", "next_action": "time_in"})

            cur.close()
            conn.close()

            # Render the page for GET request
            if request.method == 'GET':
                return render_template(
                    'employee/attendance.html',
                    already_checked_in=already_checked_in,
                    already_checked_out=already_checked_out,
                    user_profile_picture=user_data[2] if user_data[2] else 'default_profile.png',
                    user_data=user_data  # Pass user_data to the template
                )
            
    
#-----------------------------------------------------------------------------------------------------------



        # Route for employee profile
        @self.app.route('/employee/profile', methods=['GET', 'POST'])
        def employee_profile():
            if 'username' in session and session['role'] == 'employee':
                conn = self.ears_db()  # Open database connection
                cur = conn.cursor()

                # Fetch user details for the top bar
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Fetch employee ID using session data
                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    return redirect('/login')

                employee_id = result[0]

                # Fetch employee details from the database, including shift details, lab, and day
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

                cur.close()
                conn.close()

                # Check if employee data is found to avoid errors
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
                    flash('Employee data not found.', 'danger')
                    return redirect('/login')
            else:
                return redirect('/login')
            
            
        
#---------------------------------------------------------------------------------

        @self.app.route('/employee/history', methods=['GET'])
        def employee_history():
            if 'username' in session and session['role'] == 'employee':
                conn = self.ears_db()  # Open the database connection
                cur = conn.cursor()

                # Fetch user details for the navbar or elsewhere
                cur.execute("""
                    SELECT first_name, last_name, profile_picture
                    FROM employees
                    WHERE id = (SELECT employee_id FROM users WHERE username = %s)
                """, [session['username']])
                user_data = cur.fetchone()

                # Fetch employee ID based on the logged-in user's username
                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    cur.close()
                    conn.close()
                    return redirect('/login')

                employee_id = result[0]

                # Retrieve the attendance history for the employee with formatted check-in and check-out times, including statuses
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
                conn.close()

                # Returning the employee's attendance history page with the records and user data
                return render_template('employee/history.html', attendance_records=attendance_records, user_data=user_data)
            else:
                return redirect('/login')
            
            
#------------------------------------------------------------------------------------------------------------------------------
            
            
    # Function para paandaron ang Flask application
    def run(self):
        self.app.run(debug=True)

# Main function para mag-instantiate sang EmployeeAttendance class kag i-run ang Flask app
if __name__ == "__main__":
    x = EmployeeAttendance(__name__)
    x.run()




