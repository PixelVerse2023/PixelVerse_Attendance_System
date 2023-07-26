from flask import Flask, render_template, request, url_for, redirect
from google.cloud import bigquery
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import cv2
import os
import random
import face_recognition
import pickle
import string
import firebase_admin
from firebase_admin import credentials, db, storage
from datetime import datetime
import calendar
import time

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://automaticattendancesystem-default-rtdb.firebaseio.com/",
    'storageBucket': "automaticattendancesystem.appspot.com"
})


app = Flask(__name__)
app.config['SECRET_KEY'] = 'nyhn25622sihi896s'

login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, email):
        self.email = email

    def get_id(self):
        return str(self.email)


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Create a function to open the camera with retries


def open_camera_with_retries(camera_index=0, num_retries=5):
    for i in range(num_retries):
        capture = cv2.VideoCapture(camera_index)
        if capture.isOpened():
            return capture
        capture.release()
        time.sleep(1)

    # If the camera couldn't be opened even after retries, return Noneca
    return None


# Set up the folder to store captured images
image_folder = 'Images'
if not os.path.exists(image_folder):
    os.makedirs(image_folder)


def generate_random_number():
    return ''.join(random.choices(string.digits, k=5))


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Extract form data
        First_Name = request.form.get('FirstName')
        Last_Name = request.form.get('LastName')
        email = request.form.get('Email')
        hash_and_salted_password = generate_password_hash(
            request.form.get('Password'),
            method='pbkdf2:sha256',
            salt_length=8
        )
        password = hash_and_salted_password
        print(First_Name, Last_Name, email, password)

        # Create a BigQuery client
        client1 = bigquery.Client.from_service_account_json('bigQuery_Service_Account.json')

        # Define the BigQuery table and schema
        table_id = 'automaticattendancesystem.register.registered_users'

        # Prepare the row to insert
        row = {'First_Name': First_Name, 'Last_Name': Last_Name, 'email': email, 'password': password}
        print(row)
        # Insert the row into the BigQuery table
        table = client1.get_table(table_id)
        client1.insert_rows(table, [row])
        return render_template('login.html')


# Define a route for the homepage
@app.route('/index')
def index():

    # Pass the results to the HTML template
    return render_template('index.html')


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        client2 = bigquery.Client.from_service_account_json('bigQuery_Service_Account.json')

        # Fetching report data from BigQuery
        query = """
            SELECT email, password, User_Type
            FROM `automaticattendancesystem.register.registered_users`
            WHERE email = @email
        """

        # Define the query parameters
        query_params = [
            bigquery.ScalarQueryParameter("email", "STRING", email)
        ]

        # Set the query parameters
        job_config = bigquery.QueryJobConfig()
        job_config.query_parameters = query_params

        # Run the query
        query_job = client2.query(query, job_config=job_config)

        # Fetch the results
        results = query_job.result()
        for row in results:
            # Access a specific field by its column name
            retrieved_password = row['password']
            user_type = row['User_Type']
        if check_password_hash(retrieved_password, password):
            user = User(email)
            login_user(user)
            if user_type == 's':
                return redirect(url_for('studentIndex'))
            if user_type == 'a':
                return redirect(url_for('adminIndex'))
            else:
                return redirect(url_for('tables'))
        else:
            return render_template('login.html', login_status="Invalid login ID or password")
    return render_template('login.html')


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/tables')
def tables():
    return render_template('tables_old.html')

@app.route('/student_index')
def studentIndex():
    return render_template('student_index.html')


@app.route('/admin_index')
def adminIndex():
    return render_template('tables_old.html')


@app.route('/dashboard')
def dashboard():
    return render_template('student_dashboard.html')


@app.route('/faculty_dashboard')
def faculty_dashboard():
    return render_template('faculty_dashboard.html')


@app.route('/viewreport', methods=['GET', 'POST'])
def viewreport():
    if request.method == 'POST':
        # Retrieve form values
        fromDate = request.form.get('fromDate')
        toDate = request.form.get('toDate')
        courseSelect = request.form.get('courseSelect')
        searchStudentID = request.form.get('searchStudentID')

        print("from date", fromDate, "to date:", toDate, "selected  course:", courseSelect, "student ID",type(searchStudentID))


        client = bigquery.Client.from_service_account_json('bigQuery_Service_Account.json')

        if(searchStudentID != "0" and courseSelect !="All"):
         # Fetching report data from BigQuery
            query = """
            SELECT *
            FROM `automaticattendancesystem.report.report1`
            WHERE StudentID = @searchStudentID AND Attendance_Date BETWEEN @fromDate AND @toDate AND Course = @courseSelect
            """
            query_params = [
                bigquery.ScalarQueryParameter("searchStudentID", "INT64", int(searchStudentID)),
                bigquery.ScalarQueryParameter("fromDate", "STRING", fromDate),
                bigquery.ScalarQueryParameter("toDate", "STRING", toDate),
                bigquery.ScalarQueryParameter("courseSelect", "INT64", int(courseSelect))
            ]
        elif (courseSelect == "All"):
            # Fetching report data from BigQuery
            if(searchStudentID!="0"):
                query = """
                        SELECT *
                        FROM `automaticattendancesystem.report.report1`
                        WHERE StudentID = @searchStudentID AND Attendance_Date BETWEEN @fromDate AND @toDate
                        """
                query_params = [
                    bigquery.ScalarQueryParameter("searchStudentID", "INT64", int(searchStudentID)),
                    bigquery.ScalarQueryParameter("fromDate", "STRING", fromDate),
                    bigquery.ScalarQueryParameter("toDate", "STRING", toDate),
                ]
            else:
                query = """
                        SELECT *
                        FROM `automaticattendancesystem.report.report1`
                        WHERE Attendance_Date BETWEEN @fromDate AND @toDate
                        """
                query_params = [
                    bigquery.ScalarQueryParameter("searchStudentID", "INT64", int(searchStudentID)),
                    bigquery.ScalarQueryParameter("fromDate", "STRING", fromDate),
                    bigquery.ScalarQueryParameter("toDate", "STRING", toDate),
                ]

        else:
            query = """
                        SELECT *
                        FROM `automaticattendancesystem.report.report1`
                        WHERE Attendance_Date BETWEEN @fromDate AND @toDate AND Course = @courseSelect
                        """
            query_params = [
                bigquery.ScalarQueryParameter("fromDate", "STRING", fromDate),
                bigquery.ScalarQueryParameter("toDate", "STRING", toDate),
                bigquery.ScalarQueryParameter("courseSelect", "INT64", int(courseSelect))
            ]
        # Define the query parameters
        query_params = [
            bigquery.ScalarQueryParameter("searchStudentID", "INT64", int(searchStudentID)),
            bigquery.ScalarQueryParameter("fromDate", "STRING", fromDate),
            bigquery.ScalarQueryParameter("toDate", "STRING", toDate),
            bigquery.ScalarQueryParameter("courseSelect", "STRING", courseSelect)
        ]

        # Set the query parameters
        job_config = bigquery.QueryJobConfig()
        job_config.query_parameters = query_params

        # Run the query
        query_job = client.query(query, job_config=job_config)

        # Retrieve the results
        results = query_job.result()

        # Pass the result back to the template
        return render_template('tables_old.html', data=results)


# Create a route to handle the student facerec enrollment submission
@app.route('/submit', methods=['POST'])
def submit():
    # Get the student details from the form
    name = request.form['name']
    roll_number = request.form['roll_number']
    program_name = request.form['program_name']

    capture = open_camera_with_retries()
    if capture is None:
        return "Image is being uploaded to the cloud, pls refresh the page if not automatically redirected"

    ret, frame = capture.read()
    if not ret:
        # Failed to read a frame, handle the error
        capture.release()
        return "Image is being uploaded to the cloud, pls refresh the page if not automatically redirected"

    # Capture an image from the webcam
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # Draw rectangles around detected faces
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    image_path = os.path.join(image_folder, f'{roll_number}.png')
    cv2.imwrite(image_path, frame)
    print(image_path)
    capture.release()

    # Importing student images
    folderPath = 'Images'
    pathList = os.listdir(folderPath)
    print(pathList)
    imgList = []
    studentIds = []
    for path in pathList:
        imgList.append(cv2.imread(os.path.join(folderPath, path)))
        studentIds.append(os.path.splitext(path)[0])

        fileName = f'{folderPath}/{path}'
        bucket = storage.bucket()
        blob = bucket.blob(fileName)
        blob.upload_from_filename(fileName)

        expiration_time = calendar.timegm(time.gmtime()) + (15 * 60)
        url = blob.generate_signed_url(expiration=expiration_time)

    print(studentIds)

    def findEncodings(imagesList):
        encodeList = []
        for img in imagesList:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encode = face_recognition.face_encodings(img)[0]
            encodeList.append(encode)
        return encodeList

    print("Encoding Started ...")
    encodeListKnown = findEncodings(imgList)
    encodeListKnownWithIds = [encodeListKnown, studentIds]
    print("Encoding Complete")

    file = open("EncodeFile.p", 'wb')
    pickle.dump(encodeListKnownWithIds, file)
    file.close()
    print("File Saved")

    ref = db.reference('Students')
    current_timestamp = datetime.timestamp(datetime.now())
    formatted_time = datetime.fromtimestamp(current_timestamp).strftime('%Y-%m-%d %H:%M:%S')

    student = {
        roll_number:
            {
                "name": name,
                "major": "AIDI",
                "starting_year": 2023,
                "total_attendance": 12,
                "standing": "B",
                "year": 1,
                "last_attendance_time": formatted_time,
                "studentid": roll_number
            }
    }

    for key, value in student.items():
        ref.child(key).set(value)

    student = {
        'name': name,
        'student_id': roll_number,
        'photo_url': url
    }
    print("url is \n\n", url)

    # Process the student details or store them in a database
    # You can add your desired logic here

    # Replace this with the actual student information fetched from your database

    return render_template('student_success.html', student=student, url=url)


@app.route('/forgot-password')
def forgot_password():

    # Pass the results to the HTML template
    return render_template('forgot-password.html')


@app.route('/register_user')
def register_user():

    # Pass the results to the HTML template
    return render_template('register.html')


@app.route('/modify')
def modifyRecords():
    return render_template('modify.html')


@app.route('/fetchrecord', methods=['GET', 'POST'])
def fetchModifyRecord():
    if request.method == 'POST':
        # Retrieve form values
        modifyDate = request.form.get('modifyDate')
        modifyCourse = request.form.get('modifyCourse')
        modifyStuID = request.form.get('modifyStuID')

        client3 = bigquery.Client.from_service_account_json('bigQuery_Service_Account.json')

        # Fetching report data from BigQuery
        query = """
            SELECT *
            FROM `automaticattendancesystem.report.report1`
            WHERE StudentID = @modifyStuID AND Attendance_Date = @modifyDate AND Course = @modifyCourse
        """

        # Define the query parameters
        query_params = [
            bigquery.ScalarQueryParameter("modifyStuID", "INT64", int(modifyStuID)),
            bigquery.ScalarQueryParameter("modifyDate", "STRING", modifyDate),
            bigquery.ScalarQueryParameter("modifyCourse", "INT64", int(modifyCourse))
        ]

        # Set the query parameters
        job_config = bigquery.QueryJobConfig()
        job_config.query_parameters = query_params

        # Run the query
        query_job = client3.query(query, job_config=job_config)

        # Retrieve the results
        results = query_job.result()

        selected_record = {'StudentID': 0, 'Course': 2002, 'Student_Name': '', 'Program': '', 'Attendance_Date': '', 'Attendance': '', 'Time': ''}

        # Process the results
        for row in results:
            selected_record['StudentID']= row.StudentID
            selected_record['Course'] = row.Course
            selected_record['Student_Name'] = row.Student_Name
            selected_record['Time'] = row.Time
            selected_record['Attendance'] = row.Attendance
            selected_record['Attendance_Date'] = row.Attendance_Date
            selected_record['Program'] = row.Program
            selected_record['Attendance'] = row.Attendance
        # Pass the result back to the template
        return render_template('modify.html', result=results, row=selected_record)


@app.route('/modifyattendanceDB', methods=['GET', 'POST'])
def modifyattendanceDB():
    if request.method == 'POST':
        # Retrieve form values
        mDate = request.form.get('mDate')
        mCourse = request.form.get('mCourse')
        mID = request.form.get('mID')
        mAttendance = request.form.get('mAttendance')

        client4 = bigquery.Client.from_service_account_json('bigQuery_Service_Account.json')

        # modify the student record in Bigquery Table
        query = """
            UPDATE `automaticattendancesystem.report.report1`
            SET Attendance = @mAttendance
            WHERE StudentID = @mID AND Attendance_Date = @mDate AND Course = @mCourse
        """

        # Define the query parameters
        query_params = [
            bigquery.ScalarQueryParameter("mAttendance", "STRING", mAttendance),
            bigquery.ScalarQueryParameter("mID", "INT64", int(mID)),
            bigquery.ScalarQueryParameter("mDate", "STRING", mDate),
            bigquery.ScalarQueryParameter("mCourse", "INT64", int(mCourse))
        ]

        # Set the query parameters
        job_config = bigquery.QueryJobConfig()
        job_config.query_parameters = query_params

        # Run the query
        query_job = client4.query(query, job_config=job_config)

        msg ='Student Attendance Record Modified'

        return render_template('modify.html', DB_message= msg)


@app.route('/modify.html')
def cards():
    return render_template('modify.html')


@app.route('/enroll_student_details')
def enroll_student_details():
    logout_user()
    return render_template('enroll_student_details.html')


@app.route('/logout')
def logout():
    logout_user()
    return 'Logged out'


@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized', 401


if __name__ == '__main__':
    app.run(debug=True)