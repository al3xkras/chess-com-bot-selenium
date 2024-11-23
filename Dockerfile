FROM python:3.10-slim
WORKDIR /app
RUN apt-get update
RUN apt-get install -y wget tar 
RUN wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-ubuntu-x86-64.tar
RUN tar -xvf stockfish-ubuntu-x86-64.tar && mv stockfish/stockfish-ubuntu-x86-64 stockfish/stockfish
RUN rm stockfish-ubuntu-x86-64.tar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get clean
COPY main.py main.py
COPY docker/main.sh main.sh
RUN chmod a+x /app/main.sh /app/main.py
ENTRYPOINT ["bash", "-c", "/app/main.sh"]
