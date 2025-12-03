# EDU CLOUD – FINAL VERSION 100% WORKING WITH YOUR EXACT ENV VARS
import json, os, csv, base64, traceback
from io import StringIO
import boto3, pymysql
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def get_db_connection():
    return pymysql.connect(
        host=os.environ['RDS_HOST'],
        user=os.environ['RDS_USER'],
        password=os.environ['RDS_PASS'],
        database=os.environ['RDS_DB'],
        connect_timeout=10,
        read_timeout=10,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )

AMI_MAP = {
    "ubuntu":  "ami-0d799c9bb6de3354e",
    "windows": "ami-08b2e3c6f99cfebc4",
    "kali":    "ami-0e4f278673927a362"
}

def lambda_handler(event, context):
    # --- S3 Trigger ---
    bucket = event['Records'][0]['s3']['bucket']['name']
    key    = event['Records'][0]['s3']['object']['key']
    if not key.startswith("uploads/"):
        return {"statusCode": 200}

    s3  = boto3.client('s3')
    ec2 = boto3.resource('ec2')
    ses = boto3.client('ses', region_name='us-east-1')

    # Your private key from env var (already perfect)
    private_key_pem=os.environ['EDUCLOUD_PRIVATE_KEY']

    csv_content = s3.get_object(Bucket=bucket, Key=key)['Body'].read().decode('utf-8-sig')

    for i, row in enumerate(csv.DictReader(StringIO(csv_content))):
        try:
            name    = row.get('name', 'Student').strip()
            email   = row.get('email', '').strip().lower()
            os_type = (row.get('os', 'ubuntu') or 'ubuntu').strip().lower()

            if not email or '@' not in email:
                print(f"Skipping invalid row {i}")
                continue

            # --- Check student exists ---
            conn = get_db_connection()
            cur  = conn.cursor()
            cur.execute("SELECT id FROM students WHERE email=%s", (email,))
            if not cur.fetchone():
                print(f"Student {email} not in DB")
                conn.close()
                continue

            # --- UserData only for Windows ---
            user_data = None
            if os_type == "windows":
                user_data = '''<powershell>
<persist>true</persist>
net user Administrator Welcome123!
netsh advfirewall firewall set rule group="remote desktop" new enable=Yes
</powershell>'''

            # --- Instance launch parameters (100% safe) ---
            launch_params = {
                "ImageId": AMI_MAP[os_type],
                "InstanceType": "t3.micro",
                "MinCount": 1,
                "MaxCount": 1,
                "KeyName": os.environ['EC2_KEY_NAME'],  # Key pair name
                "NetworkInterfaces": [{
                    "DeviceIndex": 0,
                    "SubnetId": os.environ['EC2_SUBNET_ID'],  # Subnet ID
                    "Groups": [os.environ['EC2_SG_ID']],      # Security group ID
                    "AssociatePublicIpAddress": True         # Must be inside NetworkInterfaces
                }],
                "TagSpecifications": [{
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": f"EduCloud-{name}"}]
                }]
            }
            if user_data:
                launch_params["UserData"] = user_data

            instance = ec2.create_instances(**launch_params)[0]
            instance.wait_until_running()
            instance.reload()
            public_ip = instance.public_ip_address

            # --- Save to DB ---
            cur.execute("""INSERT INTO assignments (student_id, instance_id, public_ip, os_type, sent)
                           VALUES ((SELECT id FROM students WHERE email=%s), %s, %s, %s, 1)
                           ON DUPLICATE KEY UPDATE public_ip=%s, instance_id=%s""",
                        (email, instance.id, public_ip, os_type, public_ip, instance.id))
            conn.close()

            # --- EMAIL + .pem ATTACHMENT ---
            if os_type == "windows":
                html_body = f"""
                <h1>Welcome to EduCloud!</h1>
                <p>Hi {name.split()[0]}, your Windows VM is ready!</p>
                <ul>
                    <li><b>IP:</b> {public_ip}</li>
                    <li><b>Username:</b> Administrator</li>
                    <li><b>Password:</b> Welcome123!</li>
                </ul>
                <p>Open Remote Desktop → connect → done!</p>
                """
                private_key_attachment = None  # No attachment for Windows
            else:
                html_body = f"""
                <h1>Welcome to EduCloud!</h1>
                <p>Hi {name.split()[0]}, your Linux VM is ready!</p>
                <p><b>IP:</b> {public_ip}</p>
                <h3>Connect with MobaXterm (super easy):</h3>
                <ol>
                    <li>Download the attached <b>educloud-key.pem</b></li>
                    <li>Open MobaXterm → New session → SSH</li>
                    <li>Remote host: <b>{public_ip}</b></li>
                    <li>Username: <b>ubuntu</b></li>
                    <li>Advanced tab → Use private key → select the downloaded .pem</li>
                    <li>Click OK → you are connected!</li>
                </ol>
                """
                # Prepare the private key attachment
                private_key_attachment = MIMEBase('application', 'x-pem-file')
                private_key_attachment.set_payload(private_key_pem.encode())
                encoders.encode_base64(private_key_attachment)
                private_key_attachment.add_header('Content-Disposition', 'attachment', filename='educloud-key.pem')

            # Create a MIME email
            msg = MIMEMultipart()
            msg['Subject'] = 'Your EduCloud VM is ready!'
            msg['From'] = 'no-reply@webuilders.lu'
            msg['To'] = email

            # Attach the HTML body
            msg.attach(MIMEText(html_body, 'html'))

            # Attach the private key if applicable
            if private_key_attachment:
                msg.attach(private_key_attachment)

            # Send the email using SES
            ses.send_raw_email(
                Source="no-reply@webuilders.lu",
                Destinations=[email],
                RawMessage={
                    'Data': msg.as_string()
                }
            )

            print(f"SUCCESS → {email} | {public_ip} | OS: {os_type}")

        except Exception as e:
            print(f"ERROR on row {i}: {e}")
            traceback.print_exc()

    return {"statusCode": 200}