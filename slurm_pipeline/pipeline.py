import os
from os import path, environ
import re
import time
import subprocess
from collections import defaultdict
from getpass import getuser
from subprocess import DEVNULL
from typing import Optional, Iterable

from .base import SlurmPipelineBase
from .error import SchedulingError, SpecificationError


class SlurmPipeline(SlurmPipelineBase):
    """
    Read a pipeline execution specification and make it possible to schedule
    it via SLURM.
    """

    # In task script output, look for lines of the form
    #   TASK: NAME 297483 297485 297490
    # containing a task name (with no spaces) followed by zero or more numeric
    # job ids. The following regex just matches 'TASK' and the task name.
    TASK_NAME_LINE = re.compile(r"^TASK:\s*(\S+)")

    # Limits on the --nice argument to sbatch. In later SLURM versions the
    # limits are +/-2147483645. See https://slurm.schedmd.com/sbatch.html
    NICE_HIGHEST = -10000
    NICE_LOWEST = 10000

    ENV_VARS = (
        "SP_DEPENDENCY_ARG",
        "SP_FORCE",
        "SP_NICE_ARG",
        "SP_SKIP",
        "SP_ORIGINAL_ARGS",
    )

    @staticmethod
    def checkSpecification(specification: dict) -> None:
        """
        Check an execution specification is as expected.

        @param specification: A C{dict} containing an execution specification.
        @raise SpecificationError: if there is anything wrong with the
            specification.
        """
        SlurmPipelineBase.checkSpecification(specification)

        for count, step in enumerate(specification["steps"], start=1):
            try:
                cwd = step["cwd"]
            except KeyError:
                script = step["script"]
            else:
                if not path.isdir(cwd):
                    raise SpecificationError(
                        "Specification step %d specifies a working directory "
                        "(%r) that does not exist" % (count, cwd)
                    )

                script = step["script"]
                if not path.isabs(script):
                    script = path.join(cwd, script)

            if not path.exists(script):
                raise SpecificationError(
                    "The script %r in step %d does not exist" % (step["script"], count)
                )

            if not os.access(script, os.X_OK):
                raise SpecificationError(
                    "The script %r in step %d is not executable"
                    % (step["script"], count)
                )

    def schedule(
        self,
        force: bool = False,
        firstStep: Optional[str] = None,
        lastStep: Optional[str] = None,
        sleep: float = 0.0,
        scriptArgs: Optional[Iterable[str]] = None,
        skip: Optional[Iterable[str]] = None,
        startAfter: Optional[Iterable[int]] = None,
        nice: Optional[int] = None,
        printOutput: bool = False,
    ) -> dict:
        """
        Schedule the running of our execution specification.

        @param force: If C{True}, step scripts will be told (via the
            environment variable SP_FORCE=1) that they may overwrite
            pre-existing result files. I.e., that --force was used on the
            slurm-pipeline.py command line.
        @param firstStep: If not C{None}, the name of the first specification
            step to execute. Earlier steps will actually be executed but they
            will have SP_SKIPE=1 in their environment, allowing them to not
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
        @param startAfter: A C{list} of C{int} job ids that must complete
            (either successully or unsuccessully, it doesn't matter) before
            steps in the current specification may start. If C{None}, steps in
            the current specification may start immediately.
        @param nice: An C{int} nice (priority) value, in the range
            self.NICE_HIGHEST to self.NICE_LOWEST. Note that only
            privileged users can specify a negative adjustment.
        @param printOutput: If C{True}, print the output of each step.
        @raise SchedulingError: If there is a problem with the first, last, or
            skipped steps, as determined by self._checkRuntime. ValueError if
            C{nice} is not numeric or is out of its allowed range.
        @return: A specification C{dict}. This is a copy of the original
            specification, updated with information about this scheduling.
        """
        specification = self.specification
        steps = specification["steps"]
        nSteps = len(steps)
        if nSteps and lastStep is not None and firstStep is None:
            firstStep = list(specification["steps"])[0]
        skip = set(skip or ())
        self._checkRuntime(steps, firstStep, lastStep, skip, nice)
        specification.update(
            {
                "firstStep": firstStep,
                "force": force,
                "lastStep": lastStep,
                "nice": nice,
                "scheduledAt": time.time(),
                "scriptArgs": scriptArgs,
                "skip": skip,
                "sleep": sleep,
                "startAfter": startAfter,
                "steps": steps,
                "user": getuser(),
            }
        )

        environ["SP_FORCE"] = str(int(force))
        environ["SP_NICE_ARG"] = "--nice" if nice is None else "--nice=%d" % nice
        firstStepFound = lastStepFound = False

        for stepIndex, stepName in enumerate(steps):
            if firstStep is not None:
                if firstStepFound:
                    if lastStep is not None:
                        if lastStepFound:
                            impliedSkip = True
                        else:
                            if stepName == lastStep:
                                impliedSkip = False
                                lastStepFound = True
                            else:
                                impliedSkip = True
                    else:
                        impliedSkip = False
                else:
                    if stepName == firstStep:
                        impliedSkip = False
                        firstStepFound = True
                    else:
                        impliedSkip = True
            else:
                impliedSkip = False

            self._scheduleStep(
                stepName,
                steps,
                scriptArgs or [],
                impliedSkip or stepName in skip or "skip" in steps[stepName],
                startAfter,
            )

            if printOutput:
                step = steps[stepName]
                if step["stdout"]:
                    print(step["stdout"], end="")

            # If we're supposed to pause between scheduling steps and this
            # is not the last step, then sleep.
            if sleep > 0.0 and stepIndex < nSteps - 1:
                time.sleep(sleep)

        return specification

    def _scheduleStep(
        self,
        stepName: str,
        steps: dict,
        scriptArgs: Iterable[str],
        skip: bool,
        startAfter: Optional[Iterable[int]],
    ) -> None:
        """
        Schedule a single execution step.

        @param stepName: A C{str} step name.
        @param steps: A C{dict} of steps.
        @param scriptArgs: A C{list} of C{str} arguments that should be put on
            the command line of all steps that have no dependencies.
        @param skip: If C{True}, the step should be skipped, which will be
            indicated to the script by SP_SKIP=1 in its environment. SP_SKIP
            will be 0 in non-skipped steps. It is up to the script, which is
            run in either case, to decide how to behave.
        @param startAfter: A C{list} of C{int} job ids that must complete
            (either successully or unsuccessully, it doesn't matter) before
            steps in the current specification may start. If C{None}, steps in
            the current specification may start immediately.
        """
        step = steps[stepName]
        step["tasks"] = defaultdict(set)
        step["skip"] = skip
        scriptArgsStr = " ".join(map(str, scriptArgs)) if scriptArgs else ""
        if scriptArgs:
            # Single quote each script arg so shell metacharacters and
            # whitespace are preserved.
            args = []
            for arg in map(str, scriptArgs):
                if "'" in arg:
                    raise SchedulingError(
                        'Script argument "%s" contains a single quote, which '
                        "is currently not supported." % arg
                    )
                else:
                    args.append("'%s'" % arg)
            scriptArgsStr = " ".join(args)
        else:
            scriptArgsStr = ""

        if step.get("error step", False):
            separator = "?"
            after = "afternotok"
        else:
            separator = ","
            after = "afterok"

        # taskDependencies is keyed by task name. These are the tasks
        # started by the steps that the current step depends on.  Its
        # values are sets of SLURM job ids the tasks that step started and
        # which this step therefore depends on.
        step["taskDependencies"] = taskDependencies = defaultdict(set)
        for stepName in step.get("dependencies", ()):
            for taskName, jobIds in steps[stepName]["tasks"].items():
                taskDependencies[taskName].update(jobIds)

        if taskDependencies:
            if "collect" in step:
                # This step is a 'collector'. I.e., it is dependent on all
                # tasks from all its dependent steps and cannot run until
                # they have all finished. We will only run the script once,
                # and tell it about all job ids for all tasks that are
                # depended on.
                env = environ.copy()
                env["SP_ORIGINAL_ARGS"] = scriptArgsStr
                env["SP_SKIP"] = env["SP_SIMULATE"] = str(int(skip))
                dependencies = separator.join(
                    sorted(
                        ("%s:%d" % (after, jobId))
                        for jobIds in taskDependencies.values()
                        for jobId in jobIds
                    )
                )
                env["SP_DEPENDENCY_ARG"] = "--dependency=" + dependencies
                self._runStepScript(step, sorted(taskDependencies), env)
            else:
                # The script for this step gets run once for each task in the
                # steps it depends on.
                for taskName in sorted(taskDependencies):
                    env = environ.copy()
                    env["SP_ORIGINAL_ARGS"] = scriptArgsStr
                    env["SP_SKIP"] = env["SP_SIMULATE"] = str(int(skip))
                    jobIds = steps[stepName]["tasks"][taskName]
                    dependencies = separator.join(
                        sorted(("%s:%d" % (after, jobId)) for jobId in jobIds)
                    )
                    if dependencies:
                        env["SP_DEPENDENCY_ARG"] = "--dependency=" + dependencies
                    else:
                        env.pop("SP_DEPENDENCY_ARG", None)
                    self._runStepScript(step, [taskName], env)
        else:
            # Either this step has no dependencies or the steps it is
            # dependent on did not start any tasks.
            env = environ.copy()

            if startAfter:
                dependencies = separator.join(
                    sorted(("%s:%d" % (after, jobId)) for jobId in startAfter)
                )
                env["SP_DEPENDENCY_ARG"] = "--dependency=" + dependencies
            else:
                env.pop("SP_DEPENDENCY_ARG", None)

            if "dependencies" in step:
                # The step has dependencies, but the dependent steps did
                # not start any tasks. Run the step as though there were no
                # dependencies.
                args = []
            else:
                # The step has no dependencies. Run it with the original
                # command line arguments and put any --startAfter job ids
                # into the SP_DEPENDENCY_ARG environment variable.
                args = [] if scriptArgs is None else list(map(str, scriptArgs))

            env["SP_ORIGINAL_ARGS"] = scriptArgsStr
            env["SP_SKIP"] = env["SP_SIMULATE"] = str(int(skip))
            self._runStepScript(step, args, env)

        step["scheduledAt"] = time.time()

    def _runStepScript(self, step: dict, args: list[str], env: dict) -> None:
        """
        Run the script for a step, using a given environment and parse its
        output for tasks it scheduled via sbatch.

        @param step: A C{dict} with a job specification.
        @param env: A C{str} key to C{str} value environment for the script.
        @param args: A C{list} of command-line arguments.
        @raise SchedulingError: If a script outputs a task name more than once
            or if the step script cannot be executed.
        """

        # Record all SP_* environment variables available to the script.
        step["environ"] = dict((var, env[var]) for var in self.ENV_VARS if var in env)

        try:
            step["stdout"] = subprocess.check_output(
                [step["script"]] + args,
                cwd=step.get("cwd", "."),
                env=env,
                stdin=DEVNULL,
                universal_newlines=True,
            )
        except subprocess.CalledProcessError as e:
            import sys

            if sys.version_info >= (3, 5):
                raise SchedulingError(
                    "Could not execute step '%s' script '%s' in directory "
                    "'%s'. Attempted command: '%s'. Exit status: %s. Standard "
                    "output: '%s'. Standard error: '%s'."
                    % (
                        step["name"],
                        step["script"],
                        step.get("cwd", "."),
                        e.cmd,
                        e.returncode,
                        e.output,
                        e.stderr,
                    )
                )
            else:
                raise SchedulingError(
                    "Could not execute step '%s' script '%s' in directory "
                    "'%s'. Attempted command: '%s'. Exit status: %s."
                    % (
                        step["name"],
                        step["script"],
                        step.get("cwd", "."),
                        e.cmd,
                        e.returncode,
                    )
                )
        except OSError as e:
            command = " ".join([step["script"]] + args)
            raise SchedulingError(
                "Could not execute step '%s' script '%s' in directory "
                "'%s'. Attempted command: '%s'. Error: %s"
                % (step["name"], step["script"], step.get("cwd", "."), command, e)
            )

        # Look at all output lines for task names and SLURM job ids created
        # (if any) by this script. Ignore any non-matching output.
        tasks = step["tasks"]
        for line in step["stdout"].split("\n"):
            match = self.TASK_NAME_LINE.match(line)
            if match:
                taskName = match.group(1)
                # The job ids follow the 'TASK:' string and the task name.
                # If they contain duplicates we consider it an error.
                try:
                    jobIds = list(map(int, line[match.end(1) :].split()))
                except ValueError:
                    raise SchedulingError(
                        "Task name %r was output with non-numeric job ids by "
                        "%r script in step named %r. Output line was %r"
                        % (taskName, step["script"], step["name"], line)
                    )
                if len(jobIds) != len(set(jobIds)):
                    raise SchedulingError(
                        "Task name %r was output with a duplicate in its "
                        "job ids %r by %r script in step named %r"
                        % (taskName, jobIds, step["script"], step["name"])
                    )
                tasks[taskName].update(jobIds)

    def _checkRuntime(
        self,
        steps: dict,
        firstStep: Optional[str] = None,
        lastStep: Optional[str] = None,
        skip: Optional[set[str]] = None,
        nice: Optional[int] = None,
    ) -> None:
        """
        Check that a proposed scheduling makes sense.

        @param steps: An C{OrderedDict} of specification steps, keyed by step
            name.
        @param firstStep: If not C{None}, the name of the first specification
            step to execute.
        @param lastStep: If not C{None}, the name of the last specification
            step to execute.
        @param skip: A C{set} of C{str} step names that should be skipped.
        @param nice: An C{int} nice (priority) value, in the range
            self.NICE_HIGHEST to self.NICE_LOWEST. Note that only privileged
            users can specify a negative adjustment.
        @raise SchedulingError: if the last step occurs before the first, if
            the last or first step are unknown, if asked to skip a
            non-existent step, or if C{nice} is not numeric or is out of its
            allowed range (see above).
        @return: An C{OrderedDict} keyed by specification step name,
            with values that are step C{dict}s. This provides convenient /
            direct access to steps by name.
        """
        firstStepFound = False

        if firstStep is not None and firstStep not in steps:
            raise SchedulingError(
                "First step %r not found in specification" % firstStep
            )

        if lastStep is not None and lastStep not in steps:
            raise SchedulingError("Last step %r not found in specification" % lastStep)

        if nice is not None:
            try:
                nice = int(nice)
            except ValueError:
                raise SchedulingError("Nice (priority) value %r is not numeric" % nice)
            else:
                if nice < self.NICE_HIGHEST or nice > self.NICE_LOWEST:
                    raise SchedulingError(
                        "Nice (priority) value %r is outside the allowed "
                        "[%d, %d] range" % (nice, self.NICE_HIGHEST, self.NICE_LOWEST)
                    )

        for step in steps.values():
            if step["name"] == firstStep:
                firstStepFound = True

            if step["name"] == lastStep:
                if firstStep is not None and not firstStepFound:
                    raise SchedulingError(
                        "Last step (%r) occurs before first step (%r) in "
                        "the specification" % (lastStep, firstStep)
                    )

        if skip:
            unknownSteps = skip - set(steps)
            if unknownSteps:
                raise SchedulingError(
                    "Unknown skip step%s (%s) passed to schedule"
                    % (
                        "" if len(unknownSteps) == 1 else "s",
                        ", ".join(sorted(unknownSteps)),
                    )
                )
