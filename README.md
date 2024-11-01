venv\Scripts\activate
python -m venv venv
pip install -r requirements.txt
python app.py
pip freeze > requirements.txt























Unused py


        @self.app.route('/employee/profile/upload', methods=['POST'])
        def upload_profile_picture():
            if 'username' in session and session['role'] == 'employee':
                conn = self.ears_db()  # Open database connection
                cur = conn.cursor()

                # Fetch employee ID from the session data
                cur.execute("SELECT employee_id FROM users WHERE username = %s", [session['username']])
                result = cur.fetchone()

                if result is None:
                    flash("User not found.", "danger")
                    return redirect('/login')

                employee_id = result[0]

                # Check if the file is present in the request
                if 'profile_picture' not in request.files:
                    flash('No file part', 'danger')
                    return redirect(request.url)

                file = request.files['profile_picture']

                # Check if a file was selected
                if file.filename == '':
                    flash('No selected file', 'danger')
                    return redirect(request.url)

                # Check if the uploaded file is allowed and process it
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(self.app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)  # Save the file to the uploads directory

                    # Update employee profile picture in the database
                    cur.execute("""
                        UPDATE employees SET profile_picture = %s WHERE id = %s
                    """, (filename, employee_id))
                    conn.commit()

                    flash('Profile picture uploaded successfully!', 'success')
                    return redirect('/employee/profile')

                flash('Invalid file format. Allowed formats are png, jpg, jpeg, gif.', 'danger')
                return redirect('/employee/profile')

            return redirect('/login')


        def allowed_file(filename):
            ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
        


employe attedance.css 

/* General Styling */
body {
    font-family: Arial, sans-serif;
    background-color: #f4f7f9;
    margin: 0;
    padding: 0;
    color: #333;
}

/* Main container */
/* .main-container {
    max-width: 600px;
    margin: 100px auto;
    background-color: #ffffff;
    padding: 30px;
    border-radius: 10px;
    box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
    text-align: center;
} */

/* Header */
h1 {
    margin-bottom: 20px;
    font-size: 28px;
    color: #333;
    font-weight: bold;
}

/* Profile Picture Section */
.user-profile {
    margin-bottom: 20px;
}

.user-profile img.profile-pic {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    object-fit: cover;
    border: 3px solid #3498db;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* Message Section */
.message {
    font-size: 18px;
    color: #555;
    margin-bottom: 30px;
    padding: 15px;
    background-color: #eaf1f8;
    border-radius: 8px;
    border: 1px solid #3498db;
}

/* Camera Section */
#camera-section {
    margin-top: 20px;
    text-align: center;
}

#camera-section video {
    border-radius: 10px;
    box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
    margin-bottom: 15px;
}

#capture {
    background-color: #3498db;
    color: #fff;
    padding: 10px 20px;
    font-size: 16px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

#capture:hover {
    background-color: #2980b9;
}

/* Loader */
.loader {
    border: 5px solid #f3f3f3;
    border-radius: 50%;
    border-top: 5px solid #3498db;
    width: 40px;
    height: 40px;
    animation: spin 2s linear infinite;
    margin: 10px auto;
    display: none;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Attendance Form */
.attendance-button {
    background-color: #28a745;
    color: #fff;
    font-size: 18px;
    padding: 10px 30px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.3s ease, box-shadow 0.3s ease;
    margin-top: 20px;
}

.attendance-button:hover {
    background-color: #218838;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.attendance-button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
}

/* Thank You Message */
.thank-you-message {
    margin-top: 20px;
    font-size: 18px;
    color: #555;
    padding: 15px;
    background-color: #f9f9f9;
    border-radius: 8px;
    border: 1px solid #ddd;
}

/* Small Clock Styling */
.small-clock {
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: #48b7eb;
    color: #fff;
    padding: 10px 20px;
    border-radius: 8px;
    margin: 20px auto;
    max-width: 400px;
    box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.2);
}

.clock-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 0 8px;
}

.time-unit.small {
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 0.2px;
    text-shadow: 0px 1px 3px rgba(0, 0, 0, 0.2);
}

.label {
    font-size: 14px;
    text-transform: uppercase;
    color: #474747;
    margin-top: 5px;
}

.colon {
    font-size: 10px;
    font-weight: bold;
    padding: 0 5px;
    text-shadow: 0px 1px 3px rgba(0, 0, 0, 0.2);
}





---------------------------------------------------------------------