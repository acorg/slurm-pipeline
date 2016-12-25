from os import getlogin
import subprocess

from slurm_pipeline.error import SQueueError


class SQueue(object):
    """
    Fetch information about job id status from squeue.

    @param squeueArgs: A C{list} of C{str} arguments to pass to squeue
        (including the 'squeue' command itself). If C{None}, the user's
        login name will be appended to squeue -u.
    """
    def __init__(self, squeueArgs=None):
        args = squeueArgs or ['squeue', '-u', getlogin()]
        try:
            out = subprocess.check_output(args, universal_newlines=True)
        except OSError as e:
            raise SQueueError("Encountered OSError (%s) when running '%s'" %
                              (e, ' '.join(args)))

        columnInfo = {
            'JOBID': {
                'attr': 'jobid',
                'offset': None,
            },
            'ST': {
                'attr': 'status',
                'offset': None,
            },
            'TIME': {
                'attr': 'time',
                'offset': None,
            },
            'NODELIST(REASON)': {
                'attr': 'nodelistReason',
                'offset': None,
            },
        }

        jobs = {}

        for count, line in enumerate(out.split('\n')):
            fields = line.split()
            if count == 0:
                # Process header line.
                colsFound = 0
                for offset, title in enumerate(fields):
                    if title in columnInfo:
                        if columnInfo[title]['offset'] is not None:
                            raise SQueueError(
                                "Multiple columns with title %r found in '%s' "
                                'output' % (title, ' '.join(args)))
                        else:
                            columnInfo[title]['offset'] = offset
                            colsFound += 1
                if colsFound != len(columnInfo):
                    notFound = [title for title in columnInfo
                                if columnInfo[title]['offset'] is None]
                    raise SQueueError(
                        "Required column%s (%s) not found in '%s' "
                        'output' % ('' if len(notFound) == 1 else 's',
                                    ', '.join(sorted(notFound)),
                                    ' '.join(args)))
            elif line:
                jobId = int(fields[columnInfo['JOBID']['offset']])
                if jobId in jobs:
                    raise SQueueError(
                        "Job id %d found more than once in '%s' "
                        'output' % (jobId, ' '.join(args)))
                jobInfo = {}
                for title in columnInfo:
                    if title != 'JOBID':
                        jobInfo[columnInfo[title]['attr']] = fields[
                            columnInfo[title]['offset']]
                jobs[jobId] = jobInfo

        self.jobs = jobs

    def finished(self, jobId):
        """
        Has a job finished?

        @param jobId: An C{int} job id.
        @return: a C{bool}, C{True} if the job has finished, C{False} if not.
        """
        return jobId not in self.jobs

    def summarize(self, jobId):
        """
        Summarize a job's status.

        @param jobId: An C{int} job id.
        @raise KeyError: If the job has already finished.
        @return: a C{str} describing the job's status.
        """
        try:
            jobInfo = self.jobs[jobId]
        except KeyError:
            return 'Finished'
        else:
            nodelistReason = jobInfo['nodelistReason']
            if nodelistReason.startswith('('):
                extra = 'Reason=%s' % nodelistReason[1:-1]
            else:
                extra = 'Nodelist=%s' % nodelistReason
            return 'Status=%s Time=%s %s' % (
                jobInfo['status'], jobInfo['time'], extra)
