import boto3
from app.config import get_settings

settings = get_settings()

session = boto3.Session(region_name=settings.aws_region)

s3_client = session.client("s3")
dynamodb = session.resource("dynamodb")
learner_table = dynamodb.Table(settings.learner_table)