FROM python:3.6.8-stretch as builder

EXPOSE 19952

WORKDIR /app/

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python3", "tornado_server.py"]
