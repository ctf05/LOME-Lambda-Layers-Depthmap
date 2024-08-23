import os
from PIL import Image

#os.environ['SKIP_TORCH'] = '1'
import glcontext
print(glcontext.__file__)  # This will show where glcontext is installed
print(dir(glcontext))  # This will list all available attributes and modules

from DepthFlow import DepthScene

depthflow = DepthScene(backend='headless', visible=False)
depthflow.input(image=Image.open("./background.jpeg"), depth=Image.open('depth_map.png'))
depthflow.main(output="./video.mp4", base='./', local_ffmpeg_path=".\\ffmpeg-master-latest-win64-gpl\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.EXE", quality=100, fps=40, ssaa=2.5)