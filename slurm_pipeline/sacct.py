from os import environ
import subprocess
from collections import defaultdict

from .error import SAcctError


class SAcct:
    """
    Fetch information about job id status from sacct.

    @param jobIds: A C{set} of C{int} job ids to retrieve accounting information for.
    @param fieldNames: A C{list} of C{str} job field names to obtain from
        sacct. If C{None}, C{self.DEFAULT_FIELD_NAMES} will be used. See man
        sacct for the full list of possible field names.
    """

    DEFAULT_FIELD_NAMES = "JobName,State,Elapsed,Nodelist"

    def __init__(self, jobIds, fieldNames=None):
        self.fieldNames = (
            fieldNames
            or environ.get("SP_STATUS_FIELD_NAMES")
            or self.DEFAULT_FIELD_NAMES
        )
        self.jobs = self._callSacct(jobIds) if jobIds else {}

    def _callSacct(self, jobIds):
        """
        Call sacct to collect information about the job ids of interest.

        @param jobIds: A C{set} of C{int} job ids to get accounting information for.
        """
        # Make a copy of our argument, seeing as we are going to modify it.
        jobIds = set(jobIds)
        jobs = defaultdict(dict)
        args = [
            "sacct",
            "-P",
            "--format",
            "JobId," + self.fieldNames,
            "--jobs",
            ",".join(map(str, sorted(jobIds))),
        ]
        try:
            out = subprocess.check_output(args, universal_newlines=True)
        except OSError as e:
            raise SAcctError(
                "Encountered OSError (%s) when running '%s'" % (e, " ".join(args))
            )

        fieldNamesLower = tuple(map(str.lower, self.fieldNames.split(",")))

        for count, line in enumerate(out.split("\n")):
            if count == 0 or (count == 1 and line and line[0] == "-"):
                # First or second header line. When sacct is run with no
                # arguments it for some reason prints a second header line
                # that consists of hyphens and spaces. Check for that just
                # in case it prints it under other circumstances.
                continue
            elif line:
                fields = line.split("|")
                if fields[0].find(".") > -1:
                    # Ignore lines that have a job id like 1153494.extern
                    continue
                jobId = int(fields[0])
                if jobId in jobs:
                    raise SAcctError(
                        "Job id %d found more than once in '%s' output"
                        % (jobId, " ".join(args))
                    )
                if jobId in jobIds:
                    jobIds.remove(jobId)
                    fields.pop(0)
                    jobInfo = jobs[jobId]
                    for fieldName, value in zip(fieldNamesLower, fields):
                        jobInfo[fieldName] = value

        if jobIds:
            raise SAcctError(
                "sacct did not return information about the following job "
                "id%s: %s"
                % (
                    "" if len(jobIds) == 1 else "s",
                    ", ".join(map(str, sorted(jobIds))),
                )
            )

        return jobs

    def finished(self, jobId):
        """
        Has a job finished yet?

        @param jobId: An C{int} job id.
        @raise KeyError: If the job id cannot be found.
        @return: A C{bool} indicating whether the job has finished.
        """
        return self.jobs[jobId]["state"] not in {"PENDING", "RUNNING"}

    def failed(self, jobId):
        """
        Did a job fail?

        @param jobId: An C{int} job id.
        @raise KeyError: If the job id cannot be found.
        @return: A C{bool} indicating whether the job failed.
        """
        return self.jobs[jobId]["state"] == "FAILED"

    def completed(self, jobId):
        """
        Did a job complete?

        @param jobId: An C{int} job id.
        @raise KeyError: If the job id cannot be found.
        @return: A C{bool} indicating whether the job completed.
        """
        return self.jobs[jobId]["state"] == "COMPLETED"

    def state(self, jobId):
        """
        Get a job's state.

        @param jobId: An C{int} job id.
        @raise KeyError: If the job id cannot be found.
        @return: The C{str} job state.
        """
        return self.jobs[jobId]["state"]

    def summarize(self, jobId):
        """
        Summarize a job's state.

        @param jobId: An C{int} job id.
        @raise KeyError: If the job has not yet terminated.
        @return: a C{str} describing the job's state.
        """
        jobInfo = self.jobs[jobId]
        return ", ".join(
            "%s=%s" % (fieldName, jobInfo[fieldName.lower()])
            for fieldName in self.fieldNames.split(",")
        )
