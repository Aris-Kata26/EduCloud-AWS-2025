import pymysql
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)

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

try:
    with conn.cursor() as cur:
        cur.execute("CREATE DATABASE IF NOT EXISTS educloud")
        cur.execute("USE educloud")
        for statement in [s.strip() for s in schema_sql.split(';') if s.strip()]:
            cur.execute(statement)
        conn.commit()
    logging.info("EDUCLOUD DATABASE SCHEMA LOADED SUCCESSFULLY WITH PYMYSQL")
    print("Schema loaded and database is ready!")
except Exception as e:
    print(f"Error loading schema: {e}")
finally:
    conn.close()
