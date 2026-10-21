# CPU environment for the analysis scripts and tools. The recorded runs used a container based on the NVIDIA CUDA 12.1.1
# image with Python 3.10.13, NumPy 1.26.3 and pandas 2.2.3 (each run's provenance.json records Python and NumPy); no GPU
# is needed. For the post-hoc scripts also install requirements-posthoc.txt.
FROM python:3.10.13-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
ENV MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /repo
