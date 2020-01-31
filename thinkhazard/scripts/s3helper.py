import boto3
import logging
from botocore.client import Config
from botocore.exceptions import ClientError

class S3Helper:
    def __init__(self, **kwargs):
        self.s3_client = boto3.client('s3',
            **kwargs,
            config=Config(signature_version='s3v4'),
            region_name='paris'
        )

    def bucket_exists(self, bucket_name):
        buckets = self.s3_client.list_buckets()
        for bucket in buckets['Buckets']:
            if bucket["Name"] == bucket_name:
                return True
        return False

    def create_bucket(self, bucket_name):
        try:
            self.s3_client.create_bucket(Bucket=bucket_name)
        except ClientError as e:
            logging.error(e)
            return False
        return True
        
    def upload_file(self, file_name, bucket, object_name=None):
        # If S3 object_name was not specified, use file_name
        if object_name is None:
            object_name = file_name

        try:
            response = self.s3_client.upload_file(file_name, bucket, object_name)
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def download_file(self, bucket, object_name, file_name=None):
        # If S3 file_name was not specified, use object_name
        if file_name is None:
            file_name = object_name

        try:
            response = self.s3_client.download_file(bucket, object_name, file_name)
        except ClientError as e:
            logging.error(e)
            return False
        return True