import os
import pickle
import numpy as np
import cv2
import face_recognition
import cvzone
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage
from datetime import datetime
import time
from google.cloud import bigquery

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://automaticattendancesystem-default-rtdb.firebaseio.com/",
    'storageBucket': "automaticattendancesystem.appspot.com"
})

bucket = storage.bucket()

# Your BigQuery project ID
project_id = 'automaticattendancesystem'

# Your BigQuery dataset ID and table ID
dataset_id = 'report'
table_id = 'attendance_register'

#Open camera Frame
cap = cv2.VideoCapture(0) 
cap.set(3, 640)
cap.set(4, 480)


imgBackground = cv2.imread('Resources/background.jpg')

# Importing the mode images into a list
folderModePath = 'Resources/Modes'
modePathList = os.listdir(folderModePath)
imgModeList = []
for path in modePathList:
    imgModeList.append(cv2.imread(os.path.join(folderModePath, path)))
# print(len(imgModeList))

# Load the encoding file
print("Loading Encode File ...")
file = open('EncodeFile.p', 'rb')
encodeListKnownWithIds = pickle.load(file)
file.close()
encodeListKnown, studentIds = encodeListKnownWithIds
# print(studentIds)
print("Encode File Loaded")

modeType = 0
counter = 0
id = -1
imgStudent = []

while True:
    success, img = cap.read()

    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

    faceCurFrame = face_recognition.face_locations(imgS)
    encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

    imgBackground[162:162 + 480, 55:55 + 640] = img
    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

    if faceCurFrame:
        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
            # print("matches", matches)
            # print("faceDis", faceDis)

            matchIndex = np.argmin(faceDis)
            # print("Match Index", matchIndex)

            if matches[matchIndex]:
                # print("Known Face Detected")
                # print(studentIds[matchIndex])
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)
                id = studentIds[matchIndex]
                print("detected student id", id)

#inserting to BQ  ###################################################
                studentInfo = db.reference(f'Students/{id}').get()

                cred = credentials.Certificate("bigQuery_Service_Account.json")

                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'bigQuery_Service_Account.json'

                bucket = storage.bucket()

                # Your BigQuery project ID
                project_id = 'automaticattendancesystem'

                # Your BigQuery dataset ID and table ID
                dataset_id = 'report'
                table_id = 'report1'

                # studentInfo = db.reference("Students/100859999").get()


                current_time = datetime.now()
                current_date = datetime.now().date()  # Get the current date


                data = {
                                    'Time': current_time.strftime("%H:%M:%S"),
                                    'Program': studentInfo["major"],
                                    'Student_Name': studentInfo["name"],
                                    'Attendance_Date': str(current_date) ,
                                    'Attendance':'Present',
                                    'Course':"2004",
                                    'studentid': studentInfo["studentid"]           
                                              }

                # Initialize the BigQuery client
                client = bigquery.Client(project=project_id)

                # Get the dataset reference
                dataset_ref = client.dataset(dataset_id)

                # Get the table reference
                table_ref = dataset_ref.table(table_id)

                # Check if the record already exists in BigQuery for the given date and subject
                query = f"""
                    SELECT 1
                    FROM `{project_id}.{dataset_id}.{table_id}`
                    WHERE studentid = {data['studentid']}
                    AND Attendance_Date = "{datetime.now().date()}"
                    AND Program = "{data['Program']}"
                """
                query_job = client.query(query)
                result = query_job.result()
                print(result.total_rows)

                if result.total_rows > 0:
                    # If the record already exists, skip insertion
                    print("Record for the student ID and subject already exists for today. Skipping insertion.")
                else:
                    # If the record does not exist, insert the data into the table
                    # Insert the data into the table
                    errors = client.insert_rows_json(table_ref, [data])

                    if errors == []:
                        print("Data successfully inserted into BigQuery table.")
                    else:
                        print("Errors encountered while inserting data into BigQuery table:", errors)

#inserting to BQ  ###################################################


                if counter == 0:
                    cvzone.putTextRect(imgBackground, "Loading", (275, 400))
                    cv2.imshow("Face Attendance", imgBackground)
                    cv2.waitKey(1)
                    counter = 1
                    modeType = 1
                

        if counter != 0:

            if counter == 1:
                # Get the Data
                studentInfo = db.reference(f'Students/{id}').get()
                print(studentInfo)
                # Get the Image from the storage
                blob = bucket.get_blob(f'Images/{id}.png')
                array = np.frombuffer(blob.download_as_string(), np.uint8)
                imgStudent = cv2.imdecode(array, cv2.COLOR_BGRA2BGR)
                imgStudent = cv2.resize(imgStudent, (216, 216))  # Resize imgStudent
                # Update data of attendance
                datetimeObject = datetime.strptime(studentInfo['last_attendance_time'],
                                                   "%Y-%m-%d %H:%M:%S")
                secondsElapsed = (datetime.now() - datetimeObject).total_seconds()
                print(secondsElapsed)
                if secondsElapsed > 30:
                    ref = db.reference(f'Students/{id}')
                    studentInfo['total_attendance'] += 1
                    ref.child('total_attendance').set(studentInfo['total_attendance'])
                    ref.child('last_attendance_time').set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    modeType = 3
                    counter = 0
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

            if modeType != 3:

                if 10 < counter < 20:
                    modeType = 2

                imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                if counter <= 10:
                    cv2.putText(imgBackground, str(studentInfo['total_attendance']), (861, 125),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo['major']), (1006, 550),
                                cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(id), (1006, 493),
                                cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo['standing']), (910, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, str(studentInfo['year']), (1025, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, str(studentInfo['starting_year']), (1125, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)

                    (w, h), _ = cv2.getTextSize(studentInfo['name'], cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                    offset = (414 - w) // 2
                    cv2.putText(imgBackground, str(studentInfo['name']), (808 + offset, 445),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)

                    imgBackground[175:175 + imgStudent.shape[0], 909:909 + imgStudent.shape[1]] = imgStudent

                counter += 1

                if counter >= 20:
                    counter = 0
                    modeType = 0
                    studentInfo = []
                    imgStudent = []
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
    else:
        modeType = 0
        counter = 0
    # cv2.imshow("Webcam", img)
    cv2.imshow("Face Attendance", imgBackground)
    cv2.waitKey(1)

    if counter >0 :
    # Wait for 10 seconds
        time.sleep(5)
        counter = 0
        modeType = 0
        studentInfo = []
        imgStudent = []
        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
