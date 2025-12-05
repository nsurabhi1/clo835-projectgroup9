from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3

app = Flask(__name__)

# --- Config ---
DBHOST = os.environ.get("DBHOST") or "mysql"
DBUSER = os.environ.get("DBUSER") or "root"
DBPWD = os.environ.get("DBPWD") or "password"
DATABASE = os.environ.get("DATABASE") or "employees"
DBPORT = int(os.environ.get("DBPORT") or 3306)

# Customization Variables
APP_TITLE = os.environ.get("APP_TITLE") or "Final Project - Group 9"
S3_BUCKET = os.environ.get("S3_BUCKET")
S3_IMAGE_KEY = os.environ.get("S3_IMAGE_KEY")
AWS_REGION = "us-east-1"

# --- S3 Logic ---
def download_background_image():
    if S3_BUCKET and S3_IMAGE_KEY:
        print(f"Downloading background from: s3://{S3_BUCKET}/{S3_IMAGE_KEY}")
        try:
            s3 = boto3.client('s3', region_name=AWS_REGION)
            if not os.path.exists('static'):
                os.makedirs('static')
            # Save as 'bg.jpg' locally regardless of S3 name
            s3.download_file(S3_BUCKET, S3_IMAGE_KEY, 'static/bg.jpg')
            print("Download successful.")
        except Exception as e:
            print(f"S3 Error: {e}")
    else:
        print("S3_BUCKET or S3_IMAGE_KEY not set; skipping background download.")

# Run once at startup
download_background_image()

# --- DB Connection ---
db_conn = None
try:
    db_conn = connections.Connection(
        host=DBHOST,
        port=DBPORT,
        user=DBUSER,
        password=DBPWD,
        db=DATABASE
    )
    print("Database connection initiated.")
except Exception as e:
    print(f"Database connection failed: {e}")
    db_conn = None

# --- Routes ---
@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('addemp.html', title=APP_TITLE)

@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    primary_skill = request.form['primary_skill']
    location = request.form['location']
    full_name = ""

    if not db_conn:
        # DB connection never established
        print("ERROR: db_conn is None. Check DBHOST/DBUSER/DBPWD/DATABASE/DBPORT.")
        return render_template(
            'addempoutput.html',
            name="",
            title=APP_TITLE,
            error="Database connection is not available."
        )

    cursor = db_conn.cursor()
    try:
        insert_sql = """
            INSERT INTO employee (emp_id, first_name, last_name, primary_skill, location)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_sql, (emp_id, first_name, last_name, primary_skill, location))
        db_conn.commit()
        full_name = f"{first_name} {last_name}"
        print(f"Inserted employee {emp_id} - {full_name}")
    except Exception as e:
        db_conn.rollback()
        print("ERROR inserting employee:", e)
        return render_template(
            'addempoutput.html',
            name="",
            title=APP_TITLE,
            error=f"Error adding employee: {e}"
        )
    finally:
        cursor.close()

    return render_template('addempoutput.html', name=full_name, title=APP_TITLE)


@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    return render_template("getemp.html", title=APP_TITLE)

@app.route("/fetchdata", methods=['GET', 'POST'])
def FetchData():
    emp_id = request.form['emp_id']
    output = {}

    if db_conn:
        cursor = db_conn.cursor()
        try:
            select_sql = "SELECT * FROM employee WHERE emp_id=%s"
            cursor.execute(select_sql, (emp_id,))

            result = cursor.fetchone()

            if result:
                output["id"] = result[0]
                output["fname"] = result[1]
                output["lname"] = result[2]
                output["skill"] = result[3]   # template expects {{ skill }}
                output["location"] = result[4]

        except Exception as e:
            print("ERROR:", e)
        finally:
            cursor.close()
    else:
        print("ERROR: db_conn is None in FetchData")

    return render_template("getempoutput.html", **output, title=APP_TITLE)


# --- IMPORTANT: keep server running ---
if __name__ == "__main__":
    # In Docker/K8s this will run and keep the container alive
    app.run(host="0.0.0.0", port=81)
