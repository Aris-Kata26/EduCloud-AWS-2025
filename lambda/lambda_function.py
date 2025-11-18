import boto3, csv, os
from urllib.parse import unquote_plus

s3 = boto3.client('s3')
ec2 = boto3.resource('ec2')
ses = boto3.client('ses', region_name='us-east-1')

def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        if not key.startswith('uploads/'): continue
        
        obj = s3.get_object(Bucket=bucket, Key=key)
        for row in csv.DictReader(obj['Body'].read().decode('utf-8').splitlines()):
            name, email, os = row['name'], row['email'], row['os'].lower()
            
            instance = ec2.create_instances(
                ImageId='ami-0e86e20dae9224db8' if 'ubuntu' in os else 'ami-0c55b159cbfafe1f0' if 'kali' in os else 'ami-0dfaa19c0e7d8d297',
                InstanceType='t3.micro',
                MinCount=1, MaxCount=1,
                TagSpecifications=[{'ResourceType':'instance','Tags':[{'Key':'Name','Value':f'EduCloud-{name}'}]}]
            )[0]
            
            instance.wait_until_running()
            instance.reload()
            
            ses.send_email(
                Source='katar711@school.lu',
                Destination={'ToAddresses':[email]},
                Message={'Subject':{'Data':'Your EduCloud Lab is Ready!'},
                         'Body':{'Text':{'Data':f"Hi {name},\n\nYour {os.upper()} lab is ready!\nIP: {instance.public_ip_address}\n\n— Ahmed & Aristide"}}}
            )
    return {'statusCode': 200}
