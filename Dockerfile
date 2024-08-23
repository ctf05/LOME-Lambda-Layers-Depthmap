# Commands:
# docker build --no-cache --target tester -t lambda-layer-tester .
# docker build -t lambda-layer-builder .
# docker run --rm -v %cd%:/opt lambda-layer-builder

# Use the latest AWS Lambda Python runtime as the base image
FROM public.ecr.aws/lambda/python:3.11-x86_64 AS builder

# Set the working directory in the container
WORKDIR /var/task

# Install system dependencies and build dependencies
RUN yum install -y \
        git unzip wget tar gzip xz zip \
    yum clean all && \
    rm -rf /var/cache/yum

# Clone your Git repository
RUN git clone https://github.com/ctf05/LOME-Lambda-Layers-Depthmap.git .

# Create the directory structure for the Lambda layer
RUN mkdir -p /opt/python

# Copy the needed files and directories, including the broken_source-0.5.0.dist-info folder
RUN cp -r DepthFlow ShaderFlow Broken broken_source-0.5.0.dist-info glfw /opt/python/ && \
    cp pyproject.toml requirements.txt test.py /opt/python/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install \
    --no-cache-dir \
    --platform manylinux2014_x86_64 \
    --target=/opt/python \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    -r requirements.txt

# Download and install FFmpeg
RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar xJf ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg-*-amd64-static/ffmpeg /opt/python/ && \
    rm -rf ffmpeg-release-amd64-static*

# Remove unnecessary files
RUN find /opt/python -type d -name '__pycache__' -exec rm -rf {} + && \
    find /opt/python -type f -name '*.pyc' -delete && \
    find /opt/python -type f -name '*.pyo' -delete && \
    find /opt/python -type d -name 'tests' -exec rm -rf {} +

# Run the dev import
RUN python -c "import sys; sys.path.append('/opt/python'); print('Python version:', sys.version); print('Python path:', sys.path); from DepthFlow import DepthScene; print('Import successful on dev branch!')"

# Create the ZIP file with maximum compression
RUN cd /opt && zip -r9 /tmp/lambda-layer.zip python

# Create a new stage for testing. This is a more accurate enviroment of AWS Lambda
FROM public.ecr.aws/lambda/python:3.11-x86_64 AS tester

# Install system dependencies and build dependencies
RUN yum install -y \
        unzip && \
    yum clean all && \
    rm -rf /var/cache/yum

# Copy zip from the builder stage
COPY --from=builder /tmp/lambda-layer.zip /tmp/lambda-layer.zip

# Unzip the Lambda layer to /opt
RUN unzip /tmp/lambda-layer.zip -d /opt && rm /tmp/lambda-layer.zip

# Copy everything from the builder stage
#COPY --from=builder /usr/lib64 /opt/python/usr/lib64

# Set up the test environment
ENV PYTHONPATH=/opt/python:/var/runtime:/var/lang/lib/python3.11/site-packages:/var/lang/lib/python3.11/site-packages/cv2/python-3.11:/opt/python/usr/lib/python3.11/site-packages
ENV LD_LIBRARY_PATH=/opt/python/usr/lib:/opt/python/usr/lib64:/var/lang/lib:/lib64:/usr/lib64:/var/runtime:/var/runtime/lib:/var/task:/var/task/lib:/opt/lib

# Run the test import
RUN python -c "import sys; sys.path.append('/opt/python'); print('Python version:', sys.version); print('Python path:', sys.path); from DepthFlow import DepthScene; print('Import successful on test branch!')"

# Use a minimal base image for the final stage
FROM alpine:latest

# Copy the ZIP file from the builder stage
COPY --from=builder /tmp/lambda-layer.zip /DepthFlow.zip

# Set the entrypoint to copy the ZIP file to the mounted volume
ENTRYPOINT ["/bin/sh", "-c", "cp /DepthFlow.zip /opt/ && echo 'Lambda layer ZIP file created successfully.' && echo 'ZIP file size:' && du -h /opt/DepthFlow.zip"]