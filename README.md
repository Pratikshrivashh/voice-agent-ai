# Flask Voice AI Clinic Appointment Backend

A Flask backend for a Vapi Voice AI clinic appointment booking assistant. The API lets a voice agent check availability, book, cancel, reschedule, answer FAQs, and suggest alternate slots. Appointment data is stored in `appointments.json`, which makes the project simple to run locally and easy to deploy for demos.

## Features

- 7 JSON API endpoints built for Vapi voice tools
- Appointment availability checks for Monday to Friday
- Booking with name, phone number, day, time, and reason
- Cancellation by registered phone number
- Rescheduling with automatic slot release and rebooking
- FAQ endpoint for clinic information
- Alternate slot suggestions
- Input validation for day, clinic time, and 10-digit phone numbers
- Render deployment support with `Procfile` and `gunicorn`

## Project Structure

```text
voice-agent/
|-- app.py
|-- appointments.json
|-- requirements.txt
|-- Procfile
|-- .gitignore
`-- README.md
```

## Installation And Setup

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/voice-agent.git
cd voice-agent
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Activate it on macOS or Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run Locally

Start the Flask server:

```bash
python app.py
```

Local base URL:

```text
http://localhost:5000
```

## API Documentation

All endpoints return JSON. For local testing, replace `http://localhost:5000` with your deployed Render URL after deployment.

### 1. Health Check

`GET /health`

Checks whether the backend is running.

```bash
curl http://localhost:5000/health
```

Example response:

```json
{
  "status": "ok"
}
```

### 2. Check Availability

`POST /check-availability`

Checks available slots for a day. If `time` is included, it checks whether that exact slot is available.

```bash
curl -X POST http://localhost:5000/check-availability ^
  -H "Content-Type: application/json" ^
  -d "{\"day\":\"Monday\",\"time\":\"10:00 AM\"}"
```

Request body:

```json
{
  "day": "Monday",
  "time": "10:00 AM"
}
```

### 3. Book Appointment

`POST /book-appointment`

Books an appointment and removes that slot from available slots.

```bash
curl -X POST http://localhost:5000/book-appointment ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Rahul Sharma\",\"phone\":\"9876543210\",\"day\":\"Monday\",\"time\":\"10:00 AM\",\"reason\":\"General consultation\"}"
```

Request body:

```json
{
  "name": "Rahul Sharma",
  "phone": "9876543210",
  "day": "Monday",
  "time": "10:00 AM",
  "reason": "General consultation"
}
```

### 4. Cancel Appointment

`POST /cancel-appointment`

Cancels active appointments for a phone number and returns the slot to availability.

```bash
curl -X POST http://localhost:5000/cancel-appointment ^
  -H "Content-Type: application/json" ^
  -d "{\"phone\":\"9876543210\"}"
```

Request body:

```json
{
  "phone": "9876543210"
}
```

### 5. Reschedule Appointment

`POST /reschedule-appointment`

Moves an active appointment to a new available day and time.

```bash
curl -X POST http://localhost:5000/reschedule-appointment ^
  -H "Content-Type: application/json" ^
  -d "{\"phone\":\"9876543210\",\"new_day\":\"Tuesday\",\"new_time\":\"11:00 AM\"}"
```

Request body:

```json
{
  "phone": "9876543210",
  "new_day": "Tuesday",
  "new_time": "11:00 AM"
}
```

The endpoint also accepts `day` and `time` instead of `new_day` and `new_time`.

### 6. Get FAQ

`GET /get-faq`

Returns clinic FAQ answers for the voice assistant.

```bash
curl http://localhost:5000/get-faq
```

### 7. Get Alternate Slots

`POST /get-alternate-slots`

Suggests available slots on other weekdays when the preferred day is not suitable.

```bash
curl -X POST http://localhost:5000/get-alternate-slots ^
  -H "Content-Type: application/json" ^
  -d "{\"day\":\"Monday\"}"
```

Request body:

```json
{
  "day": "Monday"
}
```

## Validation Rules

- `day` must be Monday, Tuesday, Wednesday, Thursday, or Friday.
- `time` must be between 9:00 AM and 6:00 PM.
- `phone` must be exactly 10 digits.
- Invalid requests return JSON errors with proper HTTP status codes.

## Vapi Integration Guide

Create Vapi tools that call these backend URLs:

```text
GET  https://YOUR-RENDER-APP.onrender.com/health
POST https://YOUR-RENDER-APP.onrender.com/check-availability
POST https://YOUR-RENDER-APP.onrender.com/book-appointment
POST https://YOUR-RENDER-APP.onrender.com/cancel-appointment
POST https://YOUR-RENDER-APP.onrender.com/reschedule-appointment
GET  https://YOUR-RENDER-APP.onrender.com/get-faq
POST https://YOUR-RENDER-APP.onrender.com/get-alternate-slots
```

Recommended Vapi tool parameters:

- `check-availability`: `day`, optional `time`
- `book-appointment`: `name`, `phone`, `day`, `time`, optional `reason`
- `cancel-appointment`: `phone`
- `reschedule-appointment`: `phone`, `new_day`, `new_time`
- `get-alternate-slots`: `day`

The backend supports normal JSON request bodies and Vapi-style `arguments` payloads.

## Render Deployment

Push your code to GitHub:

```bash
git init
git add .
git commit -m "Prepare Flask voice appointment backend for deployment"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/voice-agent.git
git push -u origin main
```

Deploy on Render:

1. Open Render and create a new Web Service.
2. Connect your GitHub repository.
3. Select the Python runtime.
4. Set the build command:

```bash
pip install -r requirements.txt
```

5. Set the start command:

```bash
gunicorn app:app
```

The included `Procfile` also contains:

```text
web: gunicorn app:app
```

After deployment, test:

```bash
curl https://YOUR-RENDER-APP.onrender.com/health
```

## Production Notes

`appointments.json` is good for demos and simple prototypes. For real clinic traffic, move appointment data to PostgreSQL, MySQL, Firebase, or another managed database because Render's filesystem is not designed as a permanent production database.

## Next Steps

- Add a real database
- Add doctor-specific schedules
- Add admin authentication
- Send SMS or WhatsApp confirmations
- Add logs and monitoring
- Add automated tests for every endpoint
