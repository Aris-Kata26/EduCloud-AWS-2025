import tkinter as tk
from tkinter import ttk, messagebox
import smtplib
from email.message import EmailMessage
from proxmoxer import ProxmoxAPI
import threading

# --- Proxmox Config ---
PROXMOX_HOST = "10.0.10.11"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "Ahmedala.:12345"
VERIFY_SSL = False
proxmox = ProxmoxAPI(PROXMOX_HOST, user=PROXMOX_USER, password=PROXMOX_PASSWORD, verify_ssl=VERIFY_SSL)

# Templates and Students
TEMPLATES = {
    "Ubuntu Server (100)": 100,
    "Kali Linux (101)": 101,
    "Windows Server (102)": 102
}
students = [
    {"name": "Aristide Katagaruka", "class": "BTS-2", "email": "KatAr711@school.lu"},
    {"name": "Laurence Weber", "class": "BTS-2", "email": "WebLa453@school.lu"},
    {"name": "Ahmed AL-ASADI", "class": "BTS-2", "email": "al-ah960@school.lu"},
]
SENDER_EMAIL = "ahmaadalasadi@gmail.com"
SENDER_APP_PASSWORD = "lsxd urot umhz rfpv"

root = tk.Tk()
root.title("VM Email Assignment Tool")
root.geometry("900x650")
root.configure(padx=20, pady=20)

# Log area
result_text = tk.Text(root, height=10, width=110)
result_text.pack(pady=10)
def log(msg):
    result_text.insert(tk.END, msg + "\n")
    result_text.see(tk.END)
    result_text.update()

# Proxmox helper
def get_node_for_vmid(vmid):
    for node in proxmox.nodes.get():
        for vm in proxmox.nodes(node['node']).qemu.get():
            if str(vm['vmid']) == str(vmid):
                return node['node']
    return None

def get_credentials_and_instructions(os_type, ip):
    os_lower = os_type.lower()
    if "kali" in os_lower:
        username = "kali"
        password = "test..123"
        connect_html = f"""
        <h3 style="color: #2196F3;">📥 How to Access Your VM (via SSH)</h3>
        <p>Use <strong>MobaXterm</strong>, a free SSH client for Windows:</p>
        <ul>
            <li><a href="https://mobaxterm.mobatek.net/download.html" style="color: #2196F3;">Download MobaXterm</a></li>
            <li>Click <strong>Session</strong> > <strong>SSH</strong></li>
            <li>Enter the IP: <code>{ip}</code></li>
            <li>Username: <code>kali</code>, Password: <code>test..123</code></li>
        </ul>
        """
    elif "windows" in os_lower:
        username = "Administrator"
        password = "test..123"
        connect_html = f"""
        <h3 style="color: #2196F3;">🪟 How to Access Your Windows VM (Remote Desktop)</h3>
        <p>We recommend using the built-in <strong>Remote Desktop Connection</strong> app:</p>
        <ul>
            <li>Press <code>Win + R</code> → type <strong>mstsc</strong> → press Enter</li>
            <li>Enter the IP: <code>{ip}</code></li>
            <li>Username: <code>Administrator</code></li>
            <li>Password: <code>test..123</code></li>
        </ul>
        <p>If prompted for certificate, click "Yes" or "Continue".</p>
        """
    else:
        username = "ubuntu"
        password = "ubuntu"
        connect_html = f"""
        <h3 style="color: #2196F3;">📥 How to Access Your VM (via SSH)</h3>
        <p>Use <strong>MobaXterm</strong>, a free SSH client for Windows:</p>
        <ul>
            <li><a href="https://mobaxterm.mobatek.net/download.html" style="color: #2196F3;">Download MobaXterm</a></li>
            <li>Click <strong>Session</strong> > <strong>SSH</strong></li>
            <li>Enter the IP: <code>{ip}</code></li>
            <li>Username: <code>ahmed</code>, Password: <code>dd</code></li>
        </ul>
        """
    return username, password, connect_html


# Email sender logic
def send_selected_vm_info():
    selected_class = class_dropdown.get()
    class_students = [s for s in students if s["class"] == selected_class]
    selected_vms = [vm for vm, var in assign_vm_checkboxes if var.get()]

    if not selected_class:
        messagebox.showerror("Error", "Please select a class.")
        return
    if not selected_vms:
        messagebox.showerror("Error", "No VMs selected.")
        return
    if len(selected_vms) < len(class_students):
        messagebox.showerror("Error", f"Not enough VMs selected. {len(class_students)} students, {len(selected_vms)} VMs.")
        return

    def task():
        for student, (vmid, name) in zip(class_students, selected_vms):
            node = get_node_for_vmid(vmid)
            if not node:
                log(f"❌ Cannot find node for VMID {vmid}")
                continue
            try:
                name_lower = name.lower()
                if "kali" in name_lower:
                    os_type = "Kali Linux"
                elif "windows" in name_lower:
                    os_type = "Windows Server 2022"
                else:
                    os_type = "Ubuntu Server"

                # Attempt to get the VM's IP address from Proxmox guest-agent, fallback to "N/A"
                ip = "N/A"
                vm_status = proxmox.nodes(node).qemu(vmid).agent('network-get-interfaces').get() if hasattr(proxmox.nodes(node).qemu(vmid), 'agent') else None
                if vm_status and isinstance(vm_status, dict):
                    for iface in vm_status.get('result', []):
                        for addr in iface.get('ip-addresses', []):
                            if addr.get('ip-address') and not addr.get('ip-address').startswith('127.') and ':' not in addr.get('ip-address'):
                                ip = addr.get('ip-address')
                                break
                        if ip != "N/A":
                            break

                msg = EmailMessage()
                msg["Subject"] = "Your Assigned Virtual Machine"
                msg["From"] = SENDER_EMAIL
                msg["To"] = student["email"]
                username, password, connect_html = get_credentials_and_instructions(os_type, ip)

                msg.set_content("This email requires an HTML-capable email client.")
                msg.add_alternative(f"""
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
    <div style="background-color: white; border-radius: 8px; padding: 20px; border: 1px solid #ddd;">
      <h2 style="color: #4CAF50;">🎓 Your Assigned Virtual Machine</h2>
      <p>Dear <strong>{student['name']}</strong>,</p>

      <p>Below are the details of your assigned virtual machine for use in the <strong>{selected_class}</strong> class:</p>

      <table style="border-collapse: collapse; margin: 15px 0;">
        <tr><td><strong>🖥️ VM Name:</strong></td><td>{name}</td></tr>
        <tr><td><strong>💻 OS Type:</strong></td><td>{os_type}</td></tr>
        <tr><td><strong>🌐 IP Address:</strong></td><td>{ip}</td></tr>
        <tr><td><strong>👤 Username:</strong></td><td>{username}</td></tr>
        <tr><td><strong>🔐 Password:</strong></td><td>{password}</td></tr>
      </table>

      {connect_html}

      <h3 style="color: #FF5722;">📌 Important Reminders</h3>
      <ul>
        <li>Do not install unnecessary software or change critical configurations</li>
        <li>Your activity may be monitored for academic integrity</li>
        <li>If you experience connection issues, contact your instructor</li>
      </ul>

      <p style="margin-top: 20px;">Best regards,<br><strong>Your Instructor</strong></p>
    </div>
  </body>
</html>
""", subtype="html")


                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                    smtp.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
                    smtp.send_message(msg)
                log(f"✅ Sent to {student['name']} ({student['email']})")
            except Exception as e:
                log(f"❌ Error sending to {student['email']}: {e}")
    threading.Thread(target=task).start()

# --- GUI Setup ---

# Class selector label
tk.Label(root, text="Select Class to Email VMs:", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 0), padx=5)

# Styled Combobox
style = ttk.Style()
style.theme_use('clam')  # Use 'clam' to allow styling
style.configure("Custom.TCombobox",
                fieldbackground="#ffffff",
                background="#ffffff",
                foreground="#000000",
                padding=8,
                relief="flat",
                bordercolor="#4CAF50",
                font=("Segoe UI", 8, "bold"))

class_dropdown = ttk.Combobox(root, values=["BTS-1", "BTS-2"],
                              state="readonly", width=20,
                              style="Custom.TCombobox",
                                background="#ffffff", foreground="#000000",
                              font=("Segoe UI", 11, "bold")
                                )
class_dropdown.pack(pady=5, padx=10)
class_dropdown.current(0)


# VM list label
tk.Label(root, text="Select VMs to Assign:").pack(anchor="w", pady=(10, 0))

# --- VM List Section with Filters and Styling ---

assign_vm_checkboxes = []

def update_vm_list(query=""):
    for widget in vm_list_frame.winfo_children():
        widget.destroy()
    assign_vm_checkboxes.clear()
    query = query.lower()
    for node in proxmox.nodes.get():
        for vm in proxmox.nodes(node["node"]).qemu.get():
            if vm.get("template"):
                continue
            vmid = str(vm["vmid"])
            name = vm.get("name", f"VM-{vmid}")
            status = vm.get("status", "unknown")
            if query not in name.lower() and query not in vmid:
                continue
            row = tk.Frame(vm_list_frame, pady=4, bg="#ffffff")
            row.pack(fill="x", anchor="w", padx=10)
            var = tk.BooleanVar()
            cb = tk.Checkbutton(row, variable=var, font=("Segoe UI", 12), bg="#ffffff")
            cb.pack(side="left", padx=10)
            lbl = tk.Label(row, text=f"{name} (VMID {vmid}, {status})", font=("Segoe UI", 12), bg="#ffffff")
            lbl.pack(side="left")
            assign_vm_checkboxes.append(((vmid, name), var))

def filter_os(os_name):
    update_vm_list(os_name)

def on_search(event=None):
    update_vm_list(search_entry.get())

# Top bar: Search + Filter Buttons
top_frame = tk.Frame(root, bg="#ffffff")
top_frame.pack(fill="x", padx=10, pady=10)

search_entry = tk.Entry(top_frame, width=30, font=("Segoe UI", 12))
search_entry.pack(side="left", padx=(0, 10))
search_entry.bind("<Return>", on_search)

tk.Button(top_frame, text="Search", command=on_search, bg="#2196F3", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(top_frame, text="Ubuntu", command=lambda: filter_os("ubuntu"), bg="#4CAF50", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(top_frame, text="Kali", command=lambda: filter_os("kali"), bg="#FF9800", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(top_frame, text="Windows", command=lambda: filter_os("win"), bg="#9C27B0", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(top_frame, text="Reset", command=lambda: update_vm_list(), bg="#9E9E9E", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)

# Scrollable area
vm_canvas = tk.Canvas(root, bg="#ffffff", highlightthickness=0, height=300)
vm_scrollbar = tk.Scrollbar(root, orient="vertical", command=vm_canvas.yview)
vm_canvas.configure(yscrollcommand=vm_scrollbar.set)

vm_scrollbar.pack(side="right", fill="y")
vm_canvas.pack(side="left", fill="both", expand=True)

scroll_frame = tk.Frame(vm_canvas, bg="#ffffff")
vm_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

def configure_scroll_region(event):
    vm_canvas.configure(scrollregion=vm_canvas.bbox("all"))

scroll_frame.bind("<Configure>", configure_scroll_region)
vm_list_frame = scroll_frame

# Refresh, Select, and Send Buttons
bottom_frame = tk.Frame(root, bg="#ffffff")
bottom_frame.pack(pady=10)

tk.Button(bottom_frame, text="Refresh VM List", command=lambda: update_vm_list(), bg="#03A9F4", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)

tk.Button(bottom_frame, text="Select All", command=lambda: [var.set(True) for (_, var) in assign_vm_checkboxes],
          bg="#673AB7", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)

tk.Button(bottom_frame, text="Deselect All", command=lambda: [var.set(False) for (_, var) in assign_vm_checkboxes],
          bg="#795548", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)

tk.Button(bottom_frame, text="Send VM Info to Class", command=send_selected_vm_info,
          bg="#4CAF50", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)

# Initial load
update_vm_list()

# Start GUI
root.mainloop()
