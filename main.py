from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials 
from pydantic import BaseModel, field_validator
import bcrypt
import sqlite3
import jwt
import datetime
import os
app = FastAPI()

security = HTTPBearer()

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "my_super_secret_techfest_key")

def get_db_connection():
    conn = sqlite3.connect("techfest.db")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def init_db() :
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        payment_status TEXT DEFAULT 'Pending',
        is_checked_in BOOLEAN DEFAULT FALSE
    )
    """)
    conn.commit()
    conn.close()
    
init_db()

class StudentRegistration(BaseModel):
    email : str
    password : str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def check_password_length(cls, value):
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return value

@app.get("/")
def home() :
    return {"message":"Welcome to the IEEE Tech Fest API"}

@app.post("/register")
def register_student(student_data : StudentRegistration):
    password_bytes = student_data.password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes,salt)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try :
        cursor.execute(
            "INSERT INTO students (email, password, role) VALUES (?, ?, ?)",
            (student_data.email, hashed_password.decode('utf-8'), "student")
        )
        conn.commit()
    except sqlite3.IntegrityError :
        conn.close()
        raise HTTPException(status_code = 400, detail = "Email is already registered")
    
    conn.close()
    
    print(f"Recieved registaration for {student_data.email}")
    return{"message":"Registration Successful", "user_email":student_data.email}

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try :
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired wristband!")
    
def verify_volunteer(credentials:HTTPAuthorizationCredentials=Depends(security)):
    user_email = verify_token(credentials)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM students WHERE email = ?",(user_email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or user[0] != "volunteer":
        raise HTTPException(status_code=403,detail="Access Denied, volunteers only!")
    return user_email
    
class UserLogin(BaseModel) :
    email : str
    password : str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower()
    
@app.post("/login")
def login_user(login_user : UserLogin) :
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT password FROM students where email = ?", (login_user.email,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result is None :
        raise HTTPException(status_code = 400, detail = "Invalid email or password")
    saved_hashed_password = result[0]
    
    typed_password_bytes = login_user.password.encode('utf-8')
    saved_hash_bytes = saved_hashed_password.encode('utf-8')
    
    if bcrypt.checkpw(typed_password_bytes,saved_hash_bytes):
        
        wristband_data = { 
                          "sub": login_user.email,
                          "exp" : datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }
        token = jwt.encode(wristband_data, SECRET_KEY, algorithm= "HS256")
        
        return {"message":"login successful!", "token":token}
    else :
        raise HTTPException(status_code=400, detail = "Invalid email or password")


@app.post("/pay")
def process_payment(user_email: str = Depends(verify_token)) :
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE students SET payment_status = 'Paid' WHERE email = ?", (user_email,))
    conn.commit()
    
    if cursor.rowcount == 0 :
        conn.close()
        raise HTTPException(status_code=404, detail = "Student not found. Please register first.")
    
    conn.close()
    return{"message":"Payment Successful!", "email":user_email, "payment_status":"Paid"}

@app.get("/ticket")
def get_ticket(user_email : str = Depends(verify_token)) :
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, email, role, payment_status, is_checked_in FROM students WHERE email = ?", (user_email,))
    student = cursor.fetchone()
    conn.close()
    
    if not student :
        raise HTTPException(status_code=404, detail="student not found.")
    
    return {
        "message":"Welcome to the VIP area",
        "ticket_details":{
            "id":student[0],
            "email":student[1],
            "role" : student[2],
            "payment_status" : student[3],
            "is_checked_in" : student[4]
        }
    }
    
@app.get("/registrations")
def view_all_registrations(volunteer_email: str= Depends(verify_volunteer)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id,email,role,payment_status,is_checked_in FROM students")
    all_users = cursor.fetchall()
    conn.close()
    return {"message":"Volunteer Access Granted", "data":all_users}

@app.post("/check-in/{student_id}")
def check_in_student(student_id:int,volunteer_email:str = Depends(verify_volunteer)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_checked_in FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    
    if student is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Student ID not found.")
    
    if student[0]:
        conn.close()
        return {"message": f"Student {student_id} was already checked in."}
    
    cursor.execute("UPDATE students SET is_checked_in = TRUE WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    return{"message":f"Student {student_id} has been successfully checked in!"}