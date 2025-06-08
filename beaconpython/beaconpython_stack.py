from aws_cdk import Aws, Stack, RemovalPolicy
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_opensearchservice as opensearch
from constructs import Construct

class BeaconpythonStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket to store certification materials
        # Bucket name includes the account ID for uniqueness
        materials_bucket = s3.Bucket(
            self,
            "CertificationMaterialsBucket",
            bucket_name=f"certification-materials-{Aws.ACCOUNT_ID}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
        )

        # OpenSearch domain for storing embeddings
        opensearch.CfnDomain(
            self,
            "CertificationAssistantSearch",
            domain_name="cert-assistant-search",
            engine_version="OpenSearch_2.5",
            cluster_config=opensearch.CfnDomain.ClusterConfigProperty(
                instance_type="t3.small.search",
                instance_count=1,
            ),
            ebs_options=opensearch.CfnDomain.EBSOptionsProperty(
                ebs_enabled=True,
                volume_size=10,
                volume_type="gp3",
            ),
            access_policies={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": f"arn:aws:iam::{Aws.ACCOUNT_ID}:root"},
                        "Action": "es:*",
                        "Resource": "*",
                    }
                ],
            },
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # Inline Lambda to process new uploads
        ingest_function = _lambda.Function(
            self,
            "IngestFunction",
            function_name="IngestFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.InlineCode(
                "import boto3\n"
                "import logging\n"
                "import fitz\n"
                "\n"
                "s3 = boto3.client('s3')\n"
                "logger = logging.getLogger()\n"
                "logger.setLevel(logging.INFO)\n"
                "\n"
                "def handler(event, context):\n"
                "    for record in event.get('Records', []):\n"
                "        bucket = record['s3']['bucket']['name']\n"
                "        key = record['s3']['object']['key']\n"
                "        logger.info(f'New object: {key} in bucket: {bucket}')\n"
                "        obj = s3.get_object(Bucket=bucket, Key=key)\n"
                "        data = obj['Body'].read()\n"
                "        if key.lower().endswith('.pdf'):\n"
                "            doc = fitz.open(stream=data, filetype='pdf')\n"
                "            text = ''.join(page.get_text() for page in doc)\n"
                "            logger.info('Extracted text: %s', text[:1000])\n"
                "        else:\n"
                "            logger.info('Unsupported file type for key %s', key)\n"
            ),
        )

        # Allow the function to read from the materials bucket
        materials_bucket.grant_read(ingest_function)

        # Trigger the function when new objects are created
        materials_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(ingest_function),
        )

