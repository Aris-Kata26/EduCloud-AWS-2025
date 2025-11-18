import boto3
import csv
from urllib.parse import unquote_plus

ec2 = boto3.resource('ec2')
ses = boto3.client('ses')

# Your Golden AMIs — Preserved
AMI = {
    'ubuntu': 'ami-0e86e20dae9224db8',   # Ubuntu 22.04 us-east-1
    'kali':   'ami-0c55b159cbfafe1f0',   # Replace with real Kali AMI if you have one
    'windows':'ami-0dfaa19c0e7d8d297'    # Windows Server 2022
}

# Security Group & Subnet (replace with yours)
SECURITY_GROUP = "sg-0123456789abcdef0"   # Your SG that allows SSH/RDP
SUBNET_ID = "subnet-0123456789abcdef0"    # Your public subnet

def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        # Download CSV
        obj = boto3.client('s3').get_object(Bucket=bucket, Key=key)
        rows = csv.DictReader(obj['Body'].read().decode('utf-8').splitlines())
        
        for row in rows:
            name = row['name'].strip()
            email = row['email'].strip().lower()
            os_type = row['os'].strip().lower()
            
            if os_type not in AMI:
                print(f"Invalid OS {os_type} for {name}")
                continue
            
            # Launch EC2 Instance
            try:
                instance = ec2.create_instances(
                    ImageId=AMI[os_type],
                    InstanceType='t3.medium' if os_type == 'windows' else 't3.micro',
                    MinCount=1, MaxCount=1,
                    KeyName='educloud-key',
                    SubnetId=SUBNET_ID,
                    SecurityGroupIds=[SECURITY_GROUP],
                    TagSpecifications=[{
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': f"EduCloud-{name}"},
                            {'Key': 'Student', 'Value': name},
                            {'Key': 'Email', 'Value': email},
                            {'Key': 'OS', 'Value': os_type},
                            {'Key': 'Project', 'Value': 'EduCloud-2025'}
                        ]
                    }]
                )[0]
                
                instance.wait_until_running()
                instance.reload()
                ip = instance.public_ip_address
                
                # Send Email Notification
                ses.send_email(
                    Source='no-reply@educloud.lu',  # Replace with a verified SES email
                    Destination={'ToAddresses': [email]},
                    Message={
                        'Subject': {'Data': 'Your EduCloud Lab is Ready!'},
                        'Body': {'Text': {'Data': f"Hi {name},\n\nYour {os_type.upper()} lab is ready!\nIP: {ip}\n\nConnect now!\n\n— EduCloud Team"}}
                    }
                )
                
                print(f"Launched {name} → {ip}")
            
            except Exception as e:
                print(f"Failed to launch instance for {name}: {str(e)}")
