FROM amazon/aws-lambda-python:3.12

# Install dependencies
RUN pip install PyMuPDF requests requests_aws4auth

# Copy function code for all Lambdas in this image
COPY index.py search_function.py ${LAMBDA_TASK_ROOT}

CMD ["index.handler"]
