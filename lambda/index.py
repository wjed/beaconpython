import os
import tempfile
import urllib.parse
import json
import boto3
import fitz  # PyMuPDF
import requests
from requests_aws4auth import AWS4Auth

s3_client = boto3.client('s3')

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
    for record in event.get('Records', []):
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, os.path.basename(key))
            s3_client.download_file(bucket, key, local_path)
            with fitz.open(local_path) as doc:
                text = "".join(page.get_text() for page in doc)

                # Truncate the extracted text to 8192 characters
                truncated = text[:8192]

                # Invoke the Amazon Titan embedding model via Bedrock
                bedrock = boto3.client("bedrock-runtime")
                response = bedrock.invoke_model(
                    modelId="amazon.titan-embed-text-v1",
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps({"inputText": truncated}),
                )

                body = json.loads(response["body"].read())
                embedding = body.get("embedding", [])

                # Log the length of the embedding vector and the first few values
                print(
                    f"Embedding length: {len(embedding)}; first values: {embedding[:5]}"
                )

                if OPENSEARCH_ENDPOINT:
                    doc_id = urllib.parse.quote(key, safe="")
                    url = f"{OPENSEARCH_ENDPOINT}/{INDEX_NAME}/_doc/{doc_id}"
                    payload = {"text": truncated, "embedding": embedding}
                    headers = {"Content-Type": "application/json"}
                    response = requests.put(url, auth=awsauth, json=payload, headers=headers)
                    response.raise_for_status()
                    print(
                        f"Indexed {doc_id} into OpenSearch with status {response.status_code}"
                    )
    return {'statusCode': 200}
