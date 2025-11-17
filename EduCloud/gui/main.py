import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import boto3
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# AWS + RDS
s3 = boto3.client('s3')
conn = pymysql.connect(
    host=os.getenv('RDS_HOST'),
    user=os.getenv('RDS_USER'),
    password=os.getenv('RDS_PASS'),
    database=os.getenv('RDS_DB')
)
cur = conn.cursor()

root = tk.Tk()
root.title("EduCloud — VM Bridge → Full AWS")
root.geometry("2000x1100")
root.configure(bg="#0c2e4a")

# HEADER — YOUR IMMORTAL VM BRIDGE COVER
header = tk.Frame(root, bg="#0c2e4a")
header.pack(pady=(30, 40))
tk.Label(header, text="VM Bridge", font=("Arial", 100, "bold"), fg="#00ff99", bg="#0c2e4a").pack()
tk.Label(header, text="→ EduCloud", font=("Arial", 100, "bold"), fg="white", bg="#0c2e4a").pack()
tk.Label(header, text="02/07/2025 → 01/12/2025", font=("Arial", 30), fg="#00ff99", bg="#0c2e4a").pack(pady=10)
tk.Label(header, text="Ahmed Al-Asadi & Aristide Katagaruka — B1CLC", font=("Arial", 22), fg="#88ddff", bg="#0c2e4a").pack()

content = tk.Frame(root, bg="#0c2e4a")
content.pack(expand=True, fill="both", padx=60)

# LEFT: CLASSES — FULL CRUD
left = tk.Frame(content, bg="#0c2e4a")
left.pack(side="left", padx=40)

tk.Label(left, text="CLASSES", font=("Arial", 20, "bold"), fg="#00ff99", bg="#0c2e4a").pack(anchor="w", pady=(0,10))
class_input = tk.Frame(left, bg="#0c2e4a")
class_input.pack(fill="x", pady=10)
tk.Label(class_input, text="Class Name:", fg="white", bg="#0c2e4a").pack(side="left")
class_entry = tk.Entry(class_input, width=30, font=("Arial", 12))
class_entry.pack(side="left", padx=10)
tk.Button(class_input, text="Add Class", command=lambda: add_class(), bg="#00ff99", fg="black", font=("Arial", 12, "bold")).pack(side="left", padx=5)

class_tree = ttk.Treeview(left, columns=("ID", "Name"), show="headings", height=10)
class_tree.heading("ID", text="ID")
class_tree.heading("Name", text="Class Name")
class_tree.column("ID", width=60)
class_tree.column("Name", width=250)
class_tree.pack(pady=10)

def update_classes():
    for i in class_tree.get_children(): class_tree.delete(i)
    cur.execute("SELECT id, name FROM classes ORDER BY name")
    for row in cur.fetchall():
        class_tree.insert("", "end", values=row, tags=(row[0],))
update_classes()

def add_class():
    name = class_entry.get().strip()
    if name:
        cur.execute("INSERT INTO classes (name) VALUES (%s)", (name,))
        conn.commit()
        update_classes()
        class_entry.delete(0, tk.END)

def edit_class():
    sel = class_tree.selection()
    if sel:
        item = class_tree.item(sel[0])
        new_name = simpledialog.askstring("Edit Class", "New name:", initialvalue=item['values'][1])
        if new_name and new_name != item['values'][1]:
            cur.execute("UPDATE classes SET name = %s WHERE id = %s", (new_name, item['values'][0]))
            conn.commit()
            update_classes()

def delete_class():
    sel = class_tree.selection()
    if sel and messagebox.askyesno("Delete", "Delete this class and all students?"):
        cur.execute("DELETE FROM classes WHERE id = %s", (class_tree.item(sel[0])['values'][0],))
        conn.commit()
        update_classes()

tk.Button(left, text="Edit Selected", command=edit_class, bg="#FFC107", fg="black").pack(side="left", padx=5)
tk.Button(left, text="Delete Selected", command=delete_class, bg="#f44336", fg="white").pack(side="left", padx=5)

# CENTER: STUDENTS — FULL CRUD WITH CLASS FK
center = tk.Frame(content, bg="#0c2e4a")
center.pack(side="left", padx=50)

tk.Label(center, font=("Arial", 20, "bold"), fg="#00ff99", bg="#0c2e4a", text="STUDENTS").pack(anchor="w", pady=(0,10))

# Add Student
student_input = tk.Frame(center, bg="#0c2e4a")
student_input.pack(fill="x", pady=10)
tk.Label(student_input, text="Name:", fg="white", bg="#0c2e4a").pack(side="left")
name_entry = tk.Entry(student_input, width=20)
name_entry.pack(side="left", padx=5)
tk.Label(student_input, text="Email:", fg="white", bg="#0c2e4a").pack(side="left", padx=10)
email_entry = tk.Entry(student_input, width=30)
email_entry.pack(side="left", padx=5)

# Class dropdown
cur.execute("SELECT name FROM classes")
class_list = [r[0] for r in cur.fetchall()]
class_var = tk.StringVar(value=class_list[0] if class_list else "")
class_menu = ttk.Combobox(student_input, textvariable=class_var, values=class_list, state="readonly", width=20)
class_menu.pack(side="left", padx=10)

def add_student():
    name = name_entry.get().strip()
    email = email_entry.get().strip().lower()
    cls = class_var.get()
    if name and email and cls:
        cur.execute("SELECT id FROM classes WHERE name = %s", (cls,))
        class_id = cur.fetchone()[0]
        cur.execute("INSERT INTO students (name, email, class_id) VALUES (%s, %s, %s)", (name, email, class_id))
        conn.commit()
        name_entry.delete(0, tk.END)
        email_entry.delete(0, tk.END)
        update_students()
        update_assignments()

tk.Button(student_input, text="Add Student", command=add_student, bg="#00ff99", fg="black", font=("Arial", 12, "bold")).pack(side="left", padx=10)

# Students Table
student_tree = ttk.Treeview(center, columns=("ID", "Name", "Email", "Class"), show="headings", height=12)
student_tree.heading("ID", text="ID")
student_tree.heading("Name", text="Name")
student_tree.heading("Email", text="Email")
student_tree.heading("Class", text="Class")
student_tree.column("ID", width=50)
student_tree.column("Name", width=180)
student_tree.column("Email", width=250)
student_tree.column("Class", width=150)
student_tree.pack(pady=10)

def update_students():
    for i in student_tree.get_children(): student_tree.delete(i)
    cur.execute("SELECT s.id, s.name, s.email, c.name FROM students s JOIN classes c ON s.class_id = c.id ORDER BY s.name")
    for row in cur.fetchall():
        student_tree.insert("", "end", values=row)

update_students()

def edit_student():
    sel = student_tree.selection()
    if sel:
        item = student_tree.item(sel[0])
        new_name = simpledialog.askstring("Edit Student", "New name:", initialvalue=item['values'][1])
        new_email = simpledialog.askstring("Edit Student", "New email:", initialvalue=item['values'][2])
        if (new_name or new_email):
            cur.execute("UPDATE students SET name = %s, email = %s WHERE id = %s",
                        (new_name or item['values'][1], new_email or item['values'][2], item['values'][0]))
            conn.commit()
            update_students()
            update_assignments()

def delete_student():
    sel = student_tree.selection()
    if sel and messagebox.askyesno("Delete", "Delete this student?"):
        cur.execute("DELETE FROM students WHERE id = %s", (student_tree.item(sel[0])['values'][0],))
        conn.commit()
        update_students()
        update_assignments()

tk.Button(center, text="Edit Selected Student", command=edit_student, bg="#FFC107", fg="black").pack(side="left", padx=5)
tk.Button(center, text="Delete Selected Student", command=delete_student, bg="#f44336", fg="white").pack(side="left", padx=5)

# Assignments Table
assignments_frame = tk.Frame(content, bg="#0c2e4a")
assignments_frame.pack(side="left", padx=50)

tk.Label(assignments_frame, font=("Arial", 20, "bold"), fg="#00ff99", bg="#0c2e4a", text="ASSIGNMENTS").pack(anchor="w", pady=(0,10))

assignments_tree = ttk.Treeview(assignments_frame, columns=("ID", "Student", "Instance", "IP", "OS", "Sent"), show="headings", height=12)
assignments_tree.heading("ID", text="ID")
assignments_tree.heading("Student", text="Student")
assignments_tree.heading("Instance", text="Instance")
assignments_tree.heading("IP", text="IP")
assignments_tree.heading("OS", text="OS")
assignments_tree.heading("Sent", text="Sent")
assignments_tree.column("ID", width=50)
assignments_tree.column("Student", width=180)
assignments_tree.column("Instance", width=150)
assignments_tree.column("IP", width=150)
assignments_tree.column("OS", width=100)
assignments_tree.column("Sent", width=80)
assignments_tree.pack(pady=10)

def update_assignments():
    for i in assignments_tree.get_children():
        assignments_tree.delete(i)
    cur.execute("SELECT a.id, s.name, a.instance_id, a.public_ip, a.os_type, a.sent FROM assignments a JOIN students s ON a.student_id = s.id ORDER BY a.id")
    for row in cur.fetchall():
        assignments_tree.insert("", "end", values=row)

update_assignments()

def mark_as_sent():
    sel = assignments_tree.selection()
    if sel:
        item = assignments_tree.item(sel[0])
        assignment_id = item['values'][0]
        cur.execute("UPDATE assignments SET sent = TRUE, sent_at = NOW() WHERE id = %s", (assignment_id,))
        conn.commit()
        update_assignments()

tk.Button(assignments_frame, text="Mark as Sent", command=mark_as_sent, bg="#4CAF50", fg="white").pack(side="left", padx=5)

# Footer
tk.Label(root, text="EduCloud — From Proxmox VM Bridge to Full AWS Cloud — Ahmed & Aristide 2025",
         font=("Arial", 18), fg="white", bg="#00bfa5").pack(side="bottom", fill="x", pady=20, ipady=15)

root.mainloop()