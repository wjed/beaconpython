from aws_cdk import Aws, Stack, RemovalPolicy
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_opensearchservice as opensearch
from aws_cdk import aws_iam as iam
from aws_cdk import aws_apigateway as apigateway
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
        domain = opensearch.CfnDomain(
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
        )
        domain.apply_removal_policy(RemovalPolicy.DESTROY)

        # Docker-based Lambda to process new uploads
        ingest_function = _lambda.DockerImageFunction(
            self,
            "IngestFunction",
            function_name="IngestFunction",
            code=_lambda.DockerImageCode.from_image_asset("lambda"),
        )

        ingest_function.add_environment(
            "OPENSEARCH_ENDPOINT", f"https://{domain.attr_domain_endpoint}"
        )

        # Allow the function to call Amazon Bedrock for embeddings
        ingest_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"]
            )
        )

        ingest_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["es:ESHttpPut"],
                resources=[
                    f"arn:aws:es:{Aws.REGION}:{Aws.ACCOUNT_ID}:domain/cert-assistant-search/*"
                ],
            )
        )

        # Allow the function to read from the materials bucket
        materials_bucket.grant_read(ingest_function)

        # Trigger the function when new objects are created
        materials_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(ingest_function),
        )

        # Docker-based Lambda to handle search queries
        search_function = _lambda.DockerImageFunction(
            self,
            "SearchFunction",
            function_name="SearchFunction",
            code=_lambda.DockerImageCode.from_image_asset(
                "lambda",
                cmd=["search_function.handler"],
            ),
            environment={
                "OPENSEARCH_ENDPOINT": f"https://{domain.attr_domain_endpoint}"
            },
        )

        # Permissions for Bedrock and OpenSearch
        search_function.add_to_role_policy(
            iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=["*"])
        )
        search_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["es:ESHttpPost", "es:ESHttpGet"],
                resources=[
                    f"arn:aws:es:{Aws.REGION}:{Aws.ACCOUNT_ID}:domain/cert-assistant-search/*"
                ],
            )
        )

        # API Gateway exposing the search endpoint
        api = apigateway.RestApi(self, "StudyAssistantApi")
        search_integration = apigateway.LambdaIntegration(search_function)
        search_resource = api.root.add_resource("search")
        search_resource.add_method("POST", search_integration)

