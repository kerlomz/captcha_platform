FROM python:3.7-slim as builder

ADD . /app

WORKDIR /app

RUN apt update && apt install -y --no-install-recommends libgl1 libglib2.0-0 && \
      rm -rf /var/lib/apt/lists/* && \
      pip install --no-cache-dir --upgrade pip && \
      pip install --no-cache-dir -r requirements.txt

VOLUME ["/app/graph", "/app/model"]
EXPOSE 19952

ENTRYPOINT ["python3", "tornado_server.py"]

# run command:
# docker run -dit --name captcha \
# -e TZ="$(cat /etc/timezone)" \
# -v $PWD/graph:/app/graph \
# -v $PWD/model:/app/model \
# -p 19952:19952 \
# [image:tag]
