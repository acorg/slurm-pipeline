import pandas as pd

from .base import SlurmPipelineBase
from .error import SpecificationError
from .sacct import SAcct
from .utils import secondsToTime, elapsedToSeconds


class SlurmPipelineStatus(SlurmPipelineBase):
    """
    Read a pipeline execution status specification and supply methods for
    examining job ids, step status, etc.

    @param specification: Either a C{str} giving the name of a file containing
        a JSON execution specification, or a C{dict} holding a correctly
        formatted execution specification.
    @param fieldNames: A C{list} of C{str} job field names to obtain from
        sacct. If C{None}, a default set will be used (determined by sacct.py).
        See man sacct for the full list of possible field names.
    """

    def __init__(self, specification, fieldNames=None):
        SlurmPipelineBase.__init__(self, specification)
        jobIds = self.jobs() | set(self.specification["startAfter"] or ())
        self.sacct = SAcct(jobIds, fieldNames=fieldNames)

    @staticmethod
    def checkSpecification(specification):
        """
        Check an execution specification is as expected.

        @param specification: A C{dict} containing an execution specification.
        @raise SpecificationError: if there is anything wrong with the
            specification.
        """
        if "scheduledAt" not in specification:
            raise SpecificationError(
                "The specification status has no top-level 'scheduledAt' key"
            )

        SlurmPipelineBase.checkSpecification(specification)

    def finalJobs(self):
        """
        Get the job ids emitted by the final steps of a specification.

        @return: A C{set} of C{int} job ids.
        """
        steps = self.specification["steps"]
        result = set()
        for stepName in self.finalSteps():
            for jobIds in steps[stepName]["tasks"].values():
                result.update(jobIds)
        return result

    def finishedJobs(self):
        """
        Get the ids of finished jobs emitted by a specification.

        @return: A C{set} of C{int} finished job ids.
        """
        finished = self.sacct.finished
        result = set()
        for stepName in self.specification["steps"]:
            result.update(
                [jobid for jobid in self.stepJobIds(stepName) if finished(jobid)]
            )
        return result

    def unfinishedJobs(self):
        """
        Get the ids of unfinished jobs emitted by a specification.

        @return: A C{set} of C{int} unfinished job ids.
        """
        finished = self.sacct.finished
        result = set()
        for stepName in self.specification["steps"]:
            result.update(
                [jobid for jobid in self.stepJobIds(stepName) if not finished(jobid)]
            )
        return result

    def jobs(self):
        """
        Get the ids of all jobs emitted by a specification.

        @return: A C{set} of C{int} job ids.
        """
        result = set()
        for stepName in self.specification["steps"]:
            jobIds = self.stepJobIds(stepName)
            result.update(jobIds)
        return result

    def stepDependentJobIds(self, stepName):
        """
        Which dependent jobs must a step wait on?

        @param stepName: The C{str} name of a step.
        @return: A C{set} of C{int} job ids that a step is dependent on.
        """
        step = self.specification["steps"][stepName]
        jobIds = set()
        for taskJobIds in step["taskDependencies"].values():
            jobIds.update(taskJobIds)
        return jobIds

    def stepJobIds(self, stepName):
        """
        Which jobs did a step emit?

        @param stepName: The C{str} name of a step.
        @return: A C{set} of C{int} emitted job ids for the step.
        """
        jobIds = set()
        step = self.specification["steps"][stepName]
        for taskJobIds in step["tasks"].values():
            jobIds.update(taskJobIds)
        return jobIds

    def _stepSummary(self, stepName):
        """
        Collect information about a step.

        @param stepName: The C{str} name of a step.
        @return: A C{list} of C{str}s with information about the step.
        """
        result = []
        append = result.append
        step = self.specification["steps"][stepName]

        # Summarize step dependencies, if any.
        try:
            dependencyCount = len(step["dependencies"])
        except KeyError:
            dependencyCount = 0

        if dependencyCount:
            append(
                "  %d step %s: %s"
                % (
                    dependencyCount,
                    "dependency" if dependencyCount == 1 else "dependencies",
                    ", ".join(step["dependencies"]),
                )
            )

            taskDependencyCount = len(step["taskDependencies"])

            jobIds = self.stepDependentJobIds(stepName)
            jobIdsCount = len(jobIds)
            jobIdsFinished = [jobId for jobId in jobIds if self.sacct.finished(jobId)]
            jobIdsFinishedCount = len(jobIdsFinished)

            append(
                "    Dependent on %d task%s emitted by the dependent "
                "step%s"
                % (
                    taskDependencyCount,
                    "" if taskDependencyCount == 1 else "s",
                    "" if dependencyCount == 1 else "s",
                )
            )

            if jobIdsCount:
                append(
                    "    Summary: %d job%s started by the dependent task%s, "
                    "of which %d (%.2f%%) are finished"
                    % (
                        jobIdsCount,
                        "" if jobIdsCount == 1 else "s",
                        "" if dependencyCount == 1 else "s",
                        jobIdsFinishedCount,
                        100.0
                        if jobIdsCount == 0
                        else (jobIdsFinishedCount / jobIdsCount * 100.0),
                    )
                )
            elif taskDependencyCount:
                append(
                    "    Summary: 0 jobs started by the dependent "
                    "task%s" % ("" if taskDependencyCount == 1 else "s")
                )

            if taskDependencyCount:
                append("    Dependent tasks:")
                for taskName in sorted(step["taskDependencies"]):
                    jobIds = step["taskDependencies"][taskName]
                    append("      %s" % taskName)
                    for jobId in sorted(jobIds):
                        append(
                            "        Job %d: %s" % (jobId, self.sacct.summarize(jobId))
                        )
        else:
            assert len(step["taskDependencies"]) == 0
            append("  No dependencies.")

        # Summarize tasks launched by this step, if any.
        taskCount = len(step["tasks"])

        if taskCount:
            append(
                "  %d task%s emitted by this step"
                % (taskCount, "" if taskCount == 1 else "s")
            )

            jobIds = self.stepJobIds(stepName)
            jobIdsCount = len(jobIds)
            jobIdsFinishedCount = [
                jobId for jobId in jobIds if self.sacct.finished(jobId)
            ]
            jobIdsFinishedCount = len(jobIdsFinishedCount)

            if jobIdsCount:
                append(
                    "    Summary: %d job%s started by %s, of which %d "
                    "(%.2f%%) are finished"
                    % (
                        jobIdsCount,
                        "" if jobIdsCount == 1 else "s",
                        "this task" if taskCount == 1 else "these tasks",
                        jobIdsFinishedCount,
                        100.0
                        if jobIdsCount == 0
                        else jobIdsFinishedCount / jobIdsCount * 100.0,
                    )
                )
            else:
                append(
                    "    Summary: 0 jobs started by %s"
                    % ("this task" if taskCount == 1 else "these tasks")
                )

            if taskCount:
                append("    Tasks:")
                for taskName in sorted(step["tasks"]):
                    jobIds = step["tasks"][taskName]
                    append("      %s" % taskName)
                    for jobId in sorted(jobIds):
                        append(
                            "        Job %d: %s" % (jobId, self.sacct.summarize(jobId))
                        )
        else:
            assert len(step["tasks"]) == 0
            append("  No tasks emitted by this step")

        result.extend(
            [
                "  Collect step: %s" % step.get("collect", "False"),
                "  Error step: %s" % step.get("error step", "False"),
                "  Working directory: %s" % step.get("cwd", "."),
                "  Scheduled at: %s" % secondsToTime(step["scheduledAt"]),
                "  Script: %s" % step["script"],
                "  Skip: %s" % step["skip"],
            ]
        )

        append("  Slurm pipeline environment variables:")
        for var in sorted(step["environ"]):
            append("    %s: %s" % (var, step["environ"][var]))

        return result

    def _stepsSummary(self):
        """
        Collect information summarizing all steps.

        @return: A C{list} of C{str}s with information about all steps.
        """
        summary = []
        append = summary.append
        steps = self.specification["steps"]
        totalJobIdsEmitted = totalJobIdsFinished = 0

        for stepName in steps:
            jobIdsEmitted = self.stepJobIds(stepName)
            jobIdsEmittedCount = len(jobIdsEmitted)
            jobIdsFinished = [
                jobId for jobId in jobIdsEmitted if self.sacct.finished(jobId)
            ]
            jobIdsFinishedCount = len(jobIdsFinished)
            totalJobIdsEmitted += jobIdsEmittedCount
            totalJobIdsFinished += jobIdsFinishedCount

            if jobIdsEmittedCount:
                percent = (
                    0.0
                    if jobIdsEmittedCount == 0
                    else jobIdsFinishedCount / jobIdsEmittedCount * 100.0
                )
                append(
                    "    %s: %d job%s emitted, %d (%.2f%%) finished"
                    % (
                        stepName,
                        jobIdsEmittedCount,
                        "" if jobIdsEmittedCount == 1 else "s",
                        jobIdsFinishedCount,
                        percent,
                    )
                )
            else:
                append("    %s: no jobs emitted" % stepName)

        percent = (
            100.0
            if totalJobIdsEmitted == 0
            else totalJobIdsFinished / totalJobIdsEmitted * 100.0
        )

        return [
            "Steps summary:",
            "  Number of steps: %d" % len(steps),
            "  Jobs emitted in total: %d" % totalJobIdsEmitted,
            "  Jobs finished: %d (%.2f%%)" % (totalJobIdsFinished, percent),
        ] + summary

    def toStr(self):
        """
        Get a printable summary of a status specification, including job
        status.

        @return: A C{str} representation of the status specification.
        """
        specification = self.specification
        # Use specification.get to get the username so we don't break if
        # we're run on a status file created before the username was being
        # stored (added in 2.0.0).
        result = [
            "Scheduled by: %s" % specification.get("user", "UNKNOWN"),
            "Scheduled at: %s" % secondsToTime(specification["scheduledAt"]),
            "Scheduling arguments:",
            "  First step: %s" % specification["firstStep"],
            "  Force: %s" % specification["force"],
            "  Last step: %s" % specification["lastStep"],
        ]
        append = result.append

        append("  Nice: %s" % specification.get("nice", "<None>"))
        append("  Sleep: %.2f" % specification.get("sleep", 0.0))

        if specification["scriptArgs"]:
            append("  Script arguments: %s" % " ".join(specification["scriptArgs"]))
        else:
            append("  Script arguments: <None>")

        if specification["skip"]:
            append("  Skip: %s" % ", ".join(specification["skip"]))
        else:
            append("  Skip: <None>")

        if specification["startAfter"]:
            startAfter = specification["startAfter"]
            nStartAfter = len(startAfter)
            finishedCount = len(
                [jobId for jobId in startAfter if self.sacct.finished(jobId)]
            )
            percent = finishedCount / nStartAfter * 100.0

            append(
                "  Start after the following %d job%s, of which %d (%.2f%%) "
                "%s finished:"
                % (
                    nStartAfter,
                    "" if nStartAfter == 1 else "s",
                    finishedCount,
                    percent,
                    "is" if finishedCount == 1 else "are",
                )
            )
            for jobId in startAfter:
                append("    Job %d: %s" % (jobId, self.sacct.summarize(jobId)))
        else:
            append("  Start after: <None>")

        # Summarize all steps, giving the number of jobs they started and
        # how many are finished.
        result.extend(self._stepsSummary())

        # Add information about each step in detail.
        for count, stepName in enumerate(self.specification["steps"], start=1):
            append("Step %d: %s" % (count, stepName))
            result.extend(self._stepSummary(stepName))

        return "\n".join(result)


