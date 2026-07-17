from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import datetime

# =======================
# FLASK APP SETTINGS
# =======================
app = Flask(__name__)
app.secret_key = "your_secret_key"

# =======================
# LOAD DATASETS
# =======================
try:
    df = pd.read_csv("data/WA_Fn-UseC_-HR-Employee-Attrition.csv", dtype={"EmployeeNumber": int})
    employee_data = df.to_dict(orient="records")
except Exception as e:
    print("Error loading HR CSV:", e)
    employee_data = []

# Attendance, leave, logs CSVs
def load_csv(file_name, default_cols, dtypes=None):
    try:
        return pd.read_csv(file_name, dtype=dtypes)
    except:
        return pd.DataFrame(columns=default_cols)

df_attendance = load_csv("data/attendance.csv", ["EmployeeNumber","Date","Status"], dtypes={"EmployeeNumber": int})
df_leave = load_csv("data/leave.csv", ["EmployeeNumber","Date","LeaveType","Status"], dtypes={"EmployeeNumber": int})
df_logs = load_csv("data/logs.csv", ["Time","User","Action"])

# =======================
# USERS DATABASE
# =======================
users = {
    "admin": {"password":"admin123","role":"hr"},
    "employee1": {"password":"emp123","role":"employee"},
    "employee2": {"password":"emp456","role":"employee"},
    "employee3": {"password":"emp789","role":"employee"},
    "employee4": {"password":"emp101","role":"employee"}
}

# =======================
# LOGIN
# =======================
@app.route("/", methods=["GET","POST"])
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        role = request.form.get("role")

        if username in users and users[username]["password"] == password and users[username]["role"] == role:
            session["user"] = username
            session["role"] = role

            # Employee Number and Name for employees
            if role == "employee":
                emp_number = request.form.get("emp_number")
                emp_name = request.form.get("emp_name").strip()
                if not emp_number or not emp_number.isdigit() or not emp_name:
                    return render_template("login.html", error="Please enter valid Employee Number and Name")
                session["emp_number"] = int(emp_number)
                session["emp_name"] = emp_name

            # Add log entry
            new_log = {
                "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "User": username,
                "Action": "Logged In"
            }
            global df_logs
            df_logs = pd.concat([df_logs, pd.DataFrame([new_log])], ignore_index=True)
            df_logs.to_csv("data/logs.csv", index=False)

            if role == "hr":
                return redirect(url_for("hr_dashboard"))
            elif role == "employee":
                return redirect(url_for("emp_dashboard"))

        else:
            return render_template("login.html", error="Invalid credentials or role mismatch")

    return render_template("login.html")

# =======================
# SIGNUP
# =======================
@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method=="POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        role = request.form.get("role")

        if username in users:
            return render_template("signup.html", error="User already exists!")

        users[username] = {"password": password, "role": role}
        return redirect(url_for("login"))

    return render_template("signup.html")

# =======================
# LOGOUT
# =======================
@app.route("/logout")
def logout():
    if "user" in session:
        new_log = {
            "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "User": session["user"],
            "Action": "Logged Out"
        }
        global df_logs
        df_logs = pd.concat([df_logs, pd.DataFrame([new_log])], ignore_index=True)
        df_logs.to_csv("data/logs.csv", index=False)

    session.pop("user", None)
    session.pop("role", None)
    session.pop("emp_number", None)
    session.pop("emp_name", None)
    return redirect(url_for("login"))

# =======================
# EMPLOYEE RECORD
# =======================
def get_employee_record():
    emp_number = session.get("emp_number")
    emp_name = session.get("emp_name")
    if not emp_number or not emp_name:
        return None

    emp_record = next((e for e in employee_data if int(e["EmployeeNumber"]) == emp_number), None)
    if emp_record:
        emp_record["EmployeeName"] = emp_name
        return emp_record
    return None

# =======================
# HR MODULE
# =======================
@app.route("/hr/dashboard")
def hr_dashboard():
    if "user" not in session or session.get("role") != "hr":
        return redirect(url_for("login"))

    total_employees = len(employee_data)
    attrition_count = df[df["Attrition"]=="Yes"].shape[0]
    attrition_rate = round((attrition_count/total_employees)*100,2)
    avg_salary = round(df["MonthlyIncome"].mean(),2)
    overtime_pct = round(len(df[df["OverTime"]=="Yes"])/total_employees*100,2)

    # --- Line Chart Data (simulate attendance trend or employee count over months) ---
    # For simplicity, we'll create monthly employee counts
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    # Simulated trend (example: number of employees active each month)
    emp_counts = [1400,1410,1420,1425,1430,1440,1450,1455,1460,1465,1470,1470]

    return render_template("hr/dashboard.html",
                           total_employees=total_employees,
                           attrition_count=attrition_count,
                           attrition_rate=attrition_rate,
                           avg_salary=avg_salary,
                           overtime_pct=overtime_pct,
                           months=months,
                           emp_counts=emp_counts)


@app.route("/hr/employee")
def hr_employee():
    if "user" not in session or session.get("role") != "hr":
        return redirect(url_for("login"))
    return render_template("hr/employee.html", employees=employee_data)

# In app.py, inside hr_attendance route:
@app.route("/hr/attendance")
def hr_attendance():
    if "user" not in session or session.get("role") != "hr":
        return redirect(url_for("login"))

    # For each employee, create a default attendance record
    merged_attendance = []
    for emp in employee_data:
        emp_id = emp["EmployeeNumber"]
        emp_name = emp.get("EmployeeName", f"Employee {emp_id}")
        
        # Example: create a default last 7 days attendance (all Present)
        # You can customize this or read from another source if needed
        for i in range(1, 8):
            date = (pd.Timestamp.now() - pd.Timedelta(days=i)).strftime("%Y-%m-%d")
            merged_attendance.append({
                "EmployeeNumber": emp_id,
                "Name": emp_name,
                "Date": date,
                "Status": "Present"   # default value
            })

    return render_template("hr/attendance.html", attendance=merged_attendance)



@app.route("/hr/logs")
def hr_logs():
    if "user" not in session or session.get("role") != "hr":
        return redirect(url_for("login"))

    logs = df_logs.to_dict(orient="records")
    return render_template("hr/logs.html", logs=logs)

@app.route("/hr/report")
def hr_report():
    if "user" not in session or session.get("role") != "hr":
        return redirect(url_for("login"))

    report_data = df[['EmployeeNumber','Department','JobRole','MonthlyIncome','Attrition']].to_dict(orient='records')
    return render_template("hr/report.html", report=report_data)

# =======================
# EMPLOYEE MODULE
# =======================
@app.route("/employee/dashboard")
def emp_dashboard():
    if "user" not in session or session.get("role") != "employee":
        return redirect(url_for("login"))
    emp_record = get_employee_record()
    if not emp_record:
        return "Employee record not found", 404
    return render_template("employee/dashboard.html", emp=emp_record)

@app.route("/employee/profile")
def emp_profile():
    if "user" not in session or session.get("role") != "employee":
        return redirect(url_for("login"))
    emp_record = get_employee_record()
    if not emp_record:
        return "Employee record not found", 404
    return render_template("employee/profile.html", profile=emp_record)

@app.route("/employee/attendance")
def emp_attendance():
    if "user" not in session or session.get("role") != "employee":
        return redirect(url_for("login"))
    emp_record = get_employee_record()
    attendance_data = df_attendance[df_attendance["EmployeeNumber"]==emp_record["EmployeeNumber"]].to_dict(orient="records")
    return render_template("employee/attendance.html", attendance=attendance_data)

@app.route("/employee/leave")
def emp_leave():
    if "user" not in session or session.get("role") != "employee":
        return redirect(url_for("login"))
    emp_record = get_employee_record()
    leave_data = df_leave[df_leave["EmployeeNumber"]==emp_record["EmployeeNumber"]].to_dict(orient="records")
    return render_template("employee/leave.html", leaves=leave_data)

@app.route("/employee/salary")
def emp_salary():
    if "user" not in session or session.get("role") != "employee":
        return redirect(url_for("login"))
    emp_record = get_employee_record()
    salary = {
        "basic": emp_record["MonthlyIncome"]*0.6,
        "hra": emp_record["MonthlyIncome"]*0.3,
        "pf": emp_record["MonthlyIncome"]*0.05,
        "net": emp_record["MonthlyIncome"]*0.85
    }
    return render_template("employee/salary.html", salary=salary)

# =======================
# RUN FLASK
# =======================
if __name__=="__main__":
    app.run(debug=True)
