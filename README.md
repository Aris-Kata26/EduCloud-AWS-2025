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

### Project Structure# EduCloud – Instant Student VMs on AWS (2025)

**One CSV upload → every student instantly gets their own fully configured EC2 VM + automatic email with credentials.**

Zero manual work for teachers · 100 % automated · Classroom-tested

![EduCloud GUI](https://raw.githubusercontent.com/Aris-Kata26/EduCloud-AWS-2025/main/docs/screenshot.png)  
*(Live screenshot – click to enlarge)*

### Features
- Beautiful dark-mode Tkinter GUI for teachers (`gui/main.py`)
- Upload any CSV → Lambda launches one EC2 instance per student in < 60 seconds
- Automatic personalized email via SES (includes `.pem` key for Linux users)
- Golden AMIs (pre-hardened, tools installed, SSH/RDP ready):
  - Ubuntu 22.04 → `ubuntu` user
  - Kali Linux → `kali` user
  - Windows Server 2022 → `Administrator/Welcome123!`
- MySQL RDS backend (tracks students & assignments)
- S3-triggered Lambda (no API Gateway, no server maintenance)
- Clean, professional folder structure

### Project Structure


### Quick Setup (15 minutes)

1. `git clone https://github.com/Aris-Kata26/EduCloud-AWS-2025.git`
2. Copy `.env.example` → `.env` and fill your AWS values
3. Run once: `python scripts/load_schema.py`
4. Upload `deploy/lambda-deploy.zip` to AWS Lambda (handler: `handler.lambda_handler`)
5. Add S3 trigger (bucket → prefix `uploads/` → suffix `.csv`)
6. Done!

### Teacher Workflow (Dead Simple)
1. Run `python gui/main.py`
2. Load a CSV (`name,email,class,os`)
3. Click **Upload & Launch VMs**
4. Students receive email with IP + credentials instantly

### Golden AMIs (see [docs/amis.md](docs/amis.md))
| OS                  | AMI ID                        | Access                         |
|---------------------|-------------------------------|--------------------------------|
| Ubuntu 22.04        | `ami-0d799c9bb6de3354e`      | SSH → `ubuntu`                 |
| Kali Linux          | `ami-0e4f278673927a362`      | SSH → `kali`                   |
| Windows Server 2022 | `ami-08b2e3c6f99cfebc4`      | RDP → `Administrator`          |

### Security & Best Practices
- Secrets only in `.env` and Lambda environment variables (never in Git)
- Private key attached only for Linux instances
- Public IPs + proper security groups
- S3 lifecycle rule moves old CSVs to Glacier after 30 days

Made with passion by **Aris Kata** – BTS SIO SLAM 2025  
Luxembourg

**Star · Fork · Use in your school!**