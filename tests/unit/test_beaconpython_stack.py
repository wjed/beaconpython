import aws_cdk as core
import aws_cdk.assertions as assertions

from beaconpython.beaconpython_stack import BeaconpythonStack

# example tests. To run these tests, uncomment this file along with the example
# resource in beaconpython/beaconpython_stack.py
def test_opensearch_domain_created():
    app = core.App()
    stack = BeaconpythonStack(app, "beaconpython")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::OpenSearchService::Domain",
        {
            "DomainName": "cert-assistant-search",
            "EngineVersion": "OpenSearch_2.5",
            "ClusterConfig": {
                "InstanceType": "t3.small.search",
                "InstanceCount": 1
            },
            "EBSOptions": {
                "EBSEnabled": True,
                "VolumeSize": 10,
                "VolumeType": "gp3"
            }
        },
    )


def test_ingest_lambda_created():
    app = core.App()
    stack = BeaconpythonStack(app, "beaconpython")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "PackageType": "Image",
            "FunctionName": "IngestFunction",
        },
    )


def test_search_lambda_created():
    app = core.App()
    stack = BeaconpythonStack(app, "beaconpython")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "PackageType": "Image",
            "FunctionName": "SearchFunction",
        },
    )
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "FunctionName": "SearchFunction",
            "VpcConfig": assertions.Match.absent(),
        },
    )


def test_api_gateway_created():
    app = core.App()
    stack = BeaconpythonStack(app, "beaconpython")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::ApiGateway::RestApi", 1)
