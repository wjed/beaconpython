import json
import os

import boto3
import requests
from requests_aws4auth import AWS4Auth

session = boto3.Session()
credentials = session.get_credentials()
region = session.region_name or os.environ.get("AWS_REGION", "us-east-1")
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    region,
    "es",
    session_token=credentials.token,
)

OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT")
INDEX_NAME = "cert-study-index"


def handler(event, context):
    question = "What is AWS IAM?"
    bedrock = boto3.client("bedrock-runtime")
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v1",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": question}),
    )

    body = json.loads(response["body"].read())
    vector = body.get("embedding", [])

    search_query = {
        "size": 3,
        "query": {
            "knn": {"embedding": {"vector": vector, "k": 3}}
        },
        "_source": ["text"],
    }

    url = f"{OPENSEARCH_ENDPOINT}/{INDEX_NAME}/_search"
    r = requests.post(url, auth=awsauth, json=search_query, headers={"Content-Type": "application/json"})
    r.raise_for_status()
    results = r.json()

    for hit in results.get("hits", {}).get("hits", []):
        print(hit.get("_source", {}).get("text"))

    return {"statusCode": 200}
