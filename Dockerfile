# Use the latest AWS Lambda Python runtime as the base image
FROM public.ecr.aws/lambda/python:latest as builder

# Set the working directory in the container
WORKDIR /var/task

# Install system dependencies and build dependencies
RUN yum update -y && \
    yum groupinstall -y "Development Tools" && \
    yum install -y \
        git unzip wget tar gzip xz zip \
        gcc make zlib-devel libjpeg-devel openjpeg2-devel \
        python3-devel \
        mesa-libGL \
        mesa-libGLU \
        glfw-devel \
        xorg-x11-server-Xvfb \
        libXi-devel \
        libXrandr-devel \
        libXcursor-devel \
        libXinerama-devel \
        glfw glfw-devel && \
    yum clean all && \
    rm -rf /var/cache/yum

# Clone your Git repository
RUN git clone https://github.com/ctf05/LOME-Lambda-Layers-Depthmap.git .

# Create the directory structure for the Lambda layer
RUN mkdir -p /opt/python

# Copy the needed files and directories, including the broken_source-0.5.0.dist-info folder
RUN cp -r DepthFlow ShaderFlow Broken broken_source-0.5.0.dist-info /opt/python/ && \
    cp pyproject.toml requirements.txt test.py /opt/python/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install \
    --no-cache-dir \
    --platform manylinux2014_x86_64 \
    --target=/opt/python \
    --implementation cp \
    --python-version 3.9 \
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

# Test the import
RUN python -c "import sys; sys.path.append('/opt/python'); from DepthFlow import DepthScene; print('Import successful!')"

# Set the working directory to /opt
WORKDIR /opt

# Create the ZIP file with maximum compression
RUN zip -r9 /tmp/lambda-layer.zip python

# Use a minimal base image for the final stage
FROM alpine:latest

# Copy the ZIP file from the previous stage
COPY --from=builder /tmp/lambda-layer.zip /lambda-layer.zip

# Set the entrypoint to copy the ZIP file to the mounted volume
ENTRYPOINT ["/bin/sh", "-c", "cp /lambda-layer.zip /opt/ && echo 'Lambda layer ZIP file created successfully.' && echo 'ZIP file size:' && du -h /opt/lambda-layer.zip"]
