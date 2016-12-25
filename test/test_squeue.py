from unittest import TestCase
from six import assertRaisesRegex
from os import getlogin

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from slurm_pipeline.error import SQueueError
from slurm_pipeline.squeue import SQueue


class TestSQueue(TestCase):
    """
    Tests for the slurm_pipeline.squeue.SQueue class.
    """
    @patch('subprocess.check_output')
    def testSQueueNotFound(self, subprocessMock):
        """
        When an attempt to run squeue fails due to an OSError, an SQueueError
        must be raised.
        """
        subprocessMock.side_effect = OSError('No such file or directory')
        error = (
            "^Encountered OSError \(No such file or directory\) when running "
            "'squeue -u %s'$" % getlogin())
        assertRaisesRegex(self, SQueueError, error,  SQueue)

    @patch('subprocess.check_output')
    def testAllColumnsMissing(self, subprocessMock):
        """
        When the squeue output does not contain any of the right column
        headings an SQueueError must be raised.
        """
        subprocessMock.return_value = 'Bad header\n'
        error = (
            '^Required columns \(JOBID, NODELIST\(REASON\), ST, TIME\) not '
            "found in 'squeue -u %s' output$" % getlogin())
        assertRaisesRegex(self, SQueueError, error,  SQueue)

    @patch('subprocess.check_output')
    def testSomeColumnsMissing(self, subprocessMock):
        """
        When the squeue output contains only some of the right column headings
        an SQueueError must be raised, indicating which columns were not found.
        """
        subprocessMock.return_value = 'JOBID ST\n'
        error = (
            '^Required columns \(NODELIST\(REASON\), TIME\) not found in '
            "'squeue -u %s' output$" % getlogin())
        assertRaisesRegex(self, SQueueError, error,  SQueue)

    @patch('subprocess.check_output')
    def testRepeatColumnName(self, subprocessMock):
        """
        When the squeue output contains a repeated column heading (among the
        headings we're interested in) an SQueueError must be raised.
        """
        subprocessMock.return_value = 'JOBID ST JOBID\n'
        error = (
            "^Multiple columns with title 'JOBID' found in 'squeue -u %s' "
            "output$" % getlogin())
        assertRaisesRegex(self, SQueueError, error,  SQueue)

    @patch('subprocess.check_output')
    def testSQueueCalledAsExpectedWhenNoArgsPassed(self, subprocessMock):
        """
        When no squeue arguments are passed, it must be called as expected
        (with -u LOGIN_NAME).
        """
        subprocessMock.return_value = 'JOBID ST TIME NODELIST(REASON)\n'
        SQueue()
        subprocessMock.assert_called_once_with(['squeue', '-u', getlogin()],
                                               universal_newlines=True)

    @patch('subprocess.check_output')
    def testSQueueCalledAsExpectedWhenArgsPassed(self, subprocessMock):
        """
        When squeue arguments are passed, it must be called as specified.
        """
        subprocessMock.return_value = 'JOBID ST TIME NODELIST(REASON)\n'
        SQueue(squeueArgs=['my-squeue', '--xxx', '--yyy'])
        subprocessMock.assert_called_once_with(
            ['my-squeue', '--xxx', '--yyy'], universal_newlines=True)

    @patch('subprocess.check_output')
    def testRepeatJobId(self, subprocessMock):
        """
        When the squeue output contains a repeated job id, an SQueueError must
        be raised.
        """
        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
            '1 R 4:32 (None)\n'
            '1 R 5:37 (None)\n'
        )
        error = ("^Job id 1 found more than once in 'squeue -u %s' output$" %
                 getlogin())
        assertRaisesRegex(self, SQueueError, error,  SQueue)

    @patch('subprocess.check_output')
    def testRepeatJobIdWithSqueueArgs(self, subprocessMock):
        """
        When the squeue output contains a repeated job id, an SQueueError must
        be raised with an error message showing how squeue was called,
        including when squeueArgs are given.
        """
        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
            '1 R 4:32 (None)\n'
            '1 R 5:37 (None)\n'
        )
        error = "^Job id 1 found more than once in 'my-squeue x y' output$"
        assertRaisesRegex(self, SQueueError, error,  SQueue,
                          squeueArgs=['my-squeue', 'x', 'y'])

    @patch('subprocess.check_output')
    def testJobsDict(self, subprocessMock):
        """
        The jobs dict on an SQueue instance must be set correctly if there
        is no error in the input.
        """
        subprocessMock.return_value = (
            'JOBID ST IGNORE TIME NODELIST(REASON)\n'
            '1     R  xxx    4:32 (None)\n'
            '2     S  yyy    5:37 cpu-1-b\n'
        )
        sq = SQueue()
        self.assertEqual(
            {
                1: {
                    'time': '4:32',
                    'status': 'R',
                    'nodelistReason': '(None)',
                },
                2: {
                    'time': '5:37',
                    'status': 'S',
                    'nodelistReason': 'cpu-1-b',
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
            'JOBID ST TIME NODELIST(REASON)\n'
            '1     R  4:32 (None)\n'
            '2     S  5:37 cpu-1-b\n'
        )
        sq = SQueue()
        self.assertFalse(sq.finished(1))
        self.assertTrue(sq.finished(3))

    @patch('subprocess.check_output')
    def testSummarize(self, subprocessMock):
        """
        It must be possible to get a summary of a job's status.
        """
        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
            '1     R  4:32 (None)\n'
            '2     S  5:37 cpu-1\n'
        )
        sq = SQueue()
        self.assertEqual('Status=R Time=4:32 Reason=None', sq.summarize(1))
        self.assertEqual('Status=S Time=5:37 Nodelist=cpu-1', sq.summarize(2))
        self.assertEqual('Finished', sq.summarize(3))
