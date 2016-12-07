import os
from os import path, environ
import re
import time
from six import string_types
from json import load, dumps
import subprocess
from collections import defaultdict, OrderedDict

try:
    from subprocess import DEVNULL  # py3k
except ImportError:
    DEVNULL = open(os.devnull, 'r+b')


class SlurmPipelineError(Exception):
    'Base class of all SlurmPipeline exceptions.'


class SchedulingError(SlurmPipelineError):
    'An error in scheduling execution.'


class SpecificationError(SlurmPipelineError):
    'An error was found in a specification.'


class SlurmPipeline(object):
    """
    Read a pipeline execution specification and make it possible to schedule
    it via SLURM.

    @param specification: Either a C{str} giving the name of a file containing
        a JSON execution specification, or a C{dict} holding a correctly
        formatted execution specification. Note that in the latter case the
        passed specification C{dict} will be modified by this script.
    """

    # In script output, look for lines of the form
    # TASK: NAME 297483 297485 297490
    # containing a task name (with no spaces) followed by zero or more numeric
    # job ids. The following regex just matches the first part of that.
    TASK_NAME_LINE = re.compile('^TASK:\s+(\S+)\s*')

    def __init__(self, specification):
        if isinstance(specification, string_types):
            specification = self._loadSpecification(specification)
        self._checkSpecification(specification)
        self.specification = specification

    def schedule(self, force=False, firstStep=None, lastStep=None, sleep=0.0,
                 scriptArgs=None, skip=None):
        """
        Schedule the running of our execution specification.

        @param force: If C{True}, step scripts will be told (via the
            environment variable SP_FORCE=1) that they may overwrite
            pre-existing result files. I.e., that --force was used on the
            slurm-pipeline.py command line.
        @param firstStep: If not C{None}, the name of the first specification
            step to execute. Earlier steps will actually be executed but they
            will have SP_SIMULATE=1 in their environment, allowing them to not
            do actual work (while still emitting task names without job
            numbers so that later steps receive the correct tasks to operate
            on.
        @param lastStep: If not C{None}, the name of the last specification
            step to execute. See above docs for C{firstStep} for how this
            affects the calling of step scripts.
        @param sleep: Gives the C{float} number of seconds to sleep for between
            running step scripts. This can be used to allow a distributed file
            system to settle, so that jobs that have been scheduled can be seen
            when used as dependencies in later invocations of sbatch. Pass 0.0
            for no sleep.
        @param scriptArgs: A C{list} of C{str} arguments that should be put on
            the command line of all steps that have no dependencies.
        @param skip: An iterable of C{str} step names that should be skipped.
            Those step scripts will still be run, but will have C{SP_SKIP=1}
            in their environment. Steps may also be skipped by using
            C{skip: "true"} in the pipeline specification file.
        @raise SchedulingError: If there is a problem with the first, last, or
            skipped steps, as determined by self._checkRuntime.
        @return: A specification C{dict}. This is a copy of the original
            specification, updated with information about this scheduling.
        """
        specification = self.specification.copy()
        # steps is keyed by (ordered) specification step name, with values
        # that are specification step dicts. This provides convenient
        # direct access to steps by name.
        steps = OrderedDict((s['name'], s) for s in specification['steps'])
        nSteps = len(steps)
        if nSteps and lastStep is not None and firstStep is None:
            firstStep = specification['steps'][0]['name']
        skip = set(skip or ())
        self._checkRuntime(steps, firstStep, lastStep, skip)
        specification.update({
            'force': force,
            'firstStep': firstStep,
            'lastStep': lastStep,
            'scheduledAt': time.time(),
            'scriptArgs': scriptArgs,
            'skip': skip,
            'steps': steps,
        })

        environ['SP_FORCE'] = str(int(force))
        firstStepFound = lastStepFound = False

        for stepIndex, stepName in enumerate(steps):
            if firstStep is not None:
                if firstStepFound:
                    if lastStep is not None:
                        if lastStepFound:
                            simulate = True
                        else:
                            if stepName == lastStep:
                                simulate = False
                                lastStepFound = True
                            else:
                                simulate = True
                    else:
                        simulate = False
                else:
                    if stepName == firstStep:
                        simulate = False
                        firstStepFound = True
                    else:
                        simulate = True
            else:
                simulate = False

            self._scheduleStep(stepName, steps, simulate, scriptArgs,
                               stepName in skip or ('skip' in steps[stepName]))

            # If we're supposed to pause between scheduling steps and this
            # is not the last step, then sleep.
            if sleep > 0.0 and stepIndex < nSteps - 1:
                time.sleep(sleep)

        return specification

    def _scheduleStep(self, stepName, steps, simulate, scriptArgs, skip):
        """
        Schedule a single execution step.

        @param step: A C{dict} with a job specification.
        @param simulate: If C{True}, this step should be simulated. The step
            script is still run, but with SP_SIMULATE=1 in its environment.
            Else, SP_SIMULATE=0 will be in the environment.
        @param scriptArgs: A C{list} of C{str} arguments that should be put on
            the command line of all steps that have no dependencies.
        @param skip: If C{True}, the step should be skipped, which will be
            indicated to the script by SP_SKIP=1 in its environment. SP_SKIP
            will be 0 in non-skipped steps. It is up to the script, which is
            run in either case, to decide how to behave.
        """
        step = steps[stepName]
        step['tasks'] = defaultdict(set)
        step['simulate'] = simulate
        step['skip'] = skip
        scriptArgsStr = ' '.join(map(str, scriptArgs)) if scriptArgs else ''

        if step.get('error step', False):
            separator = '?'
            after = 'afternotok'
        else:
            separator = ','
            after = 'afterok'

        # taskDependencies is keyed by task name. These are the tasks
        # started by the steps that the current step depends on.  Its
        # values are sets of SLURM job ids the tasks that step started and
        # which this step therefore depends on.
        step['taskDependencies'] = taskDependencies = defaultdict(set)
        for stepName in step.get('dependencies', ()):
            for taskName, jobIds in steps[stepName]['tasks'].items():
                taskDependencies[taskName].update(jobIds)

        if taskDependencies:
            if 'collect' in step:
                # This step is a 'collector'. I.e., it is dependent on all
                # tasks from all its dependencies and cannot run until they
                # have all finished. We will only run the script once, and tell
                # it about all job ids for all tasks that are depended on.
                env = environ.copy()
                env['SP_ORIGINAL_ARGS'] = scriptArgsStr
                env['SP_SIMULATE'] = str(int(simulate))
                env['SP_SKIP'] = str(int(skip))
                dependencies = separator.join(
                    sorted(('%s:%d' % (after, jobId))
                           for jobIds in taskDependencies.values()
                           for jobId in jobIds))
                if dependencies:
                    env['SP_DEPENDENCY_ARG'] = '--dependency=' + dependencies
                else:
                    env.pop('SP_DEPENDENCY_ARG', None)
                self._runStepScript(step, sorted(taskDependencies), env)
            else:
                # The script for this step gets run once for each task in the
                # steps it depends on.
                for taskName in sorted(taskDependencies):
                    env = environ.copy()
                    env['SP_ORIGINAL_ARGS'] = scriptArgsStr
                    env['SP_SIMULATE'] = str(int(simulate))
                    env['SP_SKIP'] = str(int(skip))
                    jobIds = steps[stepName]['tasks'][taskName]
                    dependencies = separator.join(
                        sorted(('%s:%d' % (after, jobId))
                               for jobId in jobIds))
                    if dependencies:
                        env['SP_DEPENDENCY_ARG'] = ('--dependency=' +
                                                    dependencies)
                    else:
                        env.pop('SP_DEPENDENCY_ARG', None)
                    self._runStepScript(step, [taskName], env)
        else:
            # Either this step has no dependencies or the steps it is
            # dependent on did not start any tasks. If there are no
            # dependencies, run the script with the originally passed
            # command line arguments. If there were dependencies but no
            # tasks have been started, run with no command line arguments.
            if 'dependencies' in step or scriptArgs is None:
                args = []
            else:
                args = list(map(str, scriptArgs))
            env = environ.copy()
            env['SP_ORIGINAL_ARGS'] = scriptArgsStr
            env['SP_SIMULATE'] = str(int(simulate))
            env['SP_SKIP'] = str(int(skip))
            env.pop('SP_DEPENDENCY_ARG', None)
            self._runStepScript(step, args, env)

        step['scheduledAt'] = time.time()

    def _runStepScript(self, step, args, env):
        """
        Run the script for a step, using a given environment and parse its
        output for tasks it scheduled via sbatch.

        @param step: A C{dict} with a job specification.
        @param env: A C{str} key to C{str} value environment for the script.
        @param args: A C{list} of command-line arguments.
        @raise SchedulingError: If a script outputs a task name more than once.
        """
        script = step['script']
        try:
            cwd = step['cwd']
        except KeyError:
            # No working directory was given. Run the script from our
            # current directory.
            cwd = '.'
        else:
            # A working directory was given, so make sure we have an
            # absolute path to the script so we can run it from that
            # directory.
            if not path.isabs(script):
                script = path.abspath(script)

        step['stdout'] = subprocess.check_output(
            [script] + args, cwd=cwd, env=env, stdin=DEVNULL,
            universal_newlines=True)

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
        stepNames = set()

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

            if step['name'] in stepNames:
                raise SpecificationError(
                    'The name %r of step %d was already used in '
                    'an earlier step' % (step['name'], count))

            stepNames.add(step['name'])

            if 'dependencies' in step:
                dependencies = step['dependencies']
                if not isinstance(dependencies, list):
                    raise SpecificationError(
                        'Step %d has a non-list "dependencies" key' % count)

                # All named dependencies must already have been specified.
                for dependency in dependencies:
                    if dependency not in stepNames:
                        raise SpecificationError(
                            'Step %d depends on a non-existent (or '
                            'not-yet-defined) step: %r' % (count, dependency))

            if 'error step' in step and 'dependencies' not in step:
                    raise SpecificationError(
                        'Step "%s" is an error step but has no "dependencies" '
                        'key' % (step['name']))

    def _checkRuntime(self, steps, firstStep=None, lastStep=None, skip=None):
        """
        Check that a proposed scheduling makes sense.

        @param steps: An C{OrderedDict} of specification steps, keyed by step
            name.
        @param firstStep: If not C{None}, the name of the first specification
            step to execute.
        @param lastStep: If not C{None}, the name of the last specification
            step to execute.
        @param skip: A C{set} of C{str} step names that should be skipped.
        @raise SchedulingError: if the last step occurs before the first, if
            the last or first step are unknown, or if asked to skip a
            non-existent step.
        @return: An C{OrderedDict} keyed by specification step name,
            with values that are C{self.specification} step dicts. This
            provides convenient / direct access to steps by name.
        """
        firstStepFound = False

        if firstStep is not None and firstStep not in steps:
            raise SchedulingError(
                'First step %r not found in specification' % firstStep)

        if lastStep is not None and lastStep not in steps:
            raise SchedulingError(
                'Last step %r not found in specification' % lastStep)

        for step in steps.values():
            if step['name'] == firstStep:
                firstStepFound = True

            if step['name'] == lastStep:
                if firstStep is not None and not firstStepFound:
                    raise SchedulingError(
                        'Last step (%r) occurs before first step (%r) in '
                        'the specification' % (lastStep, firstStep))

        if skip:
            unknownSteps = skip - set(steps)
            if unknownSteps:
                raise SchedulingError(
                    'Unknown skip step%s (%s) passed to schedule' % (
                        '' if len(unknownSteps) == 1 else 's',
                        ', '.join(sorted(unknownSteps))))

    @staticmethod
    def specificationToJSON(specification):
        """
        Convert a specification to a JSON string.

        @param specification: A specification C{dict}. This parameter is not
            modified.
        @return: A C{str} giving C{specification} in JSON form.
        """
        specification = specification.copy()

        # Convert sets to lists and the steps ordered dictionary into a list.
        specification['skip'] = list(specification['skip'])
        steps = []
        for step in specification['steps'].values():
            for taskName, jobIds in step['tasks'].items():
                step['tasks'][taskName] = list(sorted(jobIds))
            for taskName, jobIds in step['taskDependencies'].items():
                step['taskDependencies'][taskName] = list(sorted(jobIds))
            steps.append(step)
        specification['steps'] = steps
        return dumps(specification, sort_keys=True, indent=2,
                     separators=(',', ': '))
