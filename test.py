import os

os.environ['SKIP_TORCH'] = '1'

from DepthFlow import DepthScene

depthflow = DepthScene()
depthflow.input(image="./background.jpeg", depth='depth_map.png')
depthflow.main(output="./video.mp4", base='./')