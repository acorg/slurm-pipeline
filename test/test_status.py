from unittest import TestCase
from unittest.mock import patch

from slurm_pipeline.error import SpecificationError
from slurm_pipeline.status import SlurmPipelineStatus, SlurmPipelineStatusCollection


class TestSlurmPipelineStatus(TestCase):
    """
    Tests for the slurm_pipeline.status.SlurmPipelineStatus class.
    """

    def testNotScheduled(self):
        """
        If a specification without a top-level 'scheduledAt' key is passed to
        SlurmPipelineStatus, a SpecificationError must be raised.
        """
        error = "^The specification status has no top-level 'scheduledAt' key$"
        self.assertRaisesRegex(SpecificationError, error, SlurmPipelineStatus, {})

    @patch("subprocess.check_output")
    def testFinalJobsWithNoJobs(self, subprocessMock):
        """
        The finalJobs method should produce an empty set of job ids if the
        final step of a specification emits no jobs.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        # Two tasks were emitted, but without job ids.
                        "task1": [],
                        "task2": [],
                    },
                },
                {
                    "name": "end",
                    "scheduledAt": 1481379659.1530972,
                    "script": "end.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
            ],
        }

        subprocessMock.return_value = "JobID|JobName|State|Elapsed|Nodelist\n"

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set(), sps.finalJobs())

    @patch("subprocess.check_output")
    def testFinalJobsWithoutDependencies(self, subprocessMock):
        """
        The finalJobs method should produce the correct set of job ids emitted
        by the final steps of a specification.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "task1": [0, 1],
                        "task2": [2],
                    },
                },
                {
                    "name": "end",
                    "scheduledAt": 1481379659.1530972,
                    "script": "end.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "task1": [3, 4, 5],
                        "task2": [7, 8],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "0|name|RUNNING|04:32:00|cpu-3\n"
            "1|name|RUNNING|04:32:00|cpu-3\n"
            "2|name|RUNNING|04:32:00|cpu-3\n"
            "3|name|RUNNING|04:32:00|cpu-3\n"
            "4|name|RUNNING|04:32:00|cpu-3\n"
            "5|name|RUNNING|04:32:00|cpu-3\n"
            "6|name|RUNNING|04:32:00|cpu-3\n"
            "7|name|RUNNING|04:32:00|cpu-3\n"
            "8|name|RUNNING|04:32:00|cpu-3\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual({0, 1, 2, 3, 4, 5, 7, 8}, sps.finalJobs())

    @patch("subprocess.check_output")
    def testFinalJobsWithDependencies(self, subprocessMock):
        """
        The finalJobs method should produce the correct set of job ids emitted
        by the final step of a specification that contains a dependency.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "task1": [0, 1],
                        "task2": [2],
                    },
                },
                {
                    "dependencies": ["start"],
                    "name": "end",
                    "scheduledAt": 1481379659.1530972,
                    "script": "end.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "task1": [3, 4, 5],
                        "task2": [7, 8],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "0|name|RUNNING|04:32:00|cpu-3\n"
            "1|name|RUNNING|04:32:00|cpu-3\n"
            "2|name|RUNNING|04:32:00|cpu-3\n"
            "3|name|RUNNING|04:32:00|cpu-3\n"
            "4|name|RUNNING|04:32:00|cpu-3\n"
            "5|name|RUNNING|04:32:00|cpu-3\n"
            "6|name|RUNNING|04:32:00|cpu-3\n"
            "7|name|RUNNING|04:32:00|cpu-3\n"
            "8|name|RUNNING|04:32:00|cpu-3\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual({3, 4, 5, 7, 8}, sps.finalJobs())

    @patch("subprocess.check_output")
    def testStepJobIdSummaryNoJobs(self, subprocessMock):
        """
        The stepJobIds method should return an empty set if a step emitted no
        jobs.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
            ],
        }

        subprocessMock.return_value = "JobID|JobName|State|Elapsed|Nodelist\n"

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set(), sps.stepJobIds("start"))

    @patch("subprocess.check_output")
    def testStepJobIdSummaryTwoJobsNeitherFinished(self, subprocessMock):
        """
        The stepJobIds method should return the expected set if a step emitted
        two jobs, neither of which is finished.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "fun": [34, 35],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "34|name|RUNNING|04:32:00|cpu-3\n"
            "35|name|RUNNING|04:32:00|cpu-4\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual({34, 35}, sps.stepJobIds("start"))

    @patch("subprocess.check_output")
    def testStepJobIdSummaryTwoJobsOneFinished(self, subprocessMock):
        """
        The stepJobIds method should return the expected set if a step emitted
        two jobs, one of which is finished.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "fun": [34, 35],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "34|name|RUNNING|04:32:00|cpu-3\n"
            "35|name|COMPLETED|04:32:00|cpu-4\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual({34, 35}, sps.stepJobIds("start"))

    @patch("subprocess.check_output")
    def testStepJobIdSummaryTwoJobsBothFinished(self, subprocessMock):
        """
        The stepJobIds method should return the expected set if a step
        emitted two jobs, both of which are finished.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "fun": [34, 35],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "34|name|COMPLETED|04:32:00|cpu-3\n"
            "35|name|COMPLETED|04:32:00|cpu-4\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual({34, 35}, sps.stepJobIds("start"))

    @patch("subprocess.check_output")
    def testUnfinishedJobsNoJobs(self, subprocessMock):
        """
        The unfinishedJobs method should return an empty set if a
        specification emitted no jobs.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
            ],
        }

        subprocessMock.return_value = "JobID|JobName|State|Elapsed|Nodelist\n"

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set(), sps.unfinishedJobs())

    @patch("subprocess.check_output")
    def testUnfinishedJobsOneUnfinishedJob(self, subprocessMock):
        """
        The unfinishedJobs method should return a set with the expected job id
        if the specification emitted one job that is not finished.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "xxx": [123],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n" "123|name|RUNNING|04:32:00|cpu-4\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual({123}, sps.unfinishedJobs())

    @patch("subprocess.check_output")
    def testUnfinishedJobsOneFinishedJob(self, subprocessMock):
        """
        The unfinishedJobs method should return an empty set if the
        specification emitted one job that is finished.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "xxx": [123],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "123|name|COMPLETED|04:32:00|cpu-4\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set(), sps.unfinishedJobs())

    @patch("subprocess.check_output")
    def testUnfinishedJobsMultipleSteps(self, subprocessMock):
        """
        The unfinishedJobs method should return the expected job ids if the
        specification has multiple steps.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "xxx": [12, 34],
                    },
                },
                {
                    "name": "end",
                    "scheduledAt": 1481379659.1530972,
                    "script": "end.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "yyy": [56, 78, 90],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "12|name|RUNNING|04:32:00|cpu-3\n"
            "34|name|COMPLETED|04:32:00|cpu-3\n"
            "56|name|RUNNING|04:32:00|cpu-4\n"
            "78|name|COMPLETED|04:32:00|cpu-4\n"
            "90|name|RUNNING|04:32:00|cpu-5\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual({12, 56, 90}, sps.unfinishedJobs())

    @patch("subprocess.check_output")
    def testFinishedJobsNoJobs(self, subprocessMock):
        """
        The finishedJobs method should return an empty set if a
        specification emitted no jobs.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
            ],
        }

        subprocessMock.return_value = "JobID|JobName|State|Elapsed|Nodelist\n"

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set(), sps.finishedJobs())

    @patch("subprocess.check_output")
    def testFinishedJobsOneFinishedJob(self, subprocessMock):
        """
        The finishedJobs method should return a set with the expected job id
        if the specification emitted one job that is finished.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "xxx": [123],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "123|name|COMPLETED|04:32:00|cpu-4\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual({123}, sps.finishedJobs())

    @patch("subprocess.check_output")
    def testFinishedJobsOneUnfinishedJob(self, subprocessMock):
        """
        The finishedJobs method should return an empty set if the
        specification emitted one job that is not finished.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "xxx": [123],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n" "123|name|RUNNING|04:32:00|cpu-4\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set(), sps.finishedJobs())

    @patch("subprocess.check_output")
    def testFinishedJobsMultipleSteps(self, subprocessMock):
        """
        The finishedJobs method should return the expected job ids if the
        specification has multiple steps.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "xxx": [12, 34],
                    },
                },
                {
                    "name": "end",
                    "scheduledAt": 1481379659.1530972,
                    "script": "end.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "yyy": [56, 78, 90],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "12|name|RUNNING|04:32:00|cpu-3\n"
            "34|name|COMPLETED|04:32:00|cpu-3\n"
            "56|name|RUNNING|04:32:00|cpu-4\n"
            "78|name|COMPLETED|04:32:00|cpu-4\n"
            "90|name|RUNNING|04:32:00|cpu-5\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual({34, 78}, sps.finishedJobs())

    @patch("subprocess.check_output")
    def testJobIdsNoJobs(self, subprocessMock):
        """
        The jobs method should return an empty set when no jobs were started.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
                {
                    "name": "end",
                    "scheduledAt": 1481379659.1530972,
                    "script": "end.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
            ],
        }

        subprocessMock.return_value = "JobID|JobName|State|Elapsed|Nodelist\n"

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set(), sps.jobs())

    @patch("subprocess.check_output")
    def testJobIds(self, subprocessMock):
        """
        The jobs method should return all emitted job ids.
        """
        status = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "xxx": [12, 34],
                    },
                },
                {
                    "name": "end",
                    "scheduledAt": 1481379659.1530972,
                    "script": "end.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "yyy": [56, 78, 90],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "12|name|RUNNING|04:32:00|cpu-3\n"
            "34|name|COMPLETED|04:32:00|cpu-3\n"
            "56|name|RUNNING|04:32:00|cpu-4\n"
            "78|name|COMPLETED|04:32:00|cpu-4\n"
            "90|name|RUNNING|04:32:00|cpu-5\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual({12, 34, 56, 78, 90}, sps.jobs())

    @patch("subprocess.check_output")
    def testToStr(self, subprocessMock):
        """
        The toStr method must return a complete summary of the status
        specification.
        """
        status = {
            "firstStep": "panel",
            "force": False,
            "lastStep": None,
            "nice": 3,
            "user": "sw463",
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "cwd": "00-start",
                    "environ": {
                        "SP_FORCE": "1",
                        "SP_SKIP": "0",
                    },
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "00-start/start.sh",
                    "skip": False,
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
                {
                    "cwd": "01-split",
                    "dependencies": ["start"],
                    "environ": {
                        "SP_FORCE": "1",
                        "SP_SKIP": "0",
                    },
                    "name": "split",
                    "scheduledAt": 1481379664.184737,
                    "script": "01-split/sbatch.sh",
                    "skip": False,
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "chunk-aaaaa": [],
                        "chunk-aaaab": [],
                        "chunk-aaaac": [],
                    },
                },
                {
                    "cwd": "02-blastn",
                    "dependencies": ["split"],
                    "environ": {
                        "SP_FORCE": "1",
                        "SP_SKIP": "0",
                    },
                    "name": "blastn",
                    "scheduledAt": 1481379722.3996398,
                    "script": "02-blastn/sbatch.sh",
                    "skip": False,
                    "stdout": "",
                    "taskDependencies": {
                        "chunk-aaaaa": [],
                        "chunk-aaaab": [],
                        "chunk-aaaac": [],
                    },
                    "tasks": {
                        "chunk-aaaaa": [4416231],
                        "chunk-aaaab": [4416232],
                        "chunk-aaaac": [4416233],
                    },
                },
                {
                    "collect": True,
                    "cwd": "03-panel",
                    "dependencies": ["blastn"],
                    "environ": {
                        "SP_FORCE": "1",
                        "SP_SKIP": "0",
                    },
                    "name": "panel",
                    "scheduledAt": 1481379722.5036008,
                    "script": "03-panel/sbatch.sh",
                    "skip": False,
                    "stdout": "TASK: panel 4417615\n",
                    "taskDependencies": {
                        "chunk-aaaaa": [4416231],
                        "chunk-aaaab": [4416232],
                        "chunk-aaaac": [4416233],
                    },
                    "tasks": {"panel": [4417615]},
                },
                {
                    "cwd": "04-stop",
                    "dependencies": ["panel"],
                    "environ": {
                        "SP_FORCE": "1",
                        "SP_SKIP": "0",
                    },
                    "name": "stop",
                    "scheduledAt": 1481379722.5428307,
                    "script": "04-stop/sbatch.sh",
                    "skip": False,
                    "stdout": "TASK: stop 4417616\n",
                    "taskDependencies": {"panel": [4417615]},
                    "tasks": {"stop": [4417616]},
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "4416231|name1|COMPLETED|04:32:00|cpu-3\n"
            "4416232|name2|COMPLETED|04:02:00|cpu-6\n"
            "4416233|name3|COMPLETED|04:12:00|cpu-7\n"
            "4417615|name5|COMPLETED|04:11:00|cpu-8\n"
            "4417616|name6|RUNNING|04:32:00|cpu-3\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual(
            """\
Scheduled by: sw463
Scheduled at: 2016-12-10 14:20:58
Scheduling arguments:
  First step: panel
  Force: False
  Last step: None
  Nice: 3
  Sleep: 0.00
  Script arguments: <None>
  Skip: <None>
  Start after: <None>
Steps summary:
  Number of steps: 5
  Jobs emitted in total: 5
  Jobs finished: 4 (80.00%)
    start: no jobs emitted
    split: no jobs emitted
    blastn: 3 jobs emitted, 3 (100.00%) finished
    panel: 1 job emitted, 1 (100.00%) finished
    stop: 1 job emitted, 0 (0.00%) finished
Step 1: start
  No dependencies.
  No tasks emitted by this step
  Collect step: False
  Error step: False
  Working directory: 00-start
  Scheduled at: 2016-12-10 14:20:59
  Script: 00-start/start.sh
  Skip: False
  Slurm pipeline environment variables:
    SP_FORCE: 1
    SP_SKIP: 0
Step 2: split
  1 step dependency: start
    Dependent on 0 tasks emitted by the dependent step
  3 tasks emitted by this step
    Summary: 0 jobs started by these tasks
    Tasks:
      chunk-aaaaa
      chunk-aaaab
      chunk-aaaac
  Collect step: False
  Error step: False
  Working directory: 01-split
  Scheduled at: 2016-12-10 14:21:04
  Script: 01-split/sbatch.sh
  Skip: False
  Slurm pipeline environment variables:
    SP_FORCE: 1
    SP_SKIP: 0
Step 3: blastn
  1 step dependency: split
    Dependent on 3 tasks emitted by the dependent step
    Summary: 0 jobs started by the dependent tasks
    Dependent tasks:
      chunk-aaaaa
      chunk-aaaab
      chunk-aaaac
  3 tasks emitted by this step
    Summary: 3 jobs started by these tasks, of which 3 (100.00%) are finished
    Tasks:
      chunk-aaaaa
        Job 4416231: JobName=name1, State=COMPLETED, Elapsed=04:32:00, \
Nodelist=cpu-3
      chunk-aaaab
        Job 4416232: JobName=name2, State=COMPLETED, Elapsed=04:02:00, \
Nodelist=cpu-6
      chunk-aaaac
        Job 4416233: JobName=name3, State=COMPLETED, Elapsed=04:12:00, \
Nodelist=cpu-7
  Collect step: False
  Error step: False
  Working directory: 02-blastn
  Scheduled at: 2016-12-10 14:22:02
  Script: 02-blastn/sbatch.sh
  Skip: False
  Slurm pipeline environment variables:
    SP_FORCE: 1
    SP_SKIP: 0
Step 4: panel
  1 step dependency: blastn
    Dependent on 3 tasks emitted by the dependent step
    Summary: 3 jobs started by the dependent task, of which 3 (100.00%) are \
finished
    Dependent tasks:
      chunk-aaaaa
        Job 4416231: JobName=name1, State=COMPLETED, Elapsed=04:32:00, \
Nodelist=cpu-3
      chunk-aaaab
        Job 4416232: JobName=name2, State=COMPLETED, Elapsed=04:02:00, \
Nodelist=cpu-6
      chunk-aaaac
        Job 4416233: JobName=name3, State=COMPLETED, Elapsed=04:12:00, \
Nodelist=cpu-7
  1 task emitted by this step
    Summary: 1 job started by this task, of which 1 (100.00%) are finished
    Tasks:
      panel
        Job 4417615: JobName=name5, State=COMPLETED, Elapsed=04:11:00, \
Nodelist=cpu-8
  Collect step: True
  Error step: False
  Working directory: 03-panel
  Scheduled at: 2016-12-10 14:22:02
  Script: 03-panel/sbatch.sh
  Skip: False
  Slurm pipeline environment variables:
    SP_FORCE: 1
    SP_SKIP: 0
Step 5: stop
  1 step dependency: panel
    Dependent on 1 task emitted by the dependent step
    Summary: 1 job started by the dependent task, of which 1 (100.00%) are \
finished
    Dependent tasks:
      panel
        Job 4417615: JobName=name5, State=COMPLETED, Elapsed=04:11:00, \
Nodelist=cpu-8
  1 task emitted by this step
    Summary: 1 job started by this task, of which 0 (0.00%) are finished
    Tasks:
      stop
        Job 4417616: JobName=name6, State=RUNNING, Elapsed=04:32:00, \
Nodelist=cpu-3
  Collect step: False
  Error step: False
  Working directory: 04-stop
  Scheduled at: 2016-12-10 14:22:02
  Script: 04-stop/sbatch.sh
  Skip: False
  Slurm pipeline environment variables:
    SP_FORCE: 1
    SP_SKIP: 0""",
            sps.toStr(),
        )

    @patch("subprocess.check_output")
    def testToStrWithScriptArgsSkipAndStartAfter(self, subprocessMock):
        """
        The toStr method must return a complete summary of the status
        specification when scriptArgs, skip, and startAfter are specified.
        """
        status = {
            "user": "sally",
            "firstStep": None,
            "force": False,
            "lastStep": None,
            "nice": "None",
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": ["hey", "you"],
            "skip": ["start-step"],
            "sleep": 5.0,
            "startAfter": [34, 56],
            "steps": [
                {
                    "cwd": "00-start",
                    "environ": {
                        "SP_FORCE": "1",
                        "SP_SKIP": "0",
                    },
                    "name": "start-step",
                    "scheduledAt": 1481379659.1530972,
                    "script": "00-start/start.sh",
                    "skip": False,
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
            ],
        }

        subprocessMock.return_value = (
            "JobID|JobName|State|Elapsed|Nodelist\n"
            "34|name1|RUNNING|01:32:00|cpu-2\n"
            "56|name2|COMPLETED|04:32:00|cpu-3\n"
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual(
            """\
Scheduled by: sally
Scheduled at: 2016-12-10 14:20:58
Scheduling arguments:
  First step: None
  Force: False
  Last step: None
  Nice: None
  Sleep: 5.00
  Script arguments: hey you
  Skip: start-step
  Start after the following 2 jobs, of which 1 (50.00%) is finished:
    Job 34: JobName=name1, State=RUNNING, Elapsed=01:32:00, Nodelist=cpu-2
    Job 56: JobName=name2, State=COMPLETED, Elapsed=04:32:00, Nodelist=cpu-3
Steps summary:
  Number of steps: 1
  Jobs emitted in total: 0
  Jobs finished: 0 (100.00%)
    start-step: no jobs emitted
Step 1: start-step
  No dependencies.
  No tasks emitted by this step
  Collect step: False
  Error step: False
  Working directory: 00-start
  Scheduled at: 2016-12-10 14:20:59
  Script: 00-start/start.sh
  Skip: False
  Slurm pipeline environment variables:
    SP_FORCE: 1
    SP_SKIP: 0""",
            sps.toStr(),
        )


class TestSlurmPipelineStatusCollection(TestCase):
    """
    Test the SlurmPipelineStatusCollection class.
    """

    def testNonIdenticalSteps(self):
        """
        If two specifications are passed that do not have the same list of steps,
        a ValueError error must be raised.
        """
        status1 = {
            "user": "sally",
            "firstStep": None,
            "force": False,
            "lastStep": None,
            "nice": "None",
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": ["hey", "you"],
            "skip": [],
            "sleep": 5.0,
            "startAfter": [],
            "steps": [
                {
                    "cwd": "00-start",
                    "environ": {
                        "SP_FORCE": "1",
                        "SP_SKIP": "0",
                    },
                    "name": "step-1",
                    "scheduledAt": 1481379659.1530972,
                    "script": "00-start/start.sh",
                    "skip": False,
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
            ],
        }

        status2 = {
            "user": "sally",
            "firstStep": None,
            "force": False,
            "lastStep": None,
            "nice": "None",
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": ["hey", "you"],
            "skip": [],
            "sleep": 5.0,
            "startAfter": [],
            "steps": [
                {
                    "cwd": "00-start",
                    "environ": {
                        "SP_FORCE": "1",
                        "SP_SKIP": "0",
                    },
                    "name": "step-2",
                    "scheduledAt": 1481379659.1530972,
                    "script": "00-start/start.sh",
                    "skip": False,
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
            ],
        }

        error = (
            r"^The list of steps found in the first specification \['step-1'\] does "
            r"not match that found in specification number 2: \['step-2'\]\.$"
        )
        self.assertRaisesRegex(
            ValueError, error, SlurmPipelineStatusCollection, (status1, status2)
        )

    def testNonUniqueNames(self):
        """
        The list of names must not have any duplicates.
        """
        status = {
            "user": "sally",
            "firstStep": None,
            "force": False,
            "lastStep": None,
            "nice": "None",
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": ["hey", "you"],
            "skip": [],
            "sleep": 5.0,
            "startAfter": [],
            "steps": [
                {
                    "cwd": "00-start",
                    "environ": {
                        "SP_FORCE": "1",
                        "SP_SKIP": "0",
                    },
                    "name": "step-1",
                    "scheduledAt": 1481379659.1530972,
                    "script": "00-start/start.sh",
                    "skip": False,
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {},
                },
            ],
        }

        error = (
            r"^The list of specification names contains at least one "
            r"duplicate: \['a', 'a'\]\.$"
        )
        self.assertRaisesRegex(
            ValueError,
            error,
            SlurmPipelineStatusCollection,
            (status, status),
            ("a", "a"),
        )

    def testUnequalLengths(self):
        """
        The lists of specifications and names must have the same lengths.
        """
        error = (
            r"^The specifications and names lists are not the same "
            r"lengths \(0 != 1\)\.$"
        )
        self.assertRaisesRegex(
            ValueError, error, SlurmPipelineStatusCollection, (), ("a",)
        )

    @patch("subprocess.check_output")
    def testJobs(self, subprocessMock):
        """
        Test a realistic situation.
        """

        status1 = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "xxx": [12, 34],
                    },
                },
                {
                    "name": "end",
                    "scheduledAt": 1481379659.1530972,
                    "script": "end.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "yyy": [56, 78, 90],
                    },
                },
            ],
        }

        status2 = {
            "force": False,
            "lastStep": None,
            "scheduledAt": 1481379658.5455897,
            "scriptArgs": [],
            "skip": [],
            "startAfter": None,
            "steps": [
                {
                    "name": "start",
                    "scheduledAt": 1481379659.1530972,
                    "script": "start.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "xxx": [13, 35],
                    },
                },
                {
                    "name": "end",
                    "scheduledAt": 1481379659.1530972,
                    "script": "end.sh",
                    "stdout": "",
                    "taskDependencies": {},
                    "tasks": {
                        "yyy": [57, 79, 91],
                    },
                },
            ],
        }

        subprocessMock.side_effect = [
            (
                "JobID|JobName|State|Elapsed|Nodelist\n"
                "12|name|RUNNING|04:32:00|cpu-3\n"
                "34|name|COMPLETED|04:32:00|cpu-3\n"
                "56|name|FAILED|04:32:00|cpu-4\n"
                "78|name|COMPLETED|04:32:00|cpu-4\n"
                "90|name|RUNNING|04:32:00|cpu-5\n"
            ),
            (
                "JobID|JobName|State|Elapsed|Nodelist\n"
                "13|name|RUNNING|00:00:10|cpu-3\n"
                "35|name|COMPLETED|00:01:00|cpu-3\n"
                "57|name|PENDING|00:00:00|cpu-4\n"
                "79|name|COMPLETED|04:32:00|cpu-4\n"
                "91|name|FAILED|04:32:00|cpu-5\n"
            ),
        ]

        spsc = SlurmPipelineStatusCollection((status1, status2), zeroSecondsValue=999)

        # Cheap & nasty way to check that SlurmPipelineStatusCollection put
        # things into a DataFrame in the expected way.
        self.maxDiff = None
        expected = """\
        name   step task  jobId     status   node   elapsed  seconds
0  unnamed-0  start  xxx     12    RUNNING  cpu-3  04:32:00    16320
1  unnamed-0  start  xxx     34  COMPLETED  cpu-3  04:32:00    16320
2  unnamed-0    end  yyy     56     FAILED  cpu-4  04:32:00    16320
3  unnamed-0    end  yyy     78  COMPLETED  cpu-4  04:32:00    16320
4  unnamed-0    end  yyy     90    RUNNING  cpu-5  04:32:00    16320
5  unnamed-1  start  xxx     13    RUNNING  cpu-3  00:00:10       10
6  unnamed-1  start  xxx     35  COMPLETED  cpu-3  00:01:00       60
7  unnamed-1    end  yyy     57    PENDING  cpu-4  00:00:00      999
8  unnamed-1    end  yyy     79  COMPLETED  cpu-4  04:32:00    16320
9  unnamed-1    end  yyy     91     FAILED  cpu-5  04:32:00    16320\
"""
        self.assertEqual(expected, str(spsc.df))
