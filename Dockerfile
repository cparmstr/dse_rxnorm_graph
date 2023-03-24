FROM python:3.11-slim-buster as baseiine
RUN apt update && apt install unzip -y
WORKDIR /rxnorm
COPY awscliv2.zip .
RUN unzip awscliv2.zip
RUN ./aws/install

ARG AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ARG AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ARG AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}
RUN echo ${AWS_ACCESS_KEY_ID}

COPY dev-requirements.txt /rxnorm/dev-requirements.txt
RUN aws codeartifact login --tool pip --repository mw-data-dev --domain mw-data-dev --domain-owner 493679001282 --region us-west-2
RUN /usr/local/bin/pip install -r /rxnorm/dev-requirements.txt

CMD ["python", "read_rrf.py"]
