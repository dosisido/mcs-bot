FROM python:3.14-slim

WORKDIR /app

COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

COPY log4j_bridge.xml /log4j_conf/

CMD ["python", "main.py"]