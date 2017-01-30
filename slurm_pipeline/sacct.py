from os import getlogin
import subprocess

from error import SAcctError
from datetime import datetime, timedelta

class SAcct(object):
    """
    Fetch information about job id status from sacct.

    @param sacctArgs: A C{list} of C{str} arguments to pass to sacct
        (including the 'sacct' command itself). If C{None}, the user's
        login name will be appended to sacct -u.
    """
    def __init__(self, sacctArgs=None):
        starttime = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        args = sacctArgs or ['sacct', '-p', '-l', '-u', getlogin(), '-S', starttime]
        try:
            out = subprocess.check_output(args, universal_newlines=True)
        except OSError as e:
            raise SAcctError("Encountered OSError (%s) when running '%s'" %
                              (e, ' '.join(args)))

        columnInfo = {
            'JobID': {
                'attr': 'jobid',
                'offset': None,
            },
            'Elapsed': {
                'attr': 'elapsed',
                'offset': None,
            },
            'State': {
                'attr': 'state',
                'offset': None,
            }
        }

        jobs = {}

        for count, line in enumerate(out.split('\n')):
            fields = line.split('|')
            if count == 0:
                # Process header line.
                colsFound = 0
                for offset, title in enumerate(fields):
                    if title in columnInfo:
                        if columnInfo[title]['offset'] is not None:
                            raise SAcctError(
                                "Multiple columns with title %r found in '%s' "
                                'output' % (title, ' '.join(args)))
                        else:
                            columnInfo[title]['offset'] = offset
                            colsFound += 1
                if colsFound != len(columnInfo):
                    notFound = [title for title in columnInfo
                                if columnInfo[title]['offset'] is None]
                    raise SAcctError(
                        "Required column%s (%s) not found in '%s' "
                        'output' % ('' if len(notFound) == 1 else 's',
                                    ', '.join(sorted(notFound)),
                                    ' '.join(args)))
            elif count == 1:
                # header separation line
                continue
            elif line:
                # ignore job steps...
                jobId = int(fields[columnInfo['JobID']['offset']].split('.')[0])
                if jobId in jobs:
                    continue
                    # FIXME...
                    #raise SAcctError(
                    #    "Job id %d found more than once in '%s' "
                    #    'output' % (jobId, ' '.join(args)))
                jobInfo = {}
                for title in columnInfo:
                    if title != 'JobID':
                        jobInfo[columnInfo[title]['attr']] = fields[columnInfo[title]['offset']]
                jobs[jobId] = jobInfo

        self.jobs = jobs

    def finished(self, jobId):
        return self.jobs[jobId]['state'] not in ['PENDING', 'RUNNING']

    def failed(self, jobId):
        return self.jobs[jobId]['state'] == 'FAILED'

    def completed(self, jobId):
        return self.jobs[jobId]['state'] == 'COMPLETED'

    def state(self, jobId):
        return self.jobs[jobId]['state']

    def summarize(self, jobId):
        """
        Summarize a job's state.

        @param jobId: An C{int} job id.
        @raise KeyError: If the job has not yet terminated.
        @return: a C{str} describing the job's state.
        """
        jobInfo = self.jobs[jobId]
        state = jobInfo['state']
        return 'State=%s Elapsed=%s' % (
            jobInfo['state'], jobInfo['elapsed'])
