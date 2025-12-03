# EduCloud – Instant Student VMs on AWS (2025)

**One CSV upload → every student instantly gets their own EC2 instance (Ubuntu / Kali / Windows) + automatic email with login instructions.**

Fully working, classroom-tested, zero manual work after setup.

![EduCloud GUI Preview](https://via.placeholder.com/800x500.png?text=EduCloud+GUI+Preview)  
*(Replace this line later with a real screenshot of gui/main.py)*

### Features
- Beautiful desktop GUI for teachers (`gui/main.py`)
- Upload a simple CSV → Lambda automatically launches EC2 VMs for each student
- Automatic personalized email via SES (with .pem key attached for Linux)
- Golden AMIs (pre-hardened & ready):
  - Ubuntu 22.04 (SSH ready)
  - Kali Linux (SSH ready)
  - Windows Server 2022 (RDP ready – Administrator/Welcome123!)
- MySQL RDS backend (students + assignments tracking)
- S3-triggered Lambda (no API Gateway needed)
- Clean, professional project structure

### Project Structure