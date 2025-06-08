import aws_cdk as core
import aws_cdk.assertions as assertions

from beaconpython.beaconpython_stack import BeaconpythonStack

# example tests. To run these tests, uncomment this file along with the example
# resource in beaconpython/beaconpython_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = BeaconpythonStack(app, "beaconpython")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
