import boto3
import logging
from botocore.client import Config
from botocore.exceptions import ClientError

class S3Helper:
    def __init__(self, bucket, **kwargs):
        self.s3_client = boto3.client('s3',
            **kwargs,
            config=Config(signature_version='s3v4'),
            region_name='eu-west-1'
        )
        self.bucket = bucket

    def upload_file(self, file_name, object_name=None):
        # If S3 object_name was not specified, use file_name
        if object_name is None:
            object_name = file_name

        try:
            response = self.s3_client.upload_file(file_name, self.bucket, object_name)
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def download_file(self, object_name, file_name=None):
        # If S3 file_name was not specified, use object_name
        if file_name is None:
            file_name = object_name

        try:
            response = self.s3_client.download_file(self.bucket, object_name, file_name)
        except ClientError as e:
            logging.error(e)
            return False
        return True
