import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv('RDS_HOST'),
    user=os.getenv('RDS_USER'),
    password=os.getenv('RDS_PASS'),
    database=os.getenv('RDS_DB')
)

schema_sql = """
CREATE TABLE IF NOT EXISTS classes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    class_id INT,
    FOREIGN KEY (class_id) REFERENCES classes(id)
);

CREATE TABLE IF NOT EXISTS assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    instance_id VARCHAR(50),
    public_ip VARCHAR(45),
    os_type ENUM('ubuntu','kali','windows'),
    sent BOOLEAN DEFAULT FALSE,
    sent_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id)
);
"""

with conn.cursor() as cur:
    for statement in [s.strip() for s in schema_sql.split(';') if s.strip()]:
        cur.execute(statement)
    conn.commit()

print("EDUCLOUD DATABASE SCHEMA LOADED SUCCESSFULLY WITH PYMYSQL")
conn.close()
