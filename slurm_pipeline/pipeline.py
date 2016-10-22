import os
from os import path, environ
import re
from time import time
from six import string_types
from json import load
import subprocess
from collections import defaultdict


class SlurmPipelineError(Exception):
    'Base class of all SlurmPipeline exceptions'


class SchedulingError(SlurmPipelineError):
    'An error in scheduling execution'


class SpecificationError(SlurmPipelineError):
    'An error was found in a specification'


class SlurmPipeline(object):
    """
    Read a pipeline execution specification and make it possible to schedule
    it via SLURM.

    @param specification: Either a C{str} giving the name of a file containing
        a JSON execution specification, or a C{dict} holding a correctly
        formatted execution specification.
    @param scriptArgs: A C{list} of C{str} arguments that should be put on the
        command line of all steps that have no dependencies.
    """

    # In script output, look for lines of the form
    # TASK: NAME 297483 297485 297490
    # containing a task name (with no spaces) followed by zero or more numeric
    # job ids. The following regex just matches the first part of that.
    TASK_NAME_LINE = re.compile('^TASK:\s+(\S+)\s*')

    def __init__(self, specification, scriptArgs=None):
        if isinstance(specification, string_types):
            specification = self._loadSpecification(specification)
        # self.steps will be keyed by step name, with values that are
        # self.specification step dicts. This is for convenient / direct
        # access to steps by name. It is initialized in
        # self._checkSpecification.
        self.steps = {}
        self._checkSpecification(specification)
        self.specification = specification
        self._scriptArgs = scriptArgs

    def schedule(self):
        """
        Schedule the running of our execution specification.
        """
        if 'scheduledAt' in self.specification:
            raise SchedulingError('Specification has already been scheduled')
        else:
            self.specification['scheduledAt'] = time()
            for step in self.specification['steps']:
                self._scheduleStep(step)

    def _scheduleStep(self, step):
        """
        Schedule a single execution step.

        @param step: A C{dict} with a job specification.
        """
        assert 'scheduledAt' not in step
        assert 'tasks' not in step
        step['tasks'] = defaultdict(set)

        # taskDependencies is keyed by task name. These are the tasks
        # started by the steps that the current step depends on.  Its
        # values are sets of SLURM job ids the tasks that step started and
        # which this step therefore depends on.
        step['taskDependencies'] = taskDependencies = defaultdict(set)
        for stepName in step.get('dependencies', []):
            for taskName, jobIds in self.steps[stepName]['tasks'].items():
                taskDependencies[taskName].update(jobIds)

        scriptArgs = ' '.join(self._scriptArgs) if self._scriptArgs else ''

        if taskDependencies:
            if 'collect' in step:
                # This step is a 'collector'. I.e., it is dependent on all
                # tasks from all its dependencies and cannot run until they
                # have all finished. We will only run the script once, and tell
                # it about all job ids for all tasks that are depended on.
                env = environ.copy()
                env.update({
                    'SP_ORIGINAL_ARGS': scriptArgs,
                    'SP_DEPENDENCY_ARG': '--dependency=' + ','.join(
                        sorted(('afterok:%d' % jobId)
                               for jobIds in taskDependencies.values()
                               for jobId in jobIds)),
                    'SP_TASK_NAMES': ' '.join(sorted(taskDependencies)),
                })
                self._runStepScript(step, env)
            else:
                # The script for this step gets run once for each task in the
                # steps it depends on.
                for taskName in sorted(taskDependencies):
                    jobIds = self.steps[stepName]['tasks'][taskName]
                    env = environ.copy()
                    env.update({
                        'SP_ORIGINAL_ARGS': scriptArgs,
                        'SP_DEPENDENCY_ARG': '--dependency=' + (
                            ','.join(sorted(('afterok:%d' % jobId)
                                            for jobId in jobIds))),
                        'SP_TASK_NAME': taskName,
                    })
                    self._runStepScript(step, env)
        else:
            # There are no dependencies. Run the script with no setting for
            # the environment variables.
            env = environ.copy()
            env['SP_ORIGINAL_ARGS'] = scriptArgs
            for key in 'SP_TASK_NAME', 'SP_TASK_NAMES', 'SP_DEPENDENCY_ARG':
                env.pop(key, None)
            self._runStepScript(step, env, hasDependencies=False)

        step['scheduledAt'] = time()

    def _runStepScript(self, step, env, hasDependencies=True):
        """
        Run the script for a step, using a given environment and parse its
        output for tasks it scheduled via sbatch.

        @param step: A C{dict} with a job specification.
        @param env: A C{str} key to C{str} value environment for the script.
        @param hasDependencies: If C{True} the step has dependencies and will
            be run with no command line arguments. Otherwise, command line
            arguments (in self._scriptArgs) will be passed to the script.
        @raise SchedulingError: If a script outputs a task name more than once.
        """
        script = step['script']
        try:
            cwd = step['cwd']
        except KeyError:
            # No working directory was given. Run the script from our
            # current directory.
            cwd = step['cwd'] = '.'
        else:
            # A working directory was given, so make sure we have an
            # absolute path to the script so we can run it from that
            # directory.
            if not path.isabs(script):
                script = path.abspath(script)

        args = [script]

        # If this step has no dependencies and there are some script
        # arguments, add them to its command line.
        if not hasDependencies and self._scriptArgs:
            args.extend(self._scriptArgs)

        step['stdout'] = subprocess.check_output(
            args, cwd=cwd, env=env, universal_newlines=True)

        # Look at all output lines for task names and SLURM job ids created
        # (if any) by this script. Ignore any non-matching output.
        tasks = step['tasks']
        for line in step['stdout'].split('\n'):
            match = self.TASK_NAME_LINE.match(line)
            if match:
                taskName = match.group(1)
                # The job ids follow the 'TASK:' string and the task name.
                # They should not contain duplicates.
                jobIds = list(map(int, line.split()[2:]))
                if len(jobIds) != len(set(jobIds)):
                    raise SchedulingError(
                        'Task name %r was output with a duplicate in its job '
                        'ids %r by %r script in step named %r' %
                        (taskName, jobIds, script, step['name']))
                tasks[taskName].update(jobIds)

    def _loadSpecification(self, specificationFile):
        """
        Load a JSON execution specification.

        @param specificationFile: A C{str} file name containing a JSON
            execution specification.
        @raise ValueError: Will be raised (by L{json.load}) if
            C{specificationFile} does not contain valid JSON.
        @return: The parsed JSON specification as a C{dict}.
        """
        with open(specificationFile) as fp:
            return load(fp)

    def _checkSpecification(self, specification):
        """
        Check an execution specification is syntactically as expected.

        @param specification: A C{dict} containing an execution specification.
        @raise SpecificationError: if there is anything wrong with the
            specification.
        """
        if not isinstance(specification, dict):
            raise SpecificationError('The specification must be a dict (i.e., '
                                     'a JSON object when loaded from a file)')

        if 'steps' not in specification:
            raise SpecificationError(
                'The specification must have a top-level "steps" key')

        if not isinstance(specification['steps'], list):
            raise SpecificationError('The "steps" key must be a list')

        for count, step in enumerate(specification['steps'], start=1):
            if not isinstance(step, dict):
                raise SpecificationError('Step %d is not a dictionary' % count)

            if 'script' not in step:
                raise SpecificationError(
                    'Step %d does not have a "script" key' % count)

            if not isinstance(step['script'], string_types):
                raise SpecificationError(
                    'The "script" key in step %d is not a string' % count)

            if not path.exists(step['script']):
                raise SpecificationError(
                    'The script %r in step %d does not exist' %
                    (step['script'], count))

            if not os.access(step['script'], os.X_OK):
                raise SpecificationError(
                    'The script %r in step %d is not executable' %
                    (step['script'], count))

            if 'name' not in step:
                raise SpecificationError(
                    'Step %d does not have a "name" key' % count)

            if not isinstance(step['name'], string_types):
                raise SpecificationError(
                    'The "name" key in step %d is not a string' % count)

            if step['name'] in self.steps:
                raise SpecificationError(
                    'The name %r of step %d was already used in '
                    'an earlier step' % (step['name'], count))

            self.steps[step['name']] = step

            if 'dependencies' in step:
                dependencies = step['dependencies']
                if not isinstance(dependencies, list):
                    raise SpecificationError(
                        'Step %d has a non-list "dependencies" key' % count)

                # All named dependencies must already have been specified.
                for dependency in dependencies:
                    if dependency not in self.steps:
                        raise SpecificationError(
                            'Step %d depends on a non-existent (or '
                            'not-yet-defined) step: %r' % (count, dependency))
