# Use the AWS Lambda Python runtime as the base image
FROM public.ecr.aws/lambda/python:3.9

# Set the working directory in the container
WORKDIR /var/task

# Install git, unzip, wget, tar, xz, and zip
RUN yum update -y && \
    yum install -y git unzip wget tar gzip xz zip

# Clone your Git repository
RUN git clone https://github.com/ctf05/LOME-Lambda-Layers-Depthmap.git .

# Create the directory structure for the Lambda layer
RUN mkdir -p /opt/python

# Copy the needed files and directories
RUN cp -r DepthFlow ShaderFlow Broken /opt/python/ && \
    cp pyproject.toml requirements.txt test.py /opt/python/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt -t /opt/python

# Download and install FFmpeg
RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar xJf ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg-*-amd64-static/ffmpeg /opt/python/ && \
    rm -rf ffmpeg-release-amd64-static*

# Set the working directory to /opt
WORKDIR /opt

# Create the ZIP file
RUN zip -r9 /tmp/lambda-layer.zip python

# Use a minimal base image for the final stage
FROM alpine:latest

# Copy the ZIP file from the previous stage
COPY --from=0 /tmp/lambda-layer.zip /DepthFlow.zip

# Set the entrypoint to copy the ZIP file to the mounted volume
ENTRYPOINT ["/bin/sh", "-c", "cp /DepthFlow.zip /opt/ && echo 'Lambda layer ZIP file copied successfully.'"]