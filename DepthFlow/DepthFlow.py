from . import *


@define
class DepthFlowScene(ShaderFlowScene):
    """🌊 Image to → 2.5D Parallax Effect Video. High quality, user first."""
    __name__ = "DepthFlow"

    # Constants
    DEFAULT_IMAGE  = "https://w.wallhaven.cc/full/pk/wallhaven-pkz5r9.png"
    DEPTH_SHADER   = (DEPTHFLOW.RESOURCES.SHADERS/"DepthFlow.frag")
    LOADING_SHADER = (SHADERFLOW.RESOURCES.FRAGMENT/"Loading.frag")

    # DepthFlow objects
    mde: DepthFlowMDE  = Field(factory=DepthFlowMDE)

    # Parallax parameters
    parallax_fixed     = Field(default=True)
    parallax_height    = Field(default=0.2)
    parallax_focus     = Field(default=1.0)
    parallax_zoom      = Field(default=1.0)
    parallax_isometric = Field(default=0.0)
    parallax_dolly     = Field(default=0.0)
    parallax_x         = Field(default=0.0)
    parallax_y         = Field(default=0.0)

    # ------------------------------------------|
    # Parallax MDE and Loading screen tricky implementation

    __loading__:     Thread = None
    __load_image__:  Image  = None
    __load_depth__:  Image  = None

    def __parallax__(self,
        image: Option[Image, Path, "url"],
        depth: Option[Image, Path, "url"]=None,
        cache: bool=True
    ):
        self.__load_image__ = LoaderImage(image)
        self.__load_depth__ = LoaderImage(depth or self.mde(image, cache=cache))

    def parallax(self,
        image: Annotated[str,  TyperOption("--image", "-i", help="Image to parallax (path, url)")],
        depth: Annotated[str,  TyperOption("--depth", "-d", help="Depth map of the Image, None to estimate")]=None,
        cache: Annotated[bool, TyperOption("--cache", "-c", help="Cache the Depth Map estimations")]=True,
        block: Annotated[bool, TyperOption("--block", "-b", help="Wait for the Image and Depth Map to be loaded")]=False
    ):
        """
        Load a new parallax image and depth map. If depth is None, it will be estimated.
        • If block is True, the function will wait until the images are loaded (implied on rendering)
        """
        if self.__loading__ and not block:
            return

        # Start loading process
        self.engine.fragment = self.LOADING_SHADER
        self.__loading__ = BrokenThread.new(self.__parallax__,
            image=image, depth=depth, cache=cache
        )

        # Wait until loading finish
        if block: self.__loading__.join()
        self.time = 0

    # ------------------------------------------|
    # DepthFlowScene internal methods

    def _ui_(self) -> None:
        if (state := imgui.checkbox("Fixed", self.parallax_fixed))[0]:
            self.parallax_fixed = state[1]
        if (state := imgui.input_float("Height", self.parallax_height, 0.01, 0.01, "%.2f"))[0]:
            self.parallax_height = max(0, state[1])

    def _pipeline_(self) -> Iterable[ShaderVariable]:
        yield ShaderVariable("uniform", "bool",  "iParallaxFixed",     self.parallax_fixed)
        yield ShaderVariable("uniform", "float", "iParallaxHeight",    self.parallax_height)
        yield ShaderVariable("uniform", "float", "iParallaxFocus",     self.parallax_focus)
        yield ShaderVariable("uniform", "float", "iParallaxZoom",      self.parallax_zoom)
        yield ShaderVariable("uniform", "float", "iParallaxIsometric", self.parallax_isometric)
        yield ShaderVariable("uniform", "float", "iParallaxDolly",     self.parallax_dolly)
        yield ShaderVariable("uniform", "vec2",  "iParallaxPosition",  (self.parallax_x, self.parallax_y))

    def _build_(self):
        self.image = self.add(ShaderFlowTexture(name="image").repeat(False))
        self.depth = self.add(ShaderFlowTexture(name="depth").repeat(False))

    def _update_(self):

        # Set default image if none provided
        if self.image.is_empty:
            self.parallax(image=DepthFlowScene.DEFAULT_IMAGE)

        # Block when rendering (first Scene update)
        if self.rendering and self.image.is_empty:
            self.__loading__.join()

        # Load new parallax images and parallax shader
        if self.__load_image__ and self.__load_depth__:
            self.image.from_pil(self.__load_image__); self.__load_image__ = None
            self.depth.from_pil(self.__load_depth__); self.__load_depth__ = None
            self.engine.fragment = self.DEPTH_SHADER
            self.__loading__ = None
            self.time = 0

    def _handle_(self, message: ShaderFlowMessage):
        if isinstance(message, ShaderFlowMessage.Window.FileDrop):
            self.parallax(image=message.files[0], depth=message.files.get(1))

    # ------------------------------------------|
    # User defined functions

    def commands(self):
        self.broken_typer.command(self.parallax)

    @abstractmethod
    def update(self):
        """Define your own update here or from an inherited class"""

        # In and out dolly zoom
        self.parallax_dolly = 0.5*(1 + math.cos(self.time))

        # Infinite 8 loop shift
        self.parallax_x = 0.1 * math.sin(  self.time)
        self.parallax_y = 0.1 * math.sin(2*self.time)

        # Oscillating rotation
        self.camera.rotate(
            direction=self.camera.base_z,
            angle=math.cos(self.time)*self.dt*0.4
        )

        # Zoom out on the start
        # self.parallax_zoom = 0.6 + 0.4*(2/math.pi)*math.atan(3*self.time)

    @abstractmethod
    def pipeline(self) -> Iterable[ShaderVariable]:
        """Define your own pipeline here or from an inherited class"""
        ...

    @abstractmethod
    def handle(self, message: ShaderFlowMessage):
        """Handle your own messages here or from an inherited class"""
        ...
