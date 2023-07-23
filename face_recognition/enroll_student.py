from flask import Flask, render_template, request
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

# Create a route for the index page
@app.route('/')
def index():
    return render_template('enroll_student_details.html')

# Create a route to handle the form submission
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
        return "Failed to capture a frame from the camera"

    # Capture an image from the webcam
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # Draw rectangles around detected faces
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

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

if __name__ == '__main__':
    app.run()
