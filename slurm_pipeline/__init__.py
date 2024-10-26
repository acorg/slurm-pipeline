from .pipeline import SlurmPipeline
from .status import SlurmPipelineStatus

__all__ = ["SlurmPipeline", "SlurmPipelineStatus"]

# Note that the version string must have the following format, otherwise it
# will not be found by the version() function in ../setup.py
__version__ = "4.1.2"
