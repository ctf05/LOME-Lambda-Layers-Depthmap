import copy
import math
import os
from typing import Annotated, Iterable, List, Union

import imgui
import numpy
from PIL import Image
from attr import define, field
from ShaderFlow.Message import ShaderMessage
from ShaderFlow.Scene import ShaderScene
from ShaderFlow.Texture import ShaderTexture
from ShaderFlow.Variable import ShaderVariable
from typer import Option
import matplotlib.pyplot as plt

from Broken.Externals.Depthmap import (
    DepthAnythingV1,
    DepthAnythingV2,
    DepthEstimator,
    Marigold,
    ZoeDepth,
)
from Broken.Loaders import LoaderImage
from DepthFlow import DEPTHFLOW
from DepthFlow.Animation import (
    Constant,
    DepthAnimation,
    DepthPreset,
    Linear,
    Sine,
)
from DepthFlow.State import DepthState

DEPTHFLOW_ABOUT = """
🌊 Image to → 2.5D Parallax Effect Video. A Free and Open Source LeiaPix/ImmersityAI alternative.\n

Usage: All commands have a --help option with extensible configuration, and are chained together

[yellow]Examples:[/yellow]
• Simplest:    [bold blue]depthflow[/bold blue] [blue]main[/blue] [bright_black]# Realtime window, drag and drop images![/bright_black]
• Your image:  [bold blue]depthflow[/bold blue] [blue]input[/blue] -i ./image.png [blue]main[/blue]
• Exporting:   [bold blue]depthflow[/bold blue] [blue]input[/blue] -i ./image.png [blue]main[/blue] -o ./output.mp4
• Upscaler:    [bold blue]depthflow[/bold blue] [blue]realesr[/blue] --scale 2 [blue]input[/blue] -i ./image.png [blue]main[/blue] -o ./output.mp4
• Convenience: [bold blue]depthflow[/bold blue] [blue]input[/blue] -i ./image16x9.png [blue]main[/blue] -h 1440 [bright_black]# Auto calculates w=2560[/bright_black]
• Estimator:   [bold blue]depthflow[/bold blue] [blue]dav2[/blue] --model large [blue]input[/blue] -i ~/image.png [blue]main[/blue]
• Post FX:     [bold blue]depthflow[/bold blue] [blue]dof[/blue] -e [blue]vignette[/blue] -e [blue]main[/blue]

[yellow]Notes:[/yellow]
• A --ssaa value of 1.5+ is recommended for final exports, real time uses 1.2
• The [bold blue]main[/bold blue]'s --quality preset gives little improvement for small movements
• The rendered video loops perfectly, the period is the main's --time
• The last two commands must be [bold blue]input[/bold blue] and [bold blue]main[/bold blue] (in order) to work
"""

# -------------------------------------------------------------------------------------------------|

