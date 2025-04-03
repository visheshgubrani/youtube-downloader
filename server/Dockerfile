FROM python:3.13.2-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app 

COPY ./requirements.txt /app/requirements.txt 

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt 

COPY src /app/src
COPY main.py /app/main.py


CMD [ "fastapi", "run", "main.py", "--port", "8000" ]
