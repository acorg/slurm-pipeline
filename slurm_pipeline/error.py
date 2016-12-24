class SlurmPipelineError(Exception):
    'Base class of all SlurmPipeline exceptions.'


class SchedulingError(SlurmPipelineError):
    'An error in scheduling execution.'


class SpecificationError(SlurmPipelineError):
    'An error was found in a specification.'


class SQueueError(SlurmPipelineError):
    'A problem was found in the output of squeue'
