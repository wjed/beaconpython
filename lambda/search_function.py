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
    try:
        if 'body' not in event:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing request body"})}
        body = event['body']
        if isinstance(body, str):
            body = json.loads(body or '{}')
        query = body.get('query')
        if not query:
            return {"statusCode": 400, "body": json.dumps({"error": "'query' field required"})}

        bedrock = boto3.client("bedrock-runtime")
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v1",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": query}),
        )
        embed_body = json.loads(response["body"].read())
        embedding = embed_body.get("embedding", [])

        search_url = f"{OPENSEARCH_ENDPOINT}/{INDEX_NAME}/_search"
        payload = {
            "size": 3,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": embedding,
                        "k": 3
                    }
                }
            },
            "_source": ["text"]
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.get(search_url, auth=awsauth, json=payload, headers=headers)
        resp.raise_for_status()
        search_results = resp.json().get("hits", {}).get("hits", [])

        results = [
            {"text": hit.get("_source", {}).get("text", ""), "score": hit.get("_score")}
            for hit in search_results
        ]
        return {
            "statusCode": 200,
            "body": json.dumps({"results": results})
        }
    except Exception as e:
        print(f"Error processing search: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