class SlurmPipelineStatusCollection:
    """
    Manage SlurmPipelineStatus instances collected from the same pipeline.

    E.g., if you have a pipeline and you run ten samples through the pipeline, you
    can use this class to gather the SlurmPipelineStatus instances for each sample
    so you can treat them together. For this reason, the specifications passed must
    all result from running the same pipeline (i.e., have identical pipeline steps).

    @param specifications: An iterable of either a) C{str} or C{Path} instances, each
        giving the names of a file, containing a JSON execution specification, or b) a
        C{dict} holding a correctly formatted execution specification.
    @param names: If not C{None}, an iterable of C{str} names for the passed
        C{specifications}. These must be unique because they are used as dictionary
        keys. If C{None}, names "unnamed-1", "unnamed-2", etc. will be used.
    """

    def __init__(self, specifications, names=None):
        self.data = {}
        self.stepNames = None
        self.nonEmptyStepNames = []
        specifications = list(specifications)
        names = (
            list(names)
            if names
            else [f"unnamed-{i}" for i in range(len(specifications))]
        )

        if len(names) != len(specifications):
            raise ValueError(
                "The specifications and names lists are not the same lengths "
                f"({len(specifications)} != {len(names)})."
            )

        if len(set(names)) != len(names):
            raise ValueError(
                "The list of specification names contains at least one duplicate: "
                f"{names!r}."
            )

        for count, (specification, name) in enumerate(
            zip(specifications, names), start=1
        ):
            self.data[name] = SlurmPipelineStatus(specification)

            # Make sure the list of steps is the same for all specifications.
            theseSteps = list(self.data[name].specification["steps"])
            if self.stepNames:
                if self.stepNames != theseSteps:
                    raise ValueError(
                        f"The list of steps found in the first specification "
                        f"{self.stepNames!r} does not match that found in "
                        f"specification number {count}: {theseSteps!r}."
                    )
            else:
                self.stepNames = theseSteps

        names = []
        steps = []
        tasks = []
        jobIds = []
        statuses = []
        nodes = []
        elapsed = []
        seconds = []

        for name, status in self.data.items():
            for stepName, stepInfo in status.specification["steps"].items():
                for taskName, taskJobIds in stepInfo["tasks"].items():
                    for jobId in taskJobIds:
                        sacct = status.sacct.jobs[jobId]
                        names.append(name)
                        steps.append(stepName)
                        tasks.append(taskName)
                        jobIds.append(jobId)
                        statuses.append(sacct["state"])
                        nodes.append(sacct["nodelist"])

                        elapsedStr = sacct["elapsed"]
                        elapsed.append(elapsedStr)
                        seconds.append(elapsedToSeconds(elapsedStr))

        self.nonEmptyStepNames = [
            stepName for stepName in self.stepNames if stepName in steps]

        self.df = pd.DataFrame(
            {
                "name": names,
                "step": steps,
                "task": tasks,
                "jobId": jobIds,
                "status": statuses,
                "node": nodes,
                "elapsed": elapsed,
                "seconds": seconds,
            }
        )
