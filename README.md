# Project Introduction
This project is based on CNN+LSTM+CTC to realize verification code identification. 
This project is only for deployment models, If you need to train the model, please move to https://github.com/kerlomz/captcha_trainer

# Informed
1. The default requirements.txt will install CPU version, Change "requirements.txt" from "TensorFlow" to "TensorFlow-GPU" to Switch to GPU version, Use the GPU version to install the corresponding CUDA and cuDNN.
2. demo.py: An example of how to call a prediction method.
3. The model folder folder is used to store model configuration files such as model.yaml.
4. The graph folder is used to store compiled models such as model.pb
5. The deployment service will automatically load all the models in the model configuration. When a new model configuration is added, the corresponding compilation model in the graph folder will be automatically loaded, so if you need to add it, please copy the corresponding compilation model to the graph path first, then add the model configuration.


# Start
1. Install the python 3.6 environment (with pip)
2. Install virtualenv ```pip3 install virtualenv```
3. Create a separate virtual environment for the project:
    ```bash
    virtualenv -p /usr/bin/python3 venv # venv is the name of the virtual environment.
    cd venv/ # venv is the name of the virtual environment.
    source bin/activate # to activate the current virtual environment.
    cd captcha_platform # captcha_platform is the project path.
    ```
4. ```pip install -r requirements.txt```
5. Copy a config_demo.yaml to the same directory named config.yaml
6. Place your trained model.yaml in model folder, and your model.pb in graph folder (create if not exist)
7. Deploy as follows.

## 1. Http Version
1. Linux
    Deploy (Linux/Mac): 

    1. Port: 5000
    ```
    pip install gunicorn
    gunicorn -c deploy.conf.py flask_server:app
    ```
    2. Port: 19951
    ```
    python flask_server.py
    ```
    3. Port: 19952
    ```
    python tornado_server.py
    ```

2. Windows
    Deploy (Windows): 
    ```
    python flask_server.py
    ```
    Port: 19951

## 2. G-RPC Version
Deploy: 
```
python3 grpc_server.py
```
Port: 50054


# Update G-RPC-CODE
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./grpc.proto


# Directory Structure

    - captcha_platform
        - grpc_server.py
        - flask_server.py
        - tornado_server.py
        - demo.py
    - model
        - model-1.yaml
        - model-2.yaml
        - ...
    - graph
        - Model-1.pb
        - ...

# License
This project use SATA License (Star And Thank Author License), so you have to star this project before using. Read the license carefully.

# Introduction
https://www.jianshu.com/p/fccd596ef023


