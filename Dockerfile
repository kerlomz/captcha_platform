FROM python:3.6.8-stretch as builder

ADD . /app/

WORKDIR /app/

COPY requirements.txt /app/

# timezone
ENV TZ=Asia/Shanghai

RUN pip install --no-cache-dir --upgrade pip \
     && pip install --no-cache-dir -r requirements.txt


ENTRYPOINT ["python3", "tornado_server.py"]
EXPOSE 19952
# run command:
# docker run -d -p 19952:19952 [image:tag]
