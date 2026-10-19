# Python environment of the recorded runs (Python 3.10.13; package versions in requirements.txt)
FROM python:3.10.13-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
ENV MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /repo
