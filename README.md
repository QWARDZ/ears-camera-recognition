venv\Scripts\activate
python -m venv venv
pip install -r requirements.txt
python app.py
pip freeze > requirements.txt























Unused py


        @self.app.route('/employee/profile/upload', methods=['POST'])
        def upload_profile_picture():
            if 'username' in session and session['role'] == 'employee':
                conn = self.get_db_connection()  # Open database connection
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
        
