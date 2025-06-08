FROM amazon/aws-lambda-python:3.12

RUN pip install requests requests_aws4auth

COPY query.py ${LAMBDA_TASK_ROOT}

CMD ["query.handler"]
