import boto3
import logging
from botocore.client import Config
from botocore.exceptions import ClientError


class S3Helper:
    def __init__(self, settings):
        # boto generates endpoint_url for AWS if left empty
        kwargs = ({}
                  if settings["aws_endpoint_url"] == ""
                  else {"endpoint_url": settings["aws_endpoint_url"]})
        self.s3_client = boto3.client('s3',
                                      **kwargs,
                                      aws_access_key_id=settings["aws_access_key_id"],
                                      aws_secret_access_key=settings["aws_secret_access_key"],
                                      config=Config(signature_version='s3v4'),
                                      region_name='eu-west-1'
                                      )
        self.bucket = settings["aws_bucket_name"]

    def upload_file(self, file_name, object_name=None):
        # If S3 object_name was not specified, use file_name
        if object_name is None:
            object_name = file_name

        try:
            self.s3_client.upload_file(file_name, self.bucket, object_name)
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def download_file(self, object_name, file_name=None):
        # If S3 file_name was not specified, use object_name
        if file_name is None:
            file_name = object_name

        try:
            self.s3_client.download_file(self.bucket, object_name, file_name)
        except ClientError as e:
            logging.error(e)
            return False
        return True
