import cv2
import face_recognition
import pickle
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import  storage
import random
import string


cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://automaticattendancesystem-default-rtdb.firebaseio.com/",
    'storageBucket': "automaticattendancesystem.appspot.com"
})





# Function to generate a random 5-digit number
def generate_random_number():
    return ''.join(random.choices(string.digits, k=5))

# Create a frame for previewing the image
cv2.namedWindow("Preview")
cv2.waitKey(1)

# Load the pre-trained face cascade classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Initialize variables for image capture
capture_image = False

while True:
    # Capture a new frame
    capture = cv2.VideoCapture(0)
    ret, frame = capture.read()
    capture.release()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # Draw rectangles around detected faces
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

    # Display the frame with face detection
    cv2.imshow("Preview", frame)
    key = cv2.waitKey(1) & 0xFF

    if len(faces) > 0 and not capture_image:
        # If a face is detected and capture_image is False, set capture_image to True
        capture_image = True

    if key == ord('0'):
        # Press '0' to capture an image or exit the frame
        if capture_image:
            # Generate a random file name
            random_number = generate_random_number()
            file_name = f'{random_number}.png'
            file_path = os.path.join('Images', file_name)

            # Save the captured image
            cv2.imwrite(file_path, frame)
            print("New image captured and saved successfully.")
            break
        else:
            break

    if key == ord('q'):
        # Press 'q' to quit
        break

# Close the preview frame
cv2.destroyAllWindows()


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


    # print(path)
    # print(os.path.splitext(path)[0])
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