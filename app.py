from flask import Flask, request, jsonify, render_template
import psycopg2
import boto3
import uuid
from config import Config

app = Flask(__name__)

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )

# AWS Clients
s3 = boto3.client('s3', region_name=Config.AWS_REGION)
sns = boto3.client('sns', region_name=Config.AWS_REGION)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/incidents", methods=["POST"])
def create_incident():
    title = request.form["title"]
    description = request.form["description"]
    severity = request.form["severity"]
    file = request.files.get("file")

    file_url = None

    # Upload to S3 if file exists
    if file:
        file_key = str(uuid.uuid4()) + "_" + file.filename
        s3.upload_fileobj(file, Config.S3_BUCKET, file_key)
        file_url = f"https://{Config.S3_BUCKET}.s3.amazonaws.com/{file_key}"

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO incidents (title, description, severity, file_url) VALUES (%s, %s, %s, %s)",
        (title, description, severity, file_url)
    )

    conn.commit()
    cur.close()
    conn.close()

    # Send SNS Notification
    if severity == "HIGH":
        sns.publish(
            TopicArn=Config.SNS_HIGH_ARN,
            Message=f"High Severity Incident: {title}",
            Subject="HIGH INCIDENT ALERT"
        )
    elif severity == "MEDIUM":
        sns.publish(
            TopicArn=Config.SNS_MEDIUM_ARN,
            Message=f"Medium Severity Incident: {title}",
            Subject="MEDIUM INCIDENT ALERT"
        )

    return jsonify({"message": "Incident created successfully"}), 201

@app.route("/incidents", methods=["GET"])
def get_incidents():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM incidents ORDER BY created_at DESC")
    incidents = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(incidents)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)