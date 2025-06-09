import os
import json
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
    # Expect JSON payload like {"query": "your question"}
    try:
        payload = event.get("body") if isinstance(event.get("body"), str) else event
        body = json.loads(payload) if isinstance(payload, str) else payload
    except Exception:
        body = {}

    query = body.get("query")
    if not query:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Query parameter is required"}),
        }

    bedrock = boto3.client("bedrock-runtime")
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v1",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": query}),
    )

    embedding = json.loads(response["body"].read()).get("embedding", [])

    search_url = f"{OPENSEARCH_ENDPOINT}/{INDEX_NAME}/_search"
    headers = {"Content-Type": "application/json"}
    search_body = {
        "size": 3,
        "query": {"knn": {"embedding": {"vector": embedding, "k": 3}}},
        "_source": ["text"],
    }

    search_response = requests.get(
        search_url,
        auth=awsauth,
        headers=headers,
        data=json.dumps(search_body),
    )
    search_response.raise_for_status()
    results_json = search_response.json()
    hits = results_json.get("hits", {}).get("hits", [])
    results = [
        {
            "id": hit.get("_id"),
            "score": hit.get("_score"),
            "text": hit.get("_source", {}).get("text"),
        }
        for hit in hits
    ]

    return {
        "statusCode": 200,
        "body": json.dumps({"results": results}),
    }
