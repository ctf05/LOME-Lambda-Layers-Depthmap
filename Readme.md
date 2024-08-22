# LOME-Lambda-Layers-Depthmap
One layer is the ffmpeg. The other is everything else. You must install requirements.txt, include these in the other layer.

In site-packages remove _core and tests from numpy. Remove pip. This is to keep the entire package under 250mb. If we can do this, it can be one layer

Use docker to build the lambda lazer .zip:
docker build -t lambda-layer-builder .
docker run --rm -v %cd%:/opt lambda-layer-builder


Encountered bugs:
The dockerfile must specify the architecture and python version in both the image and pip. Look at AWS rec pip install.
Pydantic must be these versions:
pydantic==1.9.0
pydantic_core==2.10.1
