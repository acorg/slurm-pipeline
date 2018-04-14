from os import getlogin
import subprocess
from collections import defaultdict

from .error import SAcctError
from .utils import secondsToTime


class SAcct(object):
    """
    Fetch information about job id status from sacct.

    @param specification: A C{dict} containing an execution specification.
    @param fieldNames: A C{list} of C{str} job field names to obtain from
        sacct. If C{None}, C{self.DEFAULT_FIELD_NAMES} will be used. See man
        sacct for the full list of possible field names.
    """

    DEFAULT_FIELD_NAMES = ('State', 'Elapsed', 'Nodelist')

    def __init__(self, specification, fieldNames=None):
        self.fieldNames = (tuple(fieldNames) if fieldNames
                           else self.DEFAULT_FIELD_NAMES)

        startTime = secondsToTime(specification['scheduledAt'] - 1.0,
                                  sacctCompatible=True)
        args = [
            # Use specification.get here because the 'user' key will
            # not be present in older versions of our status output
            # (added in 1.1.14).
            'sacct', '-P', '-u', specification.get('user', getlogin()),
            '--format', 'JobId,' + ','.join(self.fieldNames), '-S', startTime]
        try:
            out = subprocess.check_output(args, universal_newlines=True)
        except OSError as e:
            raise SAcctError("Encountered OSError (%s) when running '%s'" %
                             (e, ' '.join(args)))

        self.jobs = jobs = defaultdict(dict)
        fieldNamesLower = tuple(map(str.lower, self.fieldNames))

        for count, line in enumerate(out.split('\n')):
            if count == 0 or (count == 1 and line and line[0] == '-'):
                # First or second header line. When sacct is run with no
                # arguments it for some reason prints a second header line
                # that consists of hyphens and spaces. Check for that just
                # in case it prints it under other circumstances.
                continue
            elif line:
                fields = line.split('|')
                if fields[0].find('.') > -1:
                    # Ignore lines that have a job id like 1153494.extern
                    continue
                jobId = int(fields[0])
                if jobId in jobs:
                    raise SAcctError(
                        "Job id %d found more than once in '%s' output" %
                        (jobId, ' '.join(args)))
                fields.pop(0)
                jobInfo = jobs[jobId]
                for fieldName, value in zip(fieldNamesLower, fields):
                    jobInfo[fieldName] = value

    def finished(self, jobId):
        """
        Has a job finished yet?

        @param jobId: An C{int} job id.
        @raise KeyError: If the job id cannot be found.
        @return: A C{bool} indicating whether the job has finished.
        """
        return self.jobs[jobId]['state'] not in {'PENDING', 'RUNNING'}

    def failed(self, jobId):
        """
        Did a job fail?

        @param jobId: An C{int} job id.
        @raise KeyError: If the job id cannot be found.
        @return: A C{bool} indicating whether the job failed.
        """
        return self.jobs[jobId]['state'] == 'FAILED'

    def completed(self, jobId):
        """
        Did a job complete?

        @param jobId: An C{int} job id.
        @raise KeyError: If the job id cannot be found.
        @return: A C{bool} indicating whether the job completed.
        """
        return self.jobs[jobId]['state'] == 'COMPLETED'

    def state(self, jobId):
        """
        Get a job's state.

        @param jobId: An C{int} job id.
        @raise KeyError: If the job id cannot be found.
        @return: The C{str} job state.
        """
        return self.jobs[jobId]['state']

    def summarize(self, jobId):
        """
        Summarize a job's state.

        @param jobId: An C{int} job id.
        @raise KeyError: If the job has not yet terminated.
        @return: a C{str} describing the job's state.
        """
        jobInfo = self.jobs[jobId]
        return ', '.join(
            '%s=%s' % (fieldName, jobInfo[fieldName.lower()])
            for fieldName in self.fieldNames)
