from aws_cdk import Aws, Stack
from aws_cdk import aws_s3 as s3
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
