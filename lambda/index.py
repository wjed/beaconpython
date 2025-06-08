import os
import tempfile
import urllib.parse
import boto3
import fitz  # PyMuPDF

s3_client = boto3.client('s3')


def handler(event, context):
    for record in event.get('Records', []):
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, os.path.basename(key))
            s3_client.download_file(bucket, key, local_path)
            with fitz.open(local_path) as doc:
                text = "".join(page.get_text() for page in doc)
                print(text)
    return {'statusCode': 200}
