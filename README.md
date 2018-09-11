# Informed
1. The default requirements.txt will install CPU version, Change "requirements.txt" from "TensorFlow" to "TensorFlow-GPU" to Switch to GPU version
2. demo.py: An example of how to call a prediction method.

# Start
1. Install the python 3.6 environment 
2. pip install -r requirements.txt
3. Deploy as follows

## 1. Flask Version
1. Linux
    Deploy (Linux): gunicorn -c deploy.conf.py flask_server:app
    Port: 5000

2. Windows
    Deploy (Windows): python flask_server:app
    Port: 19951

## 2. G-RPC Version
Deploy: python3 grpc_server.py
Port: 50054


# Update G-RPC-CODE
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./grpc.proto


# Directory Structure

    - captcha_platform
        - grpc_server.py
        - flask_server.py
        - demo.py
    - model
        - ***Model.pb

# Introduction
https://www.jianshu.com/p/fccd596ef023


