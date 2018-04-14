from unittest import TestCase
from six import assertRaisesRegex
from os import getlogin

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from slurm_pipeline.error import SAcctError
from slurm_pipeline.sacct import SAcct


class TestSAcct(TestCase):
    """
    Tests for the slurm_pipeline.sacct.SAcct class.
    """
    @patch('subprocess.check_output')
    def testSacctNotFound(self, subprocessMock):
        """
        When an attempt to run sacct fails due to an OSError of some kind, an
        SAcctError must be raised.
        """
        subprocessMock.side_effect = OSError('No such file or directory')
        error = (
            "^Encountered OSError \(No such file or directory\) when running "
            "'sacct -P -u %s --format JobId,State,Elapsed,Nodelist "
            "-S 1970-01-01T00:00:43'$" % getlogin())
        assertRaisesRegex(self, SAcctError, error,  SAcct, {'scheduledAt': 44})

    @patch('subprocess.check_output')
    def testSacctCalledAsExpectedWhenNoArgsPassed(self, subprocessMock):
        """
        When no sacct arguments are passed, it must be called as expected
        (with -u LOGIN_NAME).
        """
        subprocessMock.return_value = 'JobID|State|Elapsed|Nodelist\n'
        SAcct({'scheduledAt': 44})
        subprocessMock.assert_called_once_with(
            ['sacct', '-P', '-u', getlogin(), '--format',
             'JobId,State,Elapsed,Nodelist', '-S', '1970-01-01T00:00:43'],
            universal_newlines=True)

    @patch('subprocess.check_output')
    def testSacctCalledAsExpectedWhenFieldNamesPassed(self, subprocessMock):
        """
        When sacct field names are passed, sacct must be called as specified
        and the correct fields and values must be added to the SAcct instance
        'jobs' dict.
        """
        subprocessMock.return_value = (
            'JobID|Color|Year\n'
            '1|red|1968\n'
            '2|green|2011\n'
        )
        s = SAcct({'scheduledAt': 44}, fieldNames=('Color', 'Year'))
        subprocessMock.assert_called_once_with(
            ['sacct', '-P', '-u', getlogin(), '--format', 'JobId,Color,Year',
             '-S', '1970-01-01T00:00:43'], universal_newlines=True)
        self.assertEqual({'color': 'red', 'year': '1968'}, s.jobs[1])
        self.assertEqual({'color': 'green', 'year': '2011'}, s.jobs[2])

    @patch('subprocess.check_output')
    def testRepeatJobId(self, subprocessMock):
        """
        When the sacct output contains a repeated job id, an SAcctError must
        be raised.
        """
        subprocessMock.return_value = (
            'JobID|State|Elapsed|Nodelist\n'
            '1|COMPLETED|04:32:00|(none)\n'
            '1|FAILED|05:11:37|cpu-4\n'
        )
        error = ("^Job id 1 found more than once in 'sacct -P -u %s --format "
                 "JobId,State,Elapsed,Nodelist -S 1970-01-01T00:00:43' output$"
                 % getlogin())
        assertRaisesRegex(self, SAcctError, error,  SAcct, {'scheduledAt': 44})

    @patch('subprocess.check_output')
    def testJobsDict(self, subprocessMock):
        """
        The jobs dict on an SAcct instance must be set correctly if there
        is no error in the input.
        """
        subprocessMock.return_value = (
            'JobID|State|Elapsed|Nodelist\n'
            '1|COMPLETED|04:32:00|(none)\n'
            '2|FAILED|05:11:37|cpu-4\n'
        )
        sq = SAcct({'scheduledAt': 44})
        self.assertEqual(
            {
                1: {
                    'elapsed': '04:32:00',
                    'state': 'COMPLETED',
                    'nodelist': '(none)',
                },
                2: {
                    'elapsed': '05:11:37',
                    'state': 'FAILED',
                    'nodelist': 'cpu-4',
                },
            },
            sq.jobs
        )

    @patch('subprocess.check_output')
    def testFinished(self, subprocessMock):
        """
        It must be possible to tell whether a job has finished.
        """
        subprocessMock.return_value = (
            'JobID|State|Elapsed|Nodelist\n'
            '1|RUNNING|04:32:00|(none)\n'
            '3|FAILED|05:11:37|cpu-4\n'
        )
        sq = SAcct({'scheduledAt': 44})
        self.assertFalse(sq.finished(1))
        self.assertTrue(sq.finished(3))

    @patch('subprocess.check_output')
    def testSummarize(self, subprocessMock):
        """
        It must be possible to get a summary of a job's status.
        """
        subprocessMock.return_value = (
            'JobID|State|Elapsed|Nodelist\n'
            '1|COMPLETED|04:32:00|cpu-3\n'
            '2|FAILED|05:11:37|cpu-4\n'
            '3|FINISHED|05:13:00|cpu-6\n'
        )
        sq = SAcct({'scheduledAt': 100})
        self.assertEqual('State=COMPLETED, Elapsed=04:32:00, Nodelist=cpu-3',
                         sq.summarize(1))
        self.assertEqual('State=FAILED, Elapsed=05:11:37, Nodelist=cpu-4',
                         sq.summarize(2))
        self.assertEqual('State=FINISHED, Elapsed=05:13:00, Nodelist=cpu-6',
                         sq.summarize(3))