@define
class DepthScene(ShaderScene):
    __name__ = "DepthFlow"

    # Constants
    DEFAULT_IMAGE = "https://w.wallhaven.cc/full/pk/wallhaven-pkz5r9.png"
    DEPTH_SHADER  = (DEPTHFLOW.RESOURCES.SHADERS/"DepthFlow.glsl")

    # DepthFlow objects
    animation: List[Union[DepthAnimation, DepthPreset]] = field(factory=list)
    state: DepthState = field(factory=DepthState)

    def add_animation(self, animation: DepthAnimation) -> None:
        self.animation.append(copy.deepcopy(animation))


    def set_estimator(self, estimator: DepthEstimator) -> None:
        self.estimator = estimator

    def input(self,
              image: Annotated[str, Option("--image", "-i", help="[bold green](🟢 Basic)[/bold green] Background Image [green](Path, URL, NumPy, PIL)[/green]")],
              depth: Annotated[str, Option("--depth", "-d", help="[bold green](🟢 Basic)[/bold green] Depthmap of the Image [medium_purple3](None to estimate)[/medium_purple3]")]=None,
              ) -> None:
        """Load an Image from Path, URL and its Depthmap [green](See 'input --help' for options)[/green]"""

        # Load the background image
        image = LoaderImage(image)
        plt.imshow(image, cmap='viridis')
        plt.colorbar()
        plt.show()

        # Load the depth map from a file instead of estimating
        depth = Image.open(depth)  # Load the pre-existing depth map image
        depth = depth.resize((image.width, image.height))  # Resize to match the image size
        plt.imshow(depth, cmap='viridis')
        plt.colorbar()
        plt.show()

        # Continue with the original depth map processing
        self.aspect_ratio = (image.width/image.height)
        self.normal.from_numpy(self.normal_map(depth))
        self.image.from_image(image)
        self.depth.from_image(depth)

    def normal_map(self, depth: numpy.ndarray) -> numpy.ndarray:
        """Estimates a normal map from a depth map using heuristics"""
        depth = numpy.array(depth)
        if depth.ndim == 3:
            depth = depth[..., 0]
        dx = numpy.arctan2(200*numpy.gradient(depth, axis=1), 1)
        dy = numpy.arctan2(200*numpy.gradient(depth, axis=0), 1)
        normal = numpy.dstack((-dx, dy, numpy.ones_like(depth)))
        return self.normalize(normal).astype(numpy.float32)

    def normalize(self, array: numpy.ndarray) -> numpy.ndarray:
        return (array - array.min()) / ((array.max() - array.min()) or 1)

    def webui(self):
        """Launch a Gradio WebUI for DepthFlow in the browser"""
        from DepthFlow.Webui import DepthFlowWebui
        DepthFlowWebui().launch()

    def commands(self):
        self.typer.description = DEPTHFLOW_ABOUT

        with self.typer.panel(self.scene_panel):
            self.typer.command(self.state, name="config")
            self.typer.command(self.webui)
            self.typer.command(self.input)

        with self.typer.panel("🌊 Depth estimators"):
            self.typer.command(DepthAnythingV1, post=self.set_estimator, name="dav1")
            self.typer.command(DepthAnythingV2, post=self.set_estimator, name="dav2")
            self.typer.command(ZoeDepth, post=self.set_estimator)
            self.typer.command(Marigold, post=self.set_estimator)

        with self.typer.panel("🔮 Animation (Presets)"):
            ...

    def setup(self):
        if self.image.is_empty():
            self.input(image=DepthScene.DEFAULT_IMAGE)
        self.time = 0

    def build(self):
        ShaderScene.build(self)
        self.image = ShaderTexture(scene=self, name="image").repeat(False)
        self.depth = ShaderTexture(scene=self, name="depth").repeat(False)
        self.normal = ShaderTexture(scene=self, name="normal").repeat(False)
        self.shader.fragment = self.DEPTH_SHADER
        self.aspect_ratio = (16/9)
        self.ssaa = 1.2

    def update(self):
        if (eval(os.getenv("PRESETS", "0"))):
            self.state.reset()
            for item in self.animation:
                item.update(self)
            return

        elif eval(os.getenv("VERTICAL", "0")):
            self.state.offset_y = (2/math.pi) * math.asin(math.cos(self.cycle)) - 0.5
            self.state.isometric = 0.8
            self.state.height = 0.15
            self.state.static = 0.50

        elif eval(os.getenv("HORIZONTAL", "0")):
            self.state.offset_x = (2/math.pi) * math.asin(math.cos(self.cycle)) - 0.5
            self.state.isometric = 0.8
            self.state.height = 0.15
            self.state.static = 0.50

        elif (eval(os.getenv("ORGANIC", "0"))):
            self.state.isometric = 0.5

            # In and out dolly zoom
            self.state.dolly = (0.5 + 0.5*math.cos(self.cycle))

            # Infinite 8 loop shift
            self.state.offset_x = (0.2 * math.sin(1*self.cycle))
            self.state.offset_y = (0.2 * math.sin(2*self.cycle))

            # Integral rotation (better for realtime)
            self.camera.rotate(
                direction=self.camera.base_z,
                angle=math.cos(self.cycle)*self.dt*0.4
            )

            # Fixed known rotation
            self.camera.rotate2d(1.5*math.sin(self.cycle))

            # Zoom in on the start
            # self.config.zoom = 1.2 - 0.2*(2/math.pi)*math.atan(self.time)

        # "ORBITAL" default
        else:
            self.state.isometric = 0.51 + 0.5 * math.cos(self.cycle/2)**2
            self.state.offset_x = 0.5 * math.sin(self.cycle)
            self.state.static = 0.50
            self.state.height = 0.25
            self.state.focus = 0.50

    def handle(self, message: ShaderMessage):
        ShaderScene.handle(self, message)

        if isinstance(message, ShaderMessage.Window.FileDrop):
            files = iter(message.files)
            self.input(image=next(files), depth=next(files, None))

    def pipeline(self) -> Iterable[ShaderVariable]:
        yield from ShaderScene.pipeline(self)
        yield from self.state.pipeline()

    def ui(self) -> None:
        if (state := imgui.slider_float("Height", self.state.height, 0, 1, "%.2f"))[0]:
            self.state.height = max(0, state[1])
        if (state := imgui.slider_float("Static", self.state.static, 0, 1, "%.2f"))[0]:
            self.state.static = max(0, state[1])
        if (state := imgui.slider_float("Focus", self.state.focus, 0, 1, "%.2f"))[0]:
            self.state.focus = max(0, state[1])
        if (state := imgui.slider_float("Invert", self.state.invert, 0, 1, "%.2f"))[0]:
            self.state.invert = max(0, state[1])
        if (state := imgui.slider_float("Zoom", self.state.zoom, 0, 2, "%.2f"))[0]:
            self.state.zoom = max(0, state[1])
        if (state := imgui.slider_float("Isometric", self.state.isometric, 0, 1, "%.2f"))[0]:
            self.state.isometric = max(0, state[1])
        if (state := imgui.slider_float("Dolly", self.state.dolly, 0, 5, "%.2f"))[0]:
            self.state.dolly = max(0, state[1])

        imgui.text("- True camera position")
        if (state := imgui.slider_float("Center X", self.state.center_x, -self.aspect_ratio, self.aspect_ratio, "%.2f"))[0]:
            self.state.center_x = state[1]
        if (state := imgui.slider_float("Center Y", self.state.center_y, -1, 1, "%.2f"))[0]:
            self.state.center_y = state[1]

        imgui.text("- Fixed point at height changes")
        if (state := imgui.slider_float("Origin X", self.state.origin_x, -self.aspect_ratio, self.aspect_ratio, "%.2f"))[0]:
            self.state.origin_x = state[1]
        if (state := imgui.slider_float("Origin Y", self.state.origin_y, -1, 1, "%.2f"))[0]:
            self.state.origin_y = state[1]

        imgui.text("- Parallax offset")
        if (state := imgui.slider_float("Offset X", self.state.offset_x, -2, 2, "%.2f"))[0]:
            self.state.offset_x = state[1]
        if (state := imgui.slider_float("Offset Y", self.state.offset_y, -2, 2, "%.2f"))[0]:
            self.state.offset_y = state[1]
