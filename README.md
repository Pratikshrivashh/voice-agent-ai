# Sumitra Hospital Voice AI Appointment Backend

This project is a small but practical backend for a hospital appointment booking voice assistant. The idea is simple: a caller can speak to a Vapi assistant, ask for a doctor or department, check OPD availability, and book, cancel, or reschedule an appointment.

The backend is built with Flask and uses Firebase Firestore for storing doctors and appointment slots. Instead of using random demo data, the seed data is based on the publicly available Sumitra Hospital OPD timetable used for this assignment.

Current deployed backend:

```text
https://voice-agent-ai-3omf.onrender.com
```

## Features

- Stores doctors and appointment slots in Firebase Firestore
- Seeds real OPD schedule data from the Sumitra Hospital timetable
- Works with Vapi tool calls using simple JSON input and output
- Checks doctor availability by day and specialty
- Books appointments only after checking for double-booking conflicts
- Cancels appointments using phone number or appointment ID
- Reschedules appointments only when the new slot is actually free
- Suggests alternate slots when the requested slot is unavailable
- Protects the seed endpoint with `SEED_SECRET_KEY`
- Falls back to `appointments.json` locally if Firebase credentials are not configured
- Runs on Render with `gunicorn`

## Firestore Structure

### Collection: `doctors`

Each document represents one doctor schedule entry.

```json
{
  "name": "Dr. Ayushi Agarwal",
  "specialty": "Cardiology",
  "days": ["Monday", "Wednesday", "Friday"],
  "startTime": "5:00 PM",
  "endTime": "6:00 PM",
  "availabilityType": "Scheduled",
  "source": "Sumitra Hospital OPD timetable"
}
```

Doctors with "On Prior Appointment" availability are stored in `doctors`, but regular bookable slots are not generated for them.

### Collection: `appointments`

Each document represents one bookable OPD slot.

```json
{
  "doctor": "Dr. Ayushi Agarwal",
  "specialty": "Cardiology",
  "day": "Monday",
  "time": "5:00 PM",
  "patient_name": "",
  "phone": "",
  "reason": "",
  "status": "Available",
  "booked_at": "",
  "cancelled_at": "",
  "rescheduled_at": "",
  "source": "Sumitra Hospital OPD timetable"
}
```

When a slot is booked, the same appointment document is updated to `status: "Booked"` with patient details.

## OPD Timetable Source

The doctor schedule used in this project is based on the Sumitra Hospital OPD timetable that was provided for the assignment and is treated as publicly available hospital schedule information. No private patient data is used in the seed data.

To make the data source clear inside Firestore, every seeded doctor and appointment slot stores this label:

```text
Sumitra Hospital OPD timetable
```

Doctors included in the seed data:

- Dr. Rajesh Goel, Nephrology, Sunday, 11:00 AM to 12:00 PM
- Dr. Somya Agarwal, Gastroenterology, Monday to Friday, 10:00 AM to 12:00 PM
- Dr. Ayushi Agarwal, Cardiology, Monday, Wednesday, Friday, 5:00 PM to 6:00 PM
- Dr. Vikas Bansal, Urology, Monday, Wednesday, Friday, 5:00 PM to 6:00 PM
- Dr. Rekha Mittal, Paediatric Neurology, Monday, Friday, 3:00 PM to 4:00 PM
- Dr. Shazia Zaidi, Dermatology & Venereology, Tuesday, Thursday, Saturday, 12:00 PM to 1:00 PM
- Dr. Neha Saini, Dental, Monday to Saturday, 10:00 AM to 6:00 PM
- Dr. Jyoti Bhatia, Physiotherapy, Monday to Saturday, 10:00 AM to 5:00 PM
- Dr. Nitin Kumar Rai, Neurology, Monday to Saturday, 9:00 AM to 10:00 AM
- Dr. Alok Sharma, Ophthalmology, Monday, Wednesday, Friday, Saturday, 10:00 AM to 12:00 PM
- Dr. Alok Sharma, Ophthalmology, Tuesday, Thursday, 2:00 PM to 4:00 PM
- Dr. Kalpana Upamanyu, Psychology, Monday, Wednesday, Friday, 12:00 PM to 2:00 PM
- Dr. A. K. Arora, Respiratory Medicine, On Prior Appointment
- Dr. Naman Utreja, Oncology, On Prior Appointment
- Dr. Ashwani Mishra, Paediatrics Surgery, Monday, Thursday, 6:00 PM to 7:00 PM
- Dr. Hemant Kumar, Neuro Surgery, On Prior Appointment

## Environment Variables

Required for production:

```text
FIREBASE_CREDENTIALS_JSON
SEED_SECRET_KEY
```

Optional:

```text
PORT
FLASK_DEBUG
LOG_LEVEL
```

### Where To Put Firebase Credentials

Do not commit the Firebase service account JSON file to GitHub.

For Render, open your Web Service and go to:

```text
Environment -> Add Environment Variable
```

Add:

```text
Key: FIREBASE_CREDENTIALS_JSON
Value: paste the full Firebase service account JSON content
```

Also add:

```text
Key: SEED_SECRET_KEY
Value: choose a long private random string
```

For local PowerShell testing:

```powershell
$env:FIREBASE_CREDENTIALS_JSON = Get-Content -Raw "C:\Users\Lenovo\Downloads\voice-ai-agent-81fca-firebase-adminsdk-fbsvc-4a6468aa9a.json"
$env:SEED_SECRET_KEY = "your-local-seed-secret"
```

## Installation

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run Locally

```bash
python app.py
```

Local base URL:

```text
http://localhost:5000
```

If `FIREBASE_CREDENTIALS_JSON` is missing, the app still runs by using `appointments.json` as a local fallback. This is useful while testing the Flask routes before connecting Firebase.

## API Endpoints

All endpoints return JSON and include a `success` boolean.

### GET `/health`

```bash
curl http://localhost:5000/health
```

### POST `/seed-data`

Seeds the real Sumitra Hospital OPD timetable into Firestore.

```bash
curl -X POST http://localhost:5000/seed-data ^
  -H "Content-Type: application/json" ^
  -H "X-Seed-Key: your-local-seed-secret" ^
  -d "{}"
```

### POST `/check-availability`

Specialty is optional.

```bash
curl -X POST http://localhost:5000/check-availability ^
  -H "Content-Type: application/json" ^
  -d "{\"day\":\"Monday\",\"specialty\":\"Cardiology\"}"
```

Request:

```json
{
  "day": "Monday",
  "specialty": "Cardiology"
}
```

### POST `/book-appointment`

```bash
curl -X POST http://localhost:5000/book-appointment ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Pratik Raj\",\"phone\":\"9876543210\",\"doctor\":\"Dr. Ayushi Agarwal\",\"specialty\":\"Cardiology\",\"day\":\"Monday\",\"time\":\"5:00 PM\",\"reason\":\"General consultation\"}"
```

Request:

```json
{
  "name": "Pratik Raj",
  "phone": "9876543210",
  "doctor": "Dr. Ayushi Agarwal",
  "specialty": "Cardiology",
  "day": "Monday",
  "time": "5:00 PM",
  "reason": "General consultation"
}
```

If the same doctor/day/time is already booked, the endpoint returns `409`.

### POST `/cancel-appointment`

Cancel by appointment ID:

```bash
curl -X POST http://localhost:5000/cancel-appointment ^
  -H "Content-Type: application/json" ^
  -d "{\"appointment_id\":\"slot_dr_ayushi_agarwal_cardiology_monday_5_00_pm\"}"
```

Cancel by phone:

```bash
curl -X POST http://localhost:5000/cancel-appointment ^
  -H "Content-Type: application/json" ^
  -d "{\"phone\":\"9876543210\"}"
```

If one phone has multiple active appointments, the API returns `409` and asks for `appointment_id`.

### POST `/reschedule-appointment`

```bash
curl -X POST http://localhost:5000/reschedule-appointment ^
  -H "Content-Type: application/json" ^
  -d "{\"phone\":\"9876543210\",\"new_doctor\":\"Dr. Ayushi Agarwal\",\"new_specialty\":\"Cardiology\",\"new_day\":\"Wednesday\",\"new_time\":\"5:00 PM\"}"
```

Request:

```json
{
  "phone": "9876543210",
  "new_doctor": "Dr. Ayushi Agarwal",
  "new_specialty": "Cardiology",
  "new_day": "Wednesday",
  "new_time": "5:00 PM"
}
```

### POST `/get-alternate-slots`

```bash
curl -X POST http://localhost:5000/get-alternate-slots ^
  -H "Content-Type: application/json" ^
  -d "{\"doctor\":\"Dr. Ayushi Agarwal\",\"specialty\":\"Cardiology\",\"day\":\"Monday\",\"time\":\"5:00 PM\"}"
```

### GET `/get-faq`

```bash
curl http://localhost:5000/get-faq
```

## Vapi Integration Guide

In Vapi, create tools that call these backend URLs. The assistant should collect the required details from the caller, then pass them to the matching endpoint.

```text
GET  https://voice-agent-ai-3omf.onrender.com/health
POST https://voice-agent-ai-3omf.onrender.com/check-availability
POST https://voice-agent-ai-3omf.onrender.com/book-appointment
POST https://voice-agent-ai-3omf.onrender.com/cancel-appointment
POST https://voice-agent-ai-3omf.onrender.com/reschedule-appointment
POST https://voice-agent-ai-3omf.onrender.com/get-alternate-slots
GET  https://voice-agent-ai-3omf.onrender.com/get-faq
```

Recommended Vapi tool parameters:

- `check-availability`: `day`, optional `specialty`
- `book-appointment`: `name`, `phone`, `doctor`, `specialty`, `day`, `time`, optional `reason`
- `cancel-appointment`: `appointment_id` or `phone`
- `reschedule-appointment`: `appointment_id` or `phone`, `new_doctor`, `new_specialty`, `new_day`, `new_time`
- `get-alternate-slots`: optional `doctor`, optional `specialty`, optional `day`, optional `time`

The backend supports plain JSON request bodies and common Vapi `arguments` payloads, so it can work both from curl/Postman and from the voice assistant.

## Render Deployment

1. Push this project to GitHub.
2. Open Render and create or update the Web Service.
3. Set the build command:

```bash
pip install -r requirements.txt
```

4. Set the start command:

```bash
gunicorn app:app
```

5. Add environment variables:

```text
FIREBASE_CREDENTIALS_JSON=<paste full service account JSON>
SEED_SECRET_KEY=<your private seed key>
```

6. Deploy.
7. Run `/seed-data` once after deployment to insert the Sumitra Hospital OPD timetable into Firestore.

Render seed command example:

```bash
curl -X POST https://voice-agent-ai-3omf.onrender.com/seed-data \
  -H "Content-Type: application/json" \
  -H "X-Seed-Key: YOUR_SEED_SECRET_KEY" \
  -d "{}"
```

## Testing Checklist

```bash
python -m py_compile app.py
```

Health:

```bash
curl http://localhost:5000/health
```

Seed:

```bash
curl -X POST http://localhost:5000/seed-data -H "X-Seed-Key: your-local-seed-secret" -H "Content-Type: application/json" -d "{}"
```

Check Monday Cardiology availability:

```bash
curl -X POST http://localhost:5000/check-availability -H "Content-Type: application/json" -d "{\"day\":\"Monday\",\"specialty\":\"Cardiology\"}"
```

Book Dr. Ayushi Agarwal:

```bash
curl -X POST http://localhost:5000/book-appointment -H "Content-Type: application/json" -d "{\"name\":\"Pratik Raj\",\"phone\":\"9876543210\",\"doctor\":\"Dr. Ayushi Agarwal\",\"specialty\":\"Cardiology\",\"day\":\"Monday\",\"time\":\"5:00 PM\",\"reason\":\"General consultation\"}"
```

Run the same booking command again. It should return:

```text
409 Conflict
```

## Limitations

- The timetable is weekday-based, so it does not yet handle calendar dates, holidays, or doctor leave.
- Slot generation uses one-hour blocks from the OPD timing range.
- Doctors marked "On Prior Appointment" are saved in Firestore, but automatic slots are not created for them.
- The timetable data is used as publicly available schedule information for this assignment/demo. It should be verified with the hospital before real-world use.
- `appointments.json` is only for local fallback. Firestore is the intended production database.
- Before using this in a real hospital workflow, add authentication, admin controls, audit logs, date-wise scheduling, and stronger data privacy controls.
