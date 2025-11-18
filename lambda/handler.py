# lambda/handler.py — FINAL & COMPLETE (EC2 launch + SES email like VM Bridge)
import json
import boto3
import csv
from io import StringIO
import pymysql
import os
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
ec2 = boto3.resource('ec2')
ses = boto3.client('ses')
conn = pymysql.connect(
    host=os.environ['RDS_ENDPOINT'],
    user=os.environ['RDS_USER'],
    password=os.environ['RDS_PASSWORD'],
    database=os.environ['RDS_DB']
)
cur = conn.cursor()

# Your Golden AMIs — Preserved
AMI_MAP = {
    'ubuntu': 'ami-0e86e20dae9224db8',   # Ubuntu 22.04 us-east-1
    'kali':   'ami-0c55b159cbfafe1f0',   # Replace with real Kali AMI if you have one
    'windows':'ami-0dfaa19c0e7d8d297'    # Windows Server 2022
}
SECURITY_GROUP = "sg-0xxxxxxxxxxxxxxx"
SUBNET_ID = "subnet-0xxxxxxxxxxxxxxx"

# BEAUTIFUL EMAIL TEMPLATE — EXACTLY LIKE VM BRIDGE
HTML_EMAIL = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Your EduCloud VM</title></head>
<body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px;">
<div style="max-width: 600px; margin: auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 0 20px rgba(0,0,0,0.1);">
  <div style="background: #0c2e4a; color: #00ff99; padding: 30px; text-align: center;">
    <h1>Assigned Virtual Machine</h1>
  </div>
  <div style="padding: 30px; line-height: 1.8; color: #333;">
    <p>Dear <strong>{name}</strong>,</p>
    <p>Below are the details of your assigned virtual machine for the <strong>{class_name}</strong> class:</p>
    <p>VM Name:<br><strong>{name}</strong></p>
    <p>OS Type:<br><strong>{os_type}</strong></p>
    <p>IP Address:<br><span style="font-size: 24px; font-weight: bold; color: #00ff99;">{ip}</span></p>
    <p>Username:<br><strong>{username}</strong></p>
    <p>Password:<br><strong>{password}</strong></p>

    <hr style="margin: 30px 0; border: 1px dashed #ddd;">
    <h3>How to Access Your VM</h3>
    <p>Use <strong>MobaXterm</strong> (free SSH/RDP client):</p>
    <ul>
      <li>Download from <a href="https://mobaxterm.mobatek.net">mobaxterm.mobatek.net</a></li>
      <li>For Ubuntu/Kali: Session → SSH → IP: <strong>{ip}</strong> → Username: <strong>{username}</strong></li>
      <li>For Windows: Session → RDP → IP: <strong>{ip}</strong> → Username: Administrator</li>
    </ul>

    <h3>Important Reminders</h3>
    <ul>
      <li>Do not install unnecessary software</li>
      <li>Your activity may be monitored</li>
      <li>Contact your instructor if connection issues</li>
    </ul>

    <p>Best regards,<br><strong>Your Instructor</strong></p>
  </div>
  <div style="background: #0c2e4a; color: #88ddff; padding: 20px; text-align: center; font-size: 14px;">
    EduCloud • BTS Luxembourg • Ahmed Al-Asadi & Aristide Katagaruka – B1CLC 2025
  </div>
</div>
</body>
</html>"""

def send_email(name, email, class_name, os_type, ip):
    username = "ubuntu" if os_type == "ubuntu" else "kali" if os_type == "kali" else "Administrator"
    password = "ubuntu" if os_type in ["ubuntu", "kali"] else "Check AWS Console → Get Windows Password"
    
    ses.send_email(
        Source="no-reply@educloud.lu",
        Destination={'ToAddresses': [email]},
        Message={
            'Subject': {'Data': 'Your EduCloud Virtual Machine is Ready!'},
            'Body': {
                'Html': {'Data': HTML_EMAIL.format(
                    name=name, class_name=class_name, os_type=os_type.title(),
                    ip=ip, username=username, password=password
                )}
            }
        }
    )
    print(f"Email sent to {email}")

def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['943']['bucket']['name']
        key = record['s3']['object']['key']
        
        obj = s3.get_object(Bucket=bucket, Key=key)
        reader = csv.DictReader(StringIO(obj['Body'].read().decode('utf-8')))
        
        for row in reader:
            name = row['name'].strip()
            email = row['email'].strip().lower()
            class_name = row['class'].strip()
            os_type = row['os'].strip().lower()
            
            if os_type not in AMI_MAP: continue
            
            # Launch EC2
            instances = ec2.create_instances(
                ImageId=AMI_MAP[os_type],
                InstanceType='t3.medium' if 'windows' in os_type else 't3.micro',
                MinCount=1, MaxCount=1,
                KeyName='educloud-key',
                SubnetId=SUBNET_ID,
                SecurityGroupIds=[SECURITY_GROUP],
                TagSpecifications=[{'ResourceType': 'instance', 'Tags': [
                    {'Key': 'Name', 'Value': f"EduCloud-{name}"},
                    {'Key': 'Student', 'Value': name},
                    {'Key': 'Email', 'Value': email},
                    {'Key': 'Class', 'Value': class_name}
                ]}]
            )
            instance = instances[0]
            instance.wait_until_running()
            instance.reload()
            
            # Save to RDS
            cur.execute("""UPDATE assignments SET instance_id=%s, public_ip=%s, sent=1 
                           WHERE student_id=(SELECT id FROM students WHERE email=%s)""",
                        (instance.instance_id, instance.public_ip_address, email))
            conn.commit()
            
            # SEND THE BEAUTIFUL EMAIL
            send_email(name, email, class_name, os_type, instance.public_ip_address)
    
    return {'statusCode': 200}