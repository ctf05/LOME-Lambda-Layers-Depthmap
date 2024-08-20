# LOME-Lambda-Layers-Depthmap
One layer is the ffmpeg. The other is everything else. You must install requirements.txt, include these in the other layer.

In site-packages remove _core and tests from numpy. Remove pip. This is to keep the entire package under 250mb. If we can do this, it can be one layer
