from unittest import TestCase
from unittest.mock import patch

from slurm_pipeline.error import SAcctError
from slurm_pipeline.sacct import SAcct


class TestSAcct(TestCase):
    """
    Tests for the slurm_pipeline.sacct.SAcct class.
    """

    @patch("subprocess.check_output")
    def testSacctNotFound(self, subprocessMock):
        """
        When an attempt to run sacct fails due to an OSError of some kind, an
        SAcctError must be raised.
        """
        subprocessMock.side_effect = OSError("No such file or directory")
        error = (
            r"^Encountered OSError \(No such file or directory\) when running "
            "'sacct -P --format JobId,JobName,State,Elapsed,Nodelist "
            "--jobs 35,40'$"
        )
        self.assertRaisesRegex(SAcctError, error, SAcct, {35, 40})

    @patch("subprocess.check_output")
    def testSacctCalledAsExpectedWhenNoArgsPassed(self, subprocessMock):
        """
        When no sacct field names are passed, it must be called as expected.
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "1|name|COMPLETED|04:32:00|cpu-3\n"
            "2|name|FAILED|05:11:37|cpu-4\n"
        )
        SAcct({1, 2})
        subprocessMock.assert_called_once_with(
            [
                "sacct",
                "-P",
                "--format",
                "JobId,JobName,State,Elapsed,Nodelist",
                "--jobs",
                "1,2",
            ],
            universal_newlines=True,
        )

    @patch("subprocess.check_output")
    def testSacctFailsToReturnAllJobIds(self, subprocessMock):
        """
        If sacct doesn't mention a needed job id, an SAcctError must be raised.
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "1|name|COMPLETED|04:32:00|cpu-3\n"
            "2|name|FAILED|05:11:37|cpu-4\n"
        )

        error = "^sacct did not return information about the following job " "id: 3$"
        self.assertRaisesRegex(SAcctError, error, SAcct, {1, 2, 3})

    @patch("subprocess.check_output")
    def testSacctCalledAsExpectedWhenFieldNamesPassed(self, subprocessMock):
        """
        When sacct field names are passed, sacct must be called as specified
        and the correct fields and values must be added to the SAcct instance
        'jobs' dict.
        """
        subprocessMock.return_value = (
            "JobID|Color|Year\n" "1|red|1968\n" "2|green|2011\n"
        )
        s = SAcct({1, 2}, fieldNames="Color,Year")
        subprocessMock.assert_called_once_with(
            ["sacct", "-P", "--format", "JobId,Color,Year", "--jobs", "1,2"],
            universal_newlines=True,
        )
        self.assertEqual({"color": "red", "year": "1968"}, s.jobs[1])
        self.assertEqual({"color": "green", "year": "2011"}, s.jobs[2])

    @patch("subprocess.check_output")
    def testRepeatJobId(self, subprocessMock):
        """
        When the sacct output contains a repeated job id, an SAcctError must
        be raised.
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "1|name|COMPLETED|04:32:00|(none)\n"
            "1|name|FAILED|05:11:37|cpu-4\n"
        )
        error = (
            "^Job id 1 found more than once in 'sacct -P --format "
            "JobId,JobName,State,Elapsed,Nodelist --jobs 1' output$"
        )
        self.assertRaisesRegex(SAcctError, error, SAcct, {1})

    @patch("subprocess.check_output")
    def testJobsDict(self, subprocessMock):
        """
        The jobs dict on an SAcct instance must be set correctly if there
        is no error in the input.
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "1|name1|COMPLETED|04:32:00|(none)\n"
            "2|name2|FAILED|05:11:37|cpu-4\n"
        )
        sa = SAcct({1, 2})
        self.assertEqual(
            {
                1: {
                    "elapsed": "04:32:00",
                    "jobname": "name1",
                    "state": "COMPLETED",
                    "nodelist": "(none)",
                },
                2: {
                    "elapsed": "05:11:37",
                    "jobname": "name2",
                    "state": "FAILED",
                    "nodelist": "cpu-4",
                },
            },
            sa.jobs,
        )

    @patch("subprocess.check_output")
    def testJobsDictWithSecondHeaderLine(self, subprocessMock):
        """
        The jobs dict on an SAcct instance must be set correctly if the
        input for some reason contains a second header line (as is printed,
        for some reason, when you call sacct with no arguments).
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "----- ----- ----- ----- -----\n"
            "1|name1|COMPLETED|04:32:00|(none)\n"
            "2|name2|FAILED|05:11:37|cpu-4\n"
        )
        sa = SAcct({1, 2})
        self.assertEqual(
            {
                1: {
                    "elapsed": "04:32:00",
                    "jobname": "name1",
                    "state": "COMPLETED",
                    "nodelist": "(none)",
                },
                2: {
                    "elapsed": "05:11:37",
                    "jobname": "name2",
                    "state": "FAILED",
                    "nodelist": "cpu-4",
                },
            },
            sa.jobs,
        )

    @patch("subprocess.check_output")
    def testJobsDictWithJobIdsContainingDots(self, subprocessMock):
        """
        The jobs dict on an SAcct instance must be set correctly if the
        input contains job ids that have dots in them. Only the lines with
        job ids that do not have dots should be processed.
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "1|name1|COMPLETED|04:32:00|cpu-0\n"
            "1.batch|name1|COMPLETED|04:00:00|cpu-2\n"
            "1.extern|name1|COMPLETED|03:00:00|cpu-3\n"
            "2.batch|name2|FAILED|06:11:37|cpu-5\n"
            "2|name2|FAILED|05:11:37|cpu-4\n"
        )
        sa = SAcct({1, 2})
        self.assertEqual(
            {
                1: {
                    "elapsed": "04:32:00",
                    "jobname": "name1",
                    "state": "COMPLETED",
                    "nodelist": "cpu-0",
                },
                2: {
                    "elapsed": "05:11:37",
                    "jobname": "name2",
                    "state": "FAILED",
                    "nodelist": "cpu-4",
                },
            },
            sa.jobs,
        )

    @patch("subprocess.check_output")
    def testSummarize(self, subprocessMock):
        """
        It must be possible to get a summary of a job's status.
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "1|name|COMPLETED|04:32:00|cpu-3\n"
            "2|name|FAILED|05:11:37|cpu-4\n"
            "3|name|FINISHED|05:13:00|cpu-6\n"
        )
        sa = SAcct({1, 2, 3})
        self.assertEqual(
            "JobName=name, State=COMPLETED, Elapsed=04:32:00, Nodelist=cpu-3",
            sa.summarize(1),
        )
        self.assertEqual(
            "JobName=name, State=FAILED, Elapsed=05:11:37, Nodelist=cpu-4",
            sa.summarize(2),
        )
        self.assertEqual(
            "JobName=name, State=FINISHED, Elapsed=05:13:00, Nodelist=cpu-6",
            sa.summarize(3),
        )

    @patch("subprocess.check_output")
    def testSummarizePreservesFieldNameCase(self, subprocessMock):
        """
        The summary of a job must preserve the case of the field names
        provided by the user.
        """
        subprocessMock.return_value = (
            "JobID|State|Elapsed|Nodelist\n" "1|COMPLETED|04:32:00|cpu-3\n"
        )
        sa = SAcct({1}, fieldNames="STATE,eLAPSED,Nodelist")
        self.assertEqual(
            "STATE=COMPLETED, eLAPSED=04:32:00, Nodelist=cpu-3", sa.summarize(1)
        )

    @patch("subprocess.check_output")
    def testFinished(self, subprocessMock):
        """
        The 'finished' method must function as expected.
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "1|name|RUNNING|04:32:00|(none)\n"
            "2|name|FAILED|05:11:37|cpu-4\n"
        )
        sa = SAcct({1, 2})
        self.assertFalse(sa.finished(1))
        self.assertTrue(sa.finished(2))

    @patch("subprocess.check_output")
    def testFailed(self, subprocessMock):
        """
        The 'failed' method must function as expected.
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "1|name|COMPLETED|04:32:00|(none)\n"
            "2|name|FAILED|05:11:37|cpu-4\n"
        )
        sa = SAcct({1, 2})
        self.assertFalse(sa.failed(1))
        self.assertTrue(sa.failed(2))

    @patch("subprocess.check_output")
    def testCompleted(self, subprocessMock):
        """
        The 'completed' method must function as expected.
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "1|name|RUNNING|04:32:00|(none)\n"
            "2|name|COMPLETED|05:11:37|cpu-4\n"
        )
        sa = SAcct({1, 2})
        self.assertFalse(sa.completed(1))
        self.assertTrue(sa.completed(2))

    @patch("subprocess.check_output")
    def testState(self, subprocessMock):
        """
        The 'state' method must function as expected.
        """
        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "1|name|RUNNING|04:32:00|(none)\n"
            "2|name|COMPLETED|05:11:37|cpu-4\n"
        )
        sa = SAcct({1, 2})
        self.assertEqual("RUNNING", sa.state(1))
        self.assertTrue("COMPLETED", sa.state(2))
