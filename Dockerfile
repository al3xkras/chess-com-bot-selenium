FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y wget tar && \
    apt-get clean

RUN useradd -m -G users chess_user
USER chess_user
WORKDIR /app

RUN wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-ubuntu-x86-64.tar && \
    tar -xvf stockfish-ubuntu-x86-64.tar && mv stockfish/stockfish-ubuntu-x86-64 stockfish/stockfish && \
    rm stockfish-ubuntu-x86-64.tar

COPY requirements.txt .
RUN pip install virtualenv && \
    python -m virtualenv venv && \
    venv/bin/pip install --no-cache-dir -r requirements.txt

USER root
COPY main.py docker/main.sh ./
RUN chown -hR chess_user:chess_user /app/main.sh /app/main.py && \
    chmod a+x /app/main.sh /app/main.py
USER chess_user

ENTRYPOINT ["bash", "-c", "/app/main.sh"]
