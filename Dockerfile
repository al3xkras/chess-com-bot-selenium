FROM python:3.10
WORKDIR /app
RUN wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-ubuntu-x86-64.tar
RUN tar -xvf stockfish-ubuntu-x86-64.tar && mv stockfish/stockfish-ubuntu-x86-64 stockfish/stockfish
RUN rm stockfish-ubuntu-x86-64.tar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY docker/main.sh .
ENTRYPOINT ["bash", "-c", "/app/main.sh"]
