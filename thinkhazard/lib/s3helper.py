import boto3
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
        self.s3_client.upload_file(file_name, self.bucket, object_name)

    def upload_fileobj(self, data, object_name):
        self.s3_client.upload_fileobj(data, self.bucket, object_name)

    def download_file(self, object_name, file_name=None):
        # If S3 file_name was not specified, use object_name
        if file_name is None:
            file_name = object_name
        self.s3_client.download_file(self.bucket, object_name, file_name)

    def delete_object(self, object_name):
        self.s3_client.delete_object(Bucket=self.bucket, Key=object_name)

    def get_object_url(self, object_name):
        """Generate S3 URL for an object."""
        return f"s3://{self.bucket}/{object_name}"

    def object_exists(self, object_name):
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=object_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # File doesn't exist
                return False
            raise

    def list_objects(self, prefix=""):
        """List objects in the bucket with a given prefix.

        Returns a list of dicts with 'Key', 'LastModified', and 'Size'.
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            objects = response.get('Contents', [])
            return [
                {
                    'Key': obj['Key'],
                    'LastModified': obj['LastModified'],
                    'Size': obj['Size']
                }
                for obj in objects
            ]
        except ClientError:
            return []
