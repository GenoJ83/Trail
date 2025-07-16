# Trail: Smart Attendance System

Trail is a smart attendance system that uses an ESP32 microcontroller and RFID (RC522) technology to log student presence in real time. When a user scans their RFID tag, the ESP32 sends the data wirelessly to a Flask-based server, which records the entry and updates a live web dashboard. The system includes visual alerts via a buzzer and LED, and future versions will integrate a fingerprint sensor for enhanced verification.

## Features
- Real-time attendance logging with RFID (RC522) and ESP32
- Flask server with REST API for attendance data
- **Firebase Firestore** for student and attendance records
- Live web dashboard for monitoring attendance
- Visual alerts (buzzer, LED) on ESP32 (hardware side)
- Future: Fingerprint sensor integration

## Setup Instructions
1. **Clone the repository**
2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up Firebase:**
   - Go to the Firebase Console, create a project, and enable Firestore.
   - Go to Project Settings > Service Accounts, click "Generate new private key", and download the JSON file.
   - Place the JSON file in the `Trail_App` directory as `firebase_key.json`.
4. **Run the Flask server:**
   ```bash
   python app.py
   ```
5. **Access the dashboard:**
   Open your browser to `http://localhost:5000`

## ESP32-to-Server Communication Protocol
- The ESP32 sends a POST request to the Flask server at `/api/attendance`.
- The request body should be JSON:
  ```json
  { "rfid": "RFID_TAG_VALUE" }
  ```
- The server responds with a JSON object indicating success or error.

## Firestore Structure
- **students** (collection)
  - [student_id] (document)
    - name: "Student Name"
    - rfid: "RFID_TAG"
- **attendance** (collection)
  - [attendance_id] (document)
    - student_id: [student_id]
    - timestamp: ISO string

## Future Plans
- Integrate fingerprint sensor for enhanced verification.
- Add admin features to manage students and view reports.

## Hardware (ESP32 Side)
- Reads RFID tags using RC522 module
- Sends HTTP POST to Flask server
- Activates buzzer/LED for feedback
- (Planned) Reads fingerprint sensor for dual authentication

## License
MIT 