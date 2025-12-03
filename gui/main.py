import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import boto3
import os
import csv
from io import StringIO, BytesIO
from dotenv import load_dotenv
 
load_dotenv()
 
# ---------- AWS ----------
aws_region = os.getenv("AWS_REGION", "us-east-1")
s3 = boto3.client("s3", region_name=aws_region)
 
S3_BUCKET = os.getenv("S3_BUCKET")
 
# ---------- ROOT WINDOW ----------
root = tk.Tk()
root.title("EduCloud — CSV Launcher")
root.geometry("1000x700")
root.configure(bg="#0b1120")
 
# ---------- STYLES ----------
style = ttk.Style()
style.theme_use("clam")
 
CARD_BG = "#020617"
TEXT_MAIN = "#e5e7eb"
TEXT_MUTED = "#9ca3af"
PRIMARY_COLOR = "#2563eb"
ACCENT_COLOR = "#22c55e"
 
style.configure("Main.TFrame", background="#0b1120")
style.configure("Card.TFrame", background=CARD_BG)
style.configure("Header.TFrame", background="#020617")
style.configure("Header.TLabel", background="#020617", foreground=TEXT_MAIN,
                font=("Segoe UI", 24, "bold"))
style.configure("SubHeader.TLabel", background="#020617", foreground=TEXT_MUTED,
                font=("Segoe UI", 11))
style.configure("SectionTitle.TLabel", background=CARD_BG, foreground=TEXT_MAIN,
                font=("Segoe UI", 15, "bold"))
style.configure("FieldLabel.TLabel", background=CARD_BG, foreground=TEXT_MUTED,
                font=("Segoe UI", 11))
 
style.configure("Primary.TButton", background=PRIMARY_COLOR, foreground="white",
                borderwidth=0, padding=8, font=("Segoe UI", 11, "bold"))
style.map("Primary.TButton", background=[("active", "#1d4ed8")])
 
style.configure("Success.TButton", background=ACCENT_COLOR, foreground="white",
                borderwidth=0, padding=10, font=("Segoe UI", 12, "bold"))
style.map("Success.TButton", background=[("active", "#16a34a")])
 
style.configure("Modern.Treeview",
                background=CARD_BG,
                fieldbackground=CARD_BG,
                foreground=TEXT_MAIN,
                bordercolor="#1f2937",
                rowheight=26)
style.configure("Modern.Treeview.Heading",
                background=CARD_BG,
                foreground=TEXT_MUTED,
                font=("Segoe UI", 10, "bold"))
style.map("Modern.Treeview",
          background=[("selected", "#1d4ed8")])
 
# ---------- STATE ----------
# now includes "class"
rows = []          # each row: {"name": ..., "email": ..., "class": ..., "os": ...}
current_filename = None
 
# ---------- HEADER ----------
header = ttk.Frame(root, style="Header.TFrame", padding=(20, 16))
header.pack(fill="x")
 
ttk.Label(header, text="EduCloud CSV Launcher", style="Header.TLabel").pack(anchor="w")
ttk.Label(header,
          text="Load a CSV (name, email, class, os), edit it, then upload to S3 to launch VMs.",
          style="SubHeader.TLabel").pack(anchor="w", pady=(4, 0))
 
# ---------- MAIN ----------
main = ttk.Frame(root, style="Main.TFrame", padding=16)
main.pack(fill="both", expand=True)
 
# ---------- LEFT CARD (controls) ----------
left_card = ttk.Frame(main, style="Card.TFrame", padding=16)
left_card.pack(side="left", fill="y", padx=(0, 12))
 
ttk.Label(left_card, text="Workflow", style="SectionTitle.TLabel").pack(anchor="w")
 
ttk.Label(
    left_card,
    text=(
        "1. Click \"Load CSV\" and choose your file\n"
        "   (columns: name, email, class, os).\n"
        "2. Review and edit rows in the table.\n"
        "3. Click \"Upload & Launch VMs\" to send the\n"
        "   final CSV to S3."
    ),
    style="FieldLabel.TLabel",
    justify="left",
    wraplength=260
).pack(anchor="w", pady=(8, 16))
 
 
def refresh_table():
    table.delete(*table.get_children())
    for idx, r in enumerate(rows):
        table.insert(
            "",
            "end",
            iid=str(idx),
            values=(r["name"], r["email"], r["class"], r["os"])
        )
 
 
def load_csv():
    global rows, current_filename
    file_path = filedialog.askopenfilename(
        title="Select students.csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if not file_path:
        return
 
    try:
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # lower-case header names for check
            header_lower = {c.lower() for c in reader.fieldnames}
            required = {"name", "email", "class", "os"}
            if not required.issubset(header_lower):
                messagebox.showerror(
                    "Invalid CSV",
                    "CSV must contain columns: name, email, class, os (case-insensitive).",
                )
                return
 
            rows = []
            for row in reader:
                rows.append(
                    {
                        "name": row.get("name") or row.get("Name") or "",
                        "email": row.get("email") or row.get("Email") or "",
                        "class": row.get("class") or row.get("Class") or "",
                        "os": (row.get("os") or row.get("OS") or "ubuntu").lower(),
                    }
                )
 
        current_filename = os.path.basename(file_path)
        refresh_table()
        messagebox.showinfo(
            "Loaded", f"Loaded {len(rows)} rows from {current_filename}"
        )
    except Exception as e:
        messagebox.showerror("Read error", f"Could not read CSV:\n{e}")
 
 
def upload_and_launch():
    if not rows:
        messagebox.showwarning(
            "No data", "Load a CSV and/or add rows before uploading."
        )
        return
    if not S3_BUCKET:
        messagebox.showerror("Config error", "S3_BUCKET is not set in .env")
        return
 
    # Build CSV from current table
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=["name", "email", "class", "os"])
    writer.writeheader()
    writer.writerows(rows)
    data = buf.getvalue().encode("utf-8")
 
    key_name = f"uploads/{current_filename or 'students.csv'}"
 
    try:
        s3.upload_fileobj(BytesIO(data), S3_BUCKET, key_name)
        messagebox.showinfo(
            "Uploaded",
            f"CSV uploaded to s3://{S3_BUCKET}/{key_name}\n\n"
            "Lambda will now launch VMs and email the students.",
        )
    except Exception as e:
        messagebox.showerror("Upload failed", f"Could not upload CSV:\n{e}")
 
 
def add_row():
    name = simpledialog.askstring("New row", "Student name:")
    if not name:
        return
    email = simpledialog.askstring("New row", "Email:")
    if not email:
        return
    cls = simpledialog.askstring("New row", "Class (e.g. BTS2CLC):") or ""
    os_type = simpledialog.askstring(
        "New row", "OS (ubuntu/kali/windows):", initialvalue="ubuntu"
    )
    if not os_type:
        os_type = "ubuntu"
 
    rows.append(
        {
            "name": name.strip(),
            "email": email.strip().lower(),
            "class": cls.strip(),
            "os": os_type.strip().lower(),
        }
    )
    refresh_table()
 
 
def edit_selected():
    sel = table.selection()
    if not sel:
        messagebox.showwarning("No selection", "Select a row to edit.")
        return
    idx = int(sel[0])
    row = rows[idx]
 
    new_name = simpledialog.askstring(
        "Edit row", "Student name:", initialvalue=row["name"] or ""
    )
    if not new_name:
        return
    new_email = simpledialog.askstring(
        "Edit row", "Email:", initialvalue=row["email"] or ""
    )
    if not new_email:
        return
    new_class = simpledialog.askstring(
        "Edit row", "Class:", initialvalue=row["class"] or ""
    ) or ""
    new_os = simpledialog.askstring(
        "Edit row", "OS (ubuntu/kali/windows):", initialvalue=row["os"] or "ubuntu"
    )
    if not new_os:
        new_os = "ubuntu"
 
    rows[idx] = {
        "name": new_name.strip(),
        "email": new_email.strip().lower(),
        "class": new_class.strip(),
        "os": new_os.strip().lower(),
    }
    refresh_table()
 
 
def delete_selected():
    sel = table.selection()
    if not sel:
        messagebox.showwarning("No selection", "Select a row to delete.")
        return
    idx = int(sel[0])
    if messagebox.askyesno("Confirm delete", "Remove this row from the CSV?"):
        rows.pop(idx)
        refresh_table()
 
 
load_btn = ttk.Button(
    left_card, text="Load CSV", style="Primary.TButton", command=load_csv
)
load_btn.pack(fill="x", pady=(0, 8))
 
upload_btn = ttk.Button(
    left_card,
    text="Upload & Launch VMs",
    style="Success.TButton",
    command=upload_and_launch,
)
upload_btn.pack(fill="x", pady=(0, 16))
 
ttk.Button(
    left_card, text="Add row", style="Primary.TButton", command=add_row
).pack(fill="x", pady=(4, 2))
ttk.Button(
    left_card, text="Edit selected row", style="Primary.TButton", command=edit_selected
).pack(fill="x", pady=2)
ttk.Button(
    left_card, text="Delete selected row", style="Primary.TButton", command=delete_selected
).pack(fill="x", pady=2)
 
# ---------- RIGHT CARD (table) ----------
right_card = ttk.Frame(main, style="Card.TFrame", padding=16)
right_card.pack(side="right", fill="both", expand=True)
 
ttk.Label(right_card, text="CSV preview (editable)", style="SectionTitle.TLabel").pack(
    anchor="w"
)
 
table = ttk.Treeview(
    right_card,
    columns=("name", "email", "class", "os"),
    show="headings",
    style="Modern.Treeview",
)
table.heading("name", text="Name")
table.heading("email", text="Email")
table.heading("class", text="Class")
table.heading("os", text="OS")
 
table.column("name", width=200)
table.column("email", width=260)
table.column("class", width=120, anchor="center")
table.column("os", width=80, anchor="center")
 
table.pack(fill="both", expand=True, pady=(8, 0))
 
root.mainloop()