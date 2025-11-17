import tkinter as tk  # Import the main GUI toolkit
from tkinter import messagebox, simpledialog  # Import dialog utilities from tkinter
from tkinter import ttk  # Import themed widgets
from proxmoxer import ProxmoxAPI  # Import the Proxmox API client
import threading  # For running background threads
import time  # For sleep/delay functionality
import subprocess
import sys
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

connection = pymysql.connect(
    host=os.getenv("RDS_HOST"),
    user=os.getenv("RDS_USER"),
    password=os.getenv("RDS_PASS"),
    database=os.getenv("RDS_DB"),
)

try:
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        print("Tables in the database:", tables)
finally:
    connection.close()

# --- Proxmox Config ---
PROXMOX_HOST = "10.0.10.11"  # IP of the Proxmox server
PROXMOX_USER = "root@pam"  # Username to access Proxmox
PROXMOX_PASSWORD = "Ahmedala.:12345"  # Password for Proxmox user

# Template options with display name mapped to VMID
TEMPLATES = {
    "Ubuntu Server (100)": 100,
    "Kali Linux (101)": 101,
    "Windows Server (102)": 102
}
TEMPLATE_VMID = list(TEMPLATES.values())[0]  # Default template VMID

VERIFY_SSL = False  # Don't verify SSL certificate (useful for self-signed certs)

# Connect to Proxmox API
proxmox = ProxmoxAPI(PROXMOX_HOST, user=PROXMOX_USER, password=PROXMOX_PASSWORD, verify_ssl=VERIFY_SSL)

vm_checkboxes = []  # Store all VM checkboxes for bulk actions

# Function to find node name for a given VMID
def get_node_for_vmid(vmid):
    for node in proxmox.nodes.get():
        node_name = node["node"]
        for vm in proxmox.nodes(node_name).qemu.get():
            if str(vm["vmid"]) == str(vmid):
                return node_name
    return None

# Function to log messages to the result text box
def log(msg):
    result_text.insert(tk.END, msg + "\n")
    result_text.see(tk.END)
    result_text.update()

# Clone VMs from selected template
def clone_vms():
    base_name = vm_name_entry.get().strip()  # Get the base VM name
    try:
        count = int(vm_count_spinbox.get())  # Get number of VMs to create
    except:
        messagebox.showerror("Error", "Invalid VM count.")
        return

    if not base_name or count < 1:
        messagebox.showerror("Error", "Please enter a base name and a valid count.")
        return

    def task():
        global TEMPLATE_VMID
        selected_template = template_dropdown.get()
        if selected_template not in TEMPLATES:
            log("❌ Please select a valid template.")
            return
        TEMPLATE_VMID = TEMPLATES[selected_template]  # Get the selected template VMID

        template_node = get_node_for_vmid(TEMPLATE_VMID)  # Find which node it's on
        if not template_node:
            log(f"❌ Template VMID {TEMPLATE_VMID} not found.")
            return

        info = proxmox.nodes(template_node).qemu(TEMPLATE_VMID).status.current.get()
        if not info.get("template"):
            log(f"❌ VMID {TEMPLATE_VMID} is not a template.")
            return

        for i in range(1, count + 1):
            name = f"{base_name}-{i}"  # Construct VM name like class1-1, class1-2...
            try:
                new_vmid = proxmox.cluster.nextid.get()  # Get next available VMID
                log(f"🔄 Cloning '{name}' (VMID {new_vmid})...")

                proxmox.nodes(template_node).qemu(TEMPLATE_VMID).clone.post(
                    newid=new_vmid,
                    name=name,
                    full=0  # Linked clone (faster and saves space)
                )

                # Wait until VM is ready
                for attempt in range(30):
                    try:
                        vm_status = proxmox.nodes(template_node).qemu(new_vmid).status.current.get()
                        if vm_status.get("status") in ["stopped", "running"]:
                            break
                    except:
                        pass
                    time.sleep(2)

                # Start the VM
                proxmox.nodes(template_node).qemu(new_vmid).status.start.post()
                log(f"✅ Started VM '{name}' (VMID {new_vmid})")
            except Exception as e:
                log(f"❌ Error with '{name}': {e}")

        update_vm_list()

    threading.Thread(target=task).start()  # Run cloning in background thread

