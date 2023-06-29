from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from google.cloud import bigquery
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from datetime import datetime


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

@app.route('/register', methods=["GET","POST"])
def register():
    if request.method == "POST":
        # Extract form data
        First_Name='Hello'
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
        row = {'First_Name': First_Name, 'Last_Name': Last_Name,'email': email, 'password': password}
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


@app.route('/login', methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        client2 = bigquery.Client.from_service_account_json('bigQuery_Service_Account.json')

        # Fetching report data from BigQuery
        query = """
            SELECT email, password
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
        if check_password_hash(retrieved_password, password):
            user = User(email)
            login_user(user)
            return redirect(url_for('tables'))
        else:
            return render_template('login.html', login_status="Invalid login ID or password")
    return render_template('login.html')


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/tables')
def tables():
    client = bigquery.Client.from_service_account_json('bigQuery_Service_Account.json')

    # Fetching report data from BigQuery
    query_report = """
        SELECT *
        FROM `automaticattendancesystem.report.report-table`
        """
    results = client.query(query_report)
    # Pass the results to the HTML template
    return render_template('tables_old.html', data=results)


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
    return render_template('cards.html')

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
            FROM `automaticattendancesystem.report.report-table`
            WHERE StudentID = @modifyStuID AND Attendance_Date = @modifyDate AND Course = @modifyCourse
        """

        # Define the query parameters
        query_params = [
            bigquery.ScalarQueryParameter("modifyStuID", "INT64", int(modifyStuID)),
            bigquery.ScalarQueryParameter("modifyDate", "STRING", modifyDate),
            bigquery.ScalarQueryParameter("modifyCourse", "STRING", modifyCourse)
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
        return render_template('cards.html', result=results, row=selected_record)

@app.route('/cards.html')
def cards():
    return render_template('cards.html')

@app.route('/logout')
def logout():
    logout_user()
    return 'Logged out'


@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized', 401


if __name__ == '__main__':
    app.run(debug=True)