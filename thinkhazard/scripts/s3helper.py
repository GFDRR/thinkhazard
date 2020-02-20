import boto3
import logging
from botocore.client import Config
from botocore.exceptions import ClientError

class S3Helper:
    def __init__(self, **kwargs):
        self.s3_client = boto3.client('s3',
            **kwargs,
            config=Config(signature_version='s3v4'),
            region_name='eu-west-1'
        )

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