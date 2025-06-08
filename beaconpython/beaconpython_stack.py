from aws_cdk import Aws, Stack, RemovalPolicy
from aws_cdk import aws_s3 as s3
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
                        "Principal": {"AWS": "*"},
                        "Action": "es:*",
                        "Resource": "*",
                    }
                ],
            },
        ).apply_removal_policy(RemovalPolicy.DESTROY)
