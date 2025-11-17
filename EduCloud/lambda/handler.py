import boto3
import csv
from urllib.parse import unquote_plus

ec2 = boto3.resource('ec2')
ses = boto3.client('ses')

AMI = {
    'ubuntu': 'ami-0e86e20dae9224db8',   # Ubuntu 22.04 us-east-1
    'kali':   'ami-0c55b159cbfafe1f0',   # Replace with real Kali AMI if you have one
    'windows':'ami-0dfaa19c0e7d8d297'    # Windows Server 2022
}

def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        obj = boto3.client('s3').get_object(Bucket=bucket, Key=key)
        rows = csv.DictReader(obj['Body'].read().decode('utf-8').splitlines())
        
        for row in rows:
            name = row['name']
            email = row['email']
            os_type = row['os'].lower()
            
            instance = ec2.create_instances(
                ImageId=AMI.get(os_type, AMI['ubuntu']),
                InstanceType='t3.micro',
                MinCount=1, MaxCount=1,
                TagSpecifications=[{'ResourceType':'instance','Tags':[{'Key':'Name','Value':f"EduCloud-{name}"}]}]
            )[0]
            
            instance.wait_until_running()
            instance.reload()
            ip = instance.public_ip_address
            
            ses.send_email(
                Source='no-reply@educloud.lu',  # ← we will verify this in 30 seconds
                Destination={'ToAddresses':[email]},
                Message={
                    'Subject': {'Data': 'Your EduCloud Lab is Ready!'},
                    'Body': {'Text': {'Data': f"Hi {name},\n\nYour {os_type.upper()} lab is ready!\nIP: {ip}\n\nConnect now!\n\n— EduCloud Team\nAhmed & Aristide"}}
                }
            )
