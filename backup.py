import boto3
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.getenv('BASE_DIR')
BUCKET_NAME = os.getenv('BUCKET_NAME')

session = boto3.Session(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)
s3 = session.resource('s3')
s3_objects = {}

bucket = s3.Bucket(BUCKET_NAME)
for obj in bucket.objects.all():
    s3_objects[obj.key] = obj.last_modified

s3_keys = s3_objects.keys()

tz_offset = datetime.utcnow().timestamp() - datetime.now().timestamp() + 3600 * time.daylight

total_size = 0
total_size_collected = 0

for root, subdirs, files in os.walk(BASE_DIR):
    for file in files:
        f = os.path.join(root, file)
        f_local = f[len(BASE_DIR):].strip(os.path.sep)
        try:
            t_remote = time.mktime(s3_objects[f_local.replace('\\', '/')].timetuple())
        except KeyError:
            pass
        t_local = os.path.getmtime(f) + tz_offset
        if (not f_local.replace('\\', '/') in s3_keys):
            total_size += os.path.getsize(f)
        elif (t_remote < t_local):
            total_size += os.path.getsize(f)

storage_class = {
    'StorageClass': 'GLACIER'
}

for root, subdirs, files in os.walk(BASE_DIR):
    for file in files:
        f = os.path.join(root, file)
        this_size = os.path.getsize(f)
        f_local = f[len(BASE_DIR):].strip(os.path.sep)
        try:
            t_remote = time.mktime(s3_objects[f_local.replace('\\', '/')].timetuple())
        except KeyError:
            pass
        t_local = os.path.getmtime(f) + tz_offset
        if (f_local.endswith('.DS_Store') or '/__' in f_local.replace('\\', '/') or f_local.startswith('__')):
            # skip .DS_Store files and files/folders beginning with '__'
            pass
        elif (not f_local.replace('\\', '/') in s3_keys):
            # if file is not in s3
            total_size_collected += os.path.getsize(f)
            print('{}/{} adding:   {} ({})'.format(total_size_collected/1000000.0, total_size/1000000.0, f_local, this_size/1000000.0))
            s3.meta.client.upload_file(f, BUCKET_NAME, f_local.replace('\\', '/'), ExtraArgs=storage_class)
        elif (t_remote < t_local):
            # if local file is newer than remote file
            total_size_collected += os.path.getsize(f)
            print('{}/{} updating: {} ({})'.format(total_size_collected/1000000.0, total_size/1000000.0, f_local, this_size/1000000.0))
            s3.meta.client.upload_file(f, BUCKET_NAME, f_local.replace('\\', '/'), ExtraArgs=storage_class)
        else:
            print('{}/{} ok:       {} ({})'.format(total_size_collected/1000000.0, total_size/1000000.0, f_local, this_size/1000000.0))
