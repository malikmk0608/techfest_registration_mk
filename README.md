# Tech Fest Registration API

This is a backend for our college tech fest registration system. Students can register, login, pay, and get their ticket. Volunteers can see all registrations and check students in at the gate.

Built using Python + FastAPI, with SQLite as the database.

## How to run it

1. Clone this repo and go into the folder
```
git clone https://github.com/malikmk0608/techfest_registration_mk.git
cd techfest_registration_mk
```

2. Install the packages
```
pip install fastapi uvicorn bcrypt pyjwt
```

3. (Optional but better) Set a secret key before running, otherwise it uses a default one:
```
export JWT_SECRET_KEY=anything_you_want
```

4. Run the server
```
uvicorn main:app --reload
```

5. Go to `http://127.0.0.1:8000/docs` in your browser. This page lets you test all the endpoints without needing Postman.

## How to make a volunteer account

There's no signup option for volunteers, only students, so that random people can't make themselves a volunteer. To test volunteer features:

1. Register normally like a student
2. Run this small script (save it as make_volunteer.py, change the email to yours, then run it):
```python
import sqlite3
conn = sqlite3.connect("techfest.db")
cursor = conn.cursor()
cursor.execute("UPDATE students SET role = 'volunteer' WHERE email = 'your_email_here'")
conn.commit()
conn.close()
print("Account successfully promoted to volunteer!")
```

Now that account is a volunteer.

## Assumptions I made

- Payment isn't connected to any real payment gateway, /pay just marks the user as paid. This was just to show the flow.
- Emails are not case sensitive, so Test@gmail.com and test@gmail.com are treated as the same.
- Password needs to be at least 6 characters.
- No "undo" for check-in, if someone is checked in by mistake it has to be fixed manually in the db.

## API Endpoints

**GET /** - just checks if server is running

**POST /register** - body: { "email": "...", "password": "..." }

**POST /login** - body: { "email": "...", "password": "..." }, returns a token. Use this token for the endpoints below by adding header Authorization: Bearer <token>

**POST /pay** - needs login token, marks the logged in user as paid

**GET /ticket** - needs login token, shows your ticket details

**GET /registrations** - needs login token + volunteer role, shows all students

**POST /check-in/{student_id}** - needs login token + volunteer role, checks in that student by id

## Testing

There's a Postman collection file in this repo called techfest.postman_collection.json. Import it into Postman and run the requests in this order: register, then login (this saves the token automatically for the rest), then pay, ticket, and if it's a volunteer account, registrations and check-in.