def fetch_ips():
    def task():
        log("🌐 Fetching IPs of all VMs...")
        for node in proxmox.nodes.get():
            node_name = node["node"]
            for vm in proxmox.nodes(node_name).qemu.get():
                if vm.get("template"):
                    continue
                vmid = str(vm["vmid"])
                name = vm.get("name", f"VM-{vmid}")
                try:
                    raw_data = proxmox.nodes(node_name).qemu(vmid).agent("network-get-interfaces").get()

                    # Check format
                    if isinstance(raw_data, dict) and "result" in raw_data:
                        interfaces = raw_data["result"]
                    elif isinstance(raw_data, list):
                        interfaces = raw_data
                    else:
                        interfaces = []

                    ip_found = None
                    for iface in interfaces:
                        ip_list = iface["ip-addresses"] if "ip-addresses" in iface else []
                        for ipinfo in ip_list:
                            if (
                                ipinfo.get("ip-address-type") == "ipv4"
                                and not ipinfo.get("ip-address", "").startswith("127.")
                            ):
                                ip_found = ipinfo["ip-address"]
                                break
                        if ip_found:
                            break

                    if ip_found:
                        log(f"✅ {name} ({vmid}) IP: {ip_found}")
                    else:
                        log(f"⚠️ {name} ({vmid}) → No IP found.")
                except Exception as e:
                    log(f"⚠️ {name} ({vmid}) → Error fetching IP: {e}")
    threading.Thread(target=task).start()


def launch_email_tool():
    try:
        subprocess.Popen(["python", "email_assigner.py"])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to launch email tool:\n{e}")

def start_selected_vms():
    def task():
        log("⚙️ Starting selected VMs...")
        for cb, vmid in vm_checkboxes:
            if cb.var.get():
                node = get_node_for_vmid(vmid)
                try:
                    proxmox.nodes(node).qemu(vmid).status.start.post()
                    log(f"✅ Started VMID {vmid}")
                except Exception as e:
                    log(f"❌ Failed to start VMID {vmid}: {e}")
        update_vm_list()
    threading.Thread(target=task).start()

# Function to perform reboot/shutdown/delete in bulk
def perform_bulk_action(action):
    def task():
        for cb, vmid in vm_checkboxes:
            if cb.var.get():  # Only act on selected VMs
                node = get_node_for_vmid(vmid)
                if not node:
                    log(f"❌ VMID {vmid} not found.")
                    continue
                try:
                    if action == "reboot":
                        proxmox.nodes(node).qemu(vmid).status.reboot.post()
                        log(f"🔁 Rebooted VMID {vmid}")
                    elif action == "shutdown":
                        proxmox.nodes(node).qemu(vmid).status.shutdown.post()
                        log(f"⏹️ Shutdown VMID {vmid}")
                    elif action == "delete":
                        proxmox.nodes(node).qemu(vmid).delete()
                        log(f"🗑️ Deleted VMID {vmid}")
                except Exception as e:
                    log(f"❌ Error on VMID {vmid}: {e}")
        update_vm_list()
    threading.Thread(target=task).start()

# Rebuild the list of VMs and their checkboxes
def update_vm_list(query=""):
    for widget in vm_list_frame.winfo_children():
        widget.destroy()
    vm_checkboxes.clear()
    query = query.lower()

    for node in proxmox.nodes.get():
        node_name = node["node"]
        for vm in proxmox.nodes(node_name).qemu.get():
            if vm.get("template"):
                continue

            name = vm.get("name", f"VM-{vm['vmid']}")
            vmid = str(vm["vmid"])
            status = vm.get("status", "unknown")

            if query not in name.lower() and query not in vmid:
                continue

            row = tk.Frame(vm_list_frame, bg="#ffffff", pady=5)
            row.pack(fill="x", padx=10)

            var = tk.BooleanVar()
            cb = tk.Checkbutton(row, variable=var, font=("Segoe UI", 14), bg="#ffffff")
            cb.var = var  # ✅ this line is CRITICAL for fetch_ips() to work
            cb.pack(side="left", padx=5)

            color = "green" if status == "running" else "red"
            dot = tk.Canvas(row, width=12, height=12, bg="#ffffff", highlightthickness=0)
            dot.create_oval(2, 2, 10, 10, fill=color)
            dot.pack(side="left")

            label = tk.Label(row, text=f"{name} (VMID {vmid}, {status})", font=("Segoe UI", 14), bg="#ffffff")
            label.pack(side="left")

            vm_checkboxes.append((cb, vmid))

# Select all checkboxes
def select_all_vms():
    for cb, _ in vm_checkboxes:
        cb.var.set(True)

# GUI Initialization
root = tk.Tk()
root.title("Proxmox Classroom VM Manager")
root.geometry("950x700")
root.configure(padx=20, pady=20)

# Input fields and buttons

# --- Redesigned Top Container (Styled with spacing and borders) ---
top_container = tk.Frame(root, bg="#ffffff")
top_container.pack(fill="x", padx=20, pady=(10, 30))  # <-- Added bottom space (30px)

style = {
    "font": ("Segoe UI", 12),
    "bg": "white",
    "highlightbackground": "#000000",  # Thin black border
    "highlightcolor": "#000000",
    "highlightthickness": 1,
    "bd": 0,
    "relief": "flat"
}

# VM Base Name
tk.Label(top_container, text="VM Base Name, e.g. Kali-BTS-1:", font=("Segoe UI", 14), bg="#ffffff").grid(row=0, column=0, sticky="e", padx=5, pady=5)
vm_name_entry = tk.Entry(top_container, width=50, **style)
vm_name_entry.grid(row=0, column=1, padx=5, pady=5)

# VM Count
tk.Label(top_container, text="Number of VMs:", font=("Segoe UI", 14), bg="#ffffff").grid(row=1, column=0, sticky="e", padx=5, pady=5)
vm_count_spinbox = tk.Spinbox(top_container, from_=1, to=50, width=5, **style)

vm_count_spinbox.grid(row=1, column=1, padx=5, pady=5, sticky="w")

# Template Dropdown
tk.Label(top_container, text="Select Template:", font=("Segoe UI", 14), bg="#ffffff").grid(row=2, column=0, sticky="e", padx=5, pady=5)
template_dropdown = ttk.Combobox(top_container, values=list(TEMPLATES.keys()), state="readonly", font=("Segoe UI", 14), width=38)
template_dropdown.current(0)
template_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="w")

# Inline Buttons
button_frame = tk.Frame(top_container, bg="#ffffff")
button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 5))

tk.Button(button_frame, text="Create VMs", command=clone_vms, bg="#4CAF50", fg="white", font=("Segoe UI", 14), padx=10, pady=5).pack(side="left", padx=10)
tk.Button(button_frame, text="Launch VM Assignment Email Tool", command=launch_email_tool, bg="#9C27B0", fg="white", font=("Segoe UI", 11), padx=10, pady=5).pack(side="left", padx=10)


# --- Redesigned VM Section with Filters, Actions & Results Panel ---

# Store checkboxes
vm_checkboxes = []

def update_vm_list(query=""):
    for widget in vm_list_frame.winfo_children():
        widget.destroy()
    vm_checkboxes.clear()
    query = query.lower()
    for node in proxmox.nodes.get():
        node_name = node["node"]
        for vm in proxmox.nodes(node_name).qemu.get():
            if vm.get("template"):
                continue
            name = vm.get("name", f"VM-{vm['vmid']}")
            vmid = str(vm["vmid"])
            status = vm.get("status", "unknown")
            if query not in name.lower() and query not in vmid:
                continue
            row = tk.Frame(vm_list_frame, bg="#ffffff", pady=5)
            row.pack(fill="x", padx=10)
            var = tk.BooleanVar()
            cb = tk.Checkbutton(row, variable=var, font=("Segoe UI", 14), bg="#ffffff")
            cb.pack(side="left", padx=5)
            color = "green" if status == "running" else "red"
            dot = tk.Canvas(row, width=12, height=12, bg="#ffffff", highlightthickness=0)
            dot.create_oval(2, 2, 10, 10, fill=color)
            dot.pack(side="left")
            label = tk.Label(row, text=f"{name} (VMID {vmid}, {status})", font=("Segoe UI", 14), bg="#ffffff")
            label.pack(side="left")
            vm_checkboxes.append((cb, vmid))
            cb.var = var  # Save var for control

def search_vms(event=None):
    update_vm_list(search_entry.get())

def filter_os(os_keyword):
    update_vm_list(os_keyword)

def select_all_vms():
    for cb, _ in vm_checkboxes:
        cb.var.set(True)

def deselect_all_vms():
    for cb, _ in vm_checkboxes:
        cb.var.set(False)

# ----------- Layout Setup ------------

main_frame = tk.Frame(root, bg="#eeeeee")
main_frame.pack(fill="both", expand=True)

left_frame = tk.Frame(main_frame, bg="#ffffff", width=850)
left_frame.pack(side="left", fill="both", expand=True)

right_frame = tk.Frame(main_frame, bg="#f9f9f9", width=400)
right_frame.pack(side="right", fill="both")

# --- Search and Filters (top row)
top_controls = tk.Frame(left_frame, bg="#ffffff")
top_controls.pack(fill="x", padx=10, pady=(10, 0))

search_entry = tk.Entry(top_controls, font=("Segoe UI", 13), width=30)
search_entry.pack(side="left", padx=(0, 10))
search_entry.bind("<Return>", search_vms)

tk.Button(top_controls, text="Search", command=search_vms, bg="#2196F3", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(top_controls, text="Ubuntu", command=lambda: filter_os("ubuntu"), bg="#4CAF50", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(top_controls, text="Kali", command=lambda: filter_os("kali"), bg="#FF9800", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(top_controls, text="Windows", command=lambda: filter_os("windows"), bg="#9C27B0", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(top_controls, text="Refrish", command=lambda: update_vm_list(), bg="#9E9E9E", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)

# --- Action Buttons (right above VM list)
action_controls = tk.Frame(left_frame, bg="#ffffff")
action_controls.pack(fill="x", padx=10, pady=(10, 5))

tk.Button(action_controls, text="Select All", command=select_all_vms, bg="#03A9F4", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(action_controls, text="Deselect All", command=deselect_all_vms, bg="#607D8B", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(action_controls, text="Fetch IPs", command=fetch_ips, bg="#3F51B5", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(action_controls, text="Start Selected", command=start_selected_vms, bg="#4CAF50", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(action_controls, text="Reboot Selected", command=lambda: perform_bulk_action("reboot"), bg="#FFC107", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(action_controls, text="Shutdown Selected", command=lambda: perform_bulk_action("shutdown"), bg="#FF9800", font=("Segoe UI", 11)).pack(side="left", padx=5)
tk.Button(action_controls, text="Delete Selected", command=lambda: perform_bulk_action("delete"), bg="#f44336", fg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)

# --- VM Scroll Area
vm_canvas = tk.Canvas(left_frame, bg="#ffffff", highlightthickness=0)
vm_scrollbar = tk.Scrollbar(left_frame, orient="vertical", command=vm_canvas.yview)
vm_canvas.configure(yscrollcommand=vm_scrollbar.set)

vm_scrollbar.pack(side="right", fill="y")
vm_canvas.pack(side="left", fill="both", expand=True)

vm_list_frame = tk.Frame(vm_canvas, bg="#ffffff")
vm_canvas.create_window((0, 0), window=vm_list_frame, anchor="nw")
vm_list_frame.bind("<Configure>", lambda e: vm_canvas.configure(scrollregion=vm_canvas.bbox("all")))

# --- Results Panel (Right)
results_header = tk.Frame(right_frame, bg="#f9f9f9")
results_header.pack(fill="x", padx=10, pady=(10, 0))

tk.Label(results_header, text="Results:", font=("Segoe UI", 12, "bold"), anchor="w", bg="#f9f9f9").pack(side="left")

def clear_results():
    result_text.delete(1.0, tk.END)

tk.Button(results_header, text="Clear Results", command=clear_results, bg="#f44336", fg="white", font=("Segoe UI", 10)).pack(side="right")

result_text = tk.Text(right_frame, font=("Consolas", 11), bg="#ffffff", height=25, width=50)
result_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))


# --- Initial load
update_vm_list()


root.mainloop()  # Start the GUI main loop


