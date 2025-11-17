import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import boto3
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# AWS
s3 = boto3.client('s3')
ec2 = boto3.resource('ec2')
ses = boto3.client('ses')

# RDS
conn = pymysql.connect(
    host=os.getenv('RDS_HOST'),
    user=os.getenv('RDS_USER'),
    password=os.getenv('RDS_PASS'),
    database=os.getenv('RDS_DB')
)
cur = conn.cursor()

root = tk.Tk()
root.title("EduCloud — VM Bridge → Full AWS")
root.geometry("1800x1000")
root.configure(bg="#0a1e2e")

# HEADER — YOUR EXACT COVER DESIGN
header = tk.Frame(root, bg="#0a1e2e")
header.pack(pady=(30, 50))
tk.Label(header, text="VM Bridge", font=("Arial", 90, "bold"), fg="#00ff99", bg="#0a1e2e").pack()
tk.Label(header, text="→ EduCloud", font=("Arial", 90, "bold"), fg="white", bg="#0a1e2e").pack()
tk.Label(header, text="02/07/2025 → 01/12/2025", font=("Arial", 28), fg="#00ff99", bg="#0a1e2e").pack(pady=10)
tk.Label(header, text="Ahmed Al-Asadi & Aristide Katagaruka — B1CLC", font=("Arial", 20), fg="#88ddff", bg="#0a1e2e").pack()

# Main layout
content = tk.Frame(root, bg="#0a1e2e")
content.pack(expand=True, fill="both", padx=50)

# LEFT: Classes
left = tk.Frame(content, bg="#0a1e2e")
left.pack(side="left", padx=30)

tk.Label(left, text="CLASSES", font=("Arial", 18, "bold"), fg="#00ff99", bg="#0a1e2e").pack(anchor="w")
class_box = tk.Frame(left, bg="#1e3a4e", relief="flat", bd=2)
class_box.pack(pady=10, fill="x")
tk.Label(class_box, text="Class Name:", fg="white", bg="#1e3a4e").pack(side="left", padx=10, pady=10)
class_entry = tk.Entry(class_box, width=25, font=("Arial", 12))
class_entry.pack(side="left", padx=10, pady=10)

def add_class():
    name = class_entry.get().strip()
    if name:
        cur.execute("INSERT INTO classes (name) VALUES (%s)", (name,))
        conn.commit()
        update_classes()
        class_entry.delete(0, tk.END)

tk.Button(class_box, text="Add", command=add_class, bg="#00ff99", fg="black", font=("Arial", 10, "bold")).pack(side="left", padx=10, pady=10)

class_tree = ttk.Treeview(left, columns=("ID", "Name"), show="headings", height=6)
class_tree.heading("ID", text="ID")
class_tree.heading("Name", text="Class")
class_tree.pack(pady=10)
def update_classes():
    for i in class_tree.get_children(): class_tree.delete(i)
    cur.execute("SELECT id, name FROM classes")
    for r in cur.fetchall(): class_tree.insert("", "end", values=r)
update_classes()

# CENTER: Students + Assignments
center = tk.Frame(content, bg="#0a1e2e")
center.pack(side="left", padx=50)

# Students CRUD
tk.Label(center, text="STUDENTS", font=("Arial", 18, "bold"), fg="#00ff99", bg="#0a1e2e").pack(anchor="w")
student_frame = tk.Frame(center, bg="#1e3a4e", bd=2, relief="flat")
student_frame.pack(pady=10, fill="x")
tk.Label(student_frame, text="Name:", fg="white", bg="#1e3a4e").pack(side="left", padx=10)
name_entry = tk.Entry(student_frame, width=20)
name_entry.pack(side="left", padx=5)
tk.Label(student_frame, text="Email:", fg="white", bg="#1e3a4e").pack(side="left", padx=10)
email_entry = tk.Entry(student_frame, width=25)
email_entry.pack(side="left", padx=5)

cur.execute("SELECT id, name FROM classes")
classes = cur.fetchall()
class_map = {name: id for id, name in classes}
class_var = tk.StringVar(value=list(class_map.keys())[0] if class_map else "")
class_menu = ttk.Combobox(student_frame, textvariable=class_var, values=list(class_map.keys()), state="readonly", width=15)
class_menu.pack(side="left", padx=10)

def add_student():
    name = name_entry.get().strip()
    email = email_entry.get().strip()
    class_name = class_var.get()
    if name and email and class_name:
        class_id = class_map[class_name]
        cur.execute("INSERT INTO students (name, email, class_id) VALUES (%s, %s, %s)", (name, email, class_id))
        conn.commit()
        update_assignments()
        name_entry.delete(0, tk.END)
        email_entry.delete(0, tk.END)

tk.Button(student_frame, text="Add Student", command=add_student, bg="#00ff99", fg="black", font=("Arial", 10, "bold")).pack(side="left", padx=10)

# Assignments Table
tk.Label(center, text="ASSIGNMENTS (EC2 Instances)", font=("Arial", 18, "bold"), fg="#00ff99", bg="#0a1e2e").pack(anchor="w", pady=(30,10))
assign_tree = ttk.Treeview(center, columns=("Student", "Email", "Class", "IP", "Sent"), show="headings", height=15)
assign_tree.heading("Student", text="Student")
assign_tree.heading("Email", text="Email")
assign_tree.heading("Class", text="Class")
assign_tree.heading("IP", text="Public IP")
assign_tree.heading("Sent", text="Email Sent")
assign_tree.column("Student", width=150)
assign_tree.column("Email", width=200)
assign_tree.column("Class", width=100)
assign_tree.column("IP", width=130)
assign_tree.column("Sent", width=80)
assign_tree.pack()

def update_assignments():
    for i in assign_tree.get_children(): assign_tree.delete(i)
    cur.execute("""
        SELECT s.name, s.email, c.name, a.public_ip, a.sent 
        FROM students s 
        JOIN classes c ON s.class_id = c.id 
        LEFT JOIN assignments a ON a.student_id = s.id
    """)
    for row in cur.fetchall():
        sent = "Yes" if row[4] else "No"
        assign_tree.insert("", "end", values=(row[0], row[1], row[2], row[3] or "Pending", sent))
update_assignments()

# RIGHT: MASSIVE UPLOAD BUTTON
right = tk.Frame(content, bg="#0a1e2e")
right.pack(side="right", padx=50)

tk.Label(right, text="UPLOAD\nstudents.csv", font=("Arial", 32, "bold"), fg="#00ff99", bg="#0a1e2e").pack(pady=100)
def upload_csv():
    file = filedialog.askopenfilename(title="Select students.csv")
    if file:
        s3.upload_file(file, os.getenv('S3_BUCKET'), "uploads/" + os.path.basename(file))
        messagebox.showinfo("EDUCLOUD", "CSV uploaded!\nFull AWS automation started:\n→ EC2 Launch\n→ IP → RDS\n→ SES Email")
        # Refresh in 10 seconds
        root.after(10000, update_assignments)

tk.Button(right, text="LAUNCH ALL VMS", command=upload_csv,
          font=("Arial", 36, "bold"), bg="#00ff99", fg="black", height=4, width=15).pack()

# Footer
tk.Label(root, text="EduCloud — From Proxmox VM Bridge to Full AWS Cloud — Ahmed & Aristide 2025",
         font=("Arial", 16), fg="#88ddff", bg="#00bfa5").pack(side="bottom", fill="x", pady=20, ipady=15)

root.mainloop()