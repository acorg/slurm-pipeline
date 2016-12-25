from unittest import TestCase
from six import assertRaisesRegex

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from slurm_pipeline.error import SpecificationError
from slurm_pipeline.squeue import SQueue
from slurm_pipeline.status import SlurmPipelineStatus, secondsToTime


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
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineStatus,
                          {})

    def testFinalJobsWithNoJobs(self):
        """
        The finalJobs method should produce an empty set of job ids if the
        final step of a specification emits no jobs.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        # Two tasks were emitted, but without job ids.
                        'task1': [],
                        'task2': [],
                    }
                },
                {
                    'name': 'end',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'end.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                    }
                },
            ]
        }

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set(), sps.finalJobs(sps.specification))

    def testFinalJobsWithoutDependencies(self):
        """
        The finalJobs method should produce the correct set of job ids emitted
        by the final steps of a specification.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'task1': [0, 1],
                        'task2': [2],
                    }
                },
                {
                    'name': 'end',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'end.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'task1': [3, 4, 5],
                        'task2': [7, 8],
                    }
                },
            ]
        }

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set((0, 1, 2, 3, 4, 5, 7, 8)),
                         sps.finalJobs(sps.specification))

    def testFinalJobsWithDependencies(self):
        """
        The finalJobs method should produce the correct set of job ids emitted
        by the final step of a specification that contains a dependency.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'task1': [0, 1],
                        'task2': [2],
                    }
                },
                {
                    'dependencies': ['start'],
                    'name': 'end',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'end.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'task1': [3, 4, 5],
                        'task2': [7, 8],
                    }
                },
            ]
        }

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set((3, 4, 5, 7, 8)),
                         sps.finalJobs(sps.specification))

    @patch('subprocess.check_output')
    def testStepJobIdSummaryNoJobs(self, subprocessMock):
        """
        The stepJobIdSummary method should return two empty sets
        if a step emitted no jobs.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
        )

        sq = SQueue()
        sps = SlurmPipelineStatus(status)
        self.assertEqual((set(), set()), sps.stepJobIdSummary('start', sq))

    @patch('subprocess.check_output')
    def testStepJobIdSummaryTwoJobsNeitherFinished(self, subprocessMock):
        """
        The stepJobIdSummary method should return the expected sets
        if a step emitted two jobs, neither of which is finished.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'fun': [34, 35],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
            '34 R 4:33, cpu-3\n'
            '35 R 4:35, cpu-4\n'
        )

        sq = SQueue()
        sps = SlurmPipelineStatus(status)
        self.assertEqual((set([34, 35]), set()),
                         sps.stepJobIdSummary('start', sq))

    @patch('subprocess.check_output')
    def testStepJobIdSummaryTwoJobsOneFinished(self, subprocessMock):
        """
        The stepJobIdSummary method should return the expected sets
        if a step emitted two jobs, one of which is finished.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'fun': [34, 35],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
            '34 R 4:33, cpu-3\n'
        )

        sq = SQueue()
        sps = SlurmPipelineStatus(status)
        self.assertEqual((set([34, 35]), set([35])),
                         sps.stepJobIdSummary('start', sq))

    @patch('subprocess.check_output')
    def testStepJobIdSummaryTwoJobsBothFinished(self, subprocessMock):
        """
        The stepJobIdSummary method should return the expected sets
        if a step emitted two jobs, both of which are finished.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'fun': [34, 35],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
        )

        sq = SQueue()
        sps = SlurmPipelineStatus(status)
        self.assertEqual((set([34, 35]), set([34, 35])),
                         sps.stepJobIdSummary('start', sq))

    @patch('subprocess.check_output')
    def testUnfinishedJobsNoJobs(self, subprocessMock):
        """
        The unfinishedJobs method should return an empty set if a
        specification emitted no jobs.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {},
                },
            ],
        }

        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set(), sps.unfinishedJobs(sps.specification))

    @patch('subprocess.check_output')
    def testUnfinishedJobsOneUnfinishedJob(self, subprocessMock):
        """
        The unfinishedJobs method should return a set with the expected job id
        if the specification emitted one job that is not finished.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'xxx': [123],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
            '123 R 45:33 (None)\n'
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set([123]), sps.unfinishedJobs(sps.specification))

    @patch('subprocess.check_output')
    def testUnfinishedJobsOneFinishedJob(self, subprocessMock):
        """
        The unfinishedJobs method should return an empty set if the
        specification emitted one job that is finished.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'xxx': [123],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set(), sps.unfinishedJobs(sps.specification))

    @patch('subprocess.check_output')
    def testUnfinishedJobsMultipleSteps(self, subprocessMock):
        """
        The unfinishedJobs method should return the expected job ids if the
        specification has multiple steps.
        """
        status = {
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'steps': [
                {
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'start.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'xxx': [12, 34],
                    },
                },
                {
                    'name': 'end',
                    'scheduledAt': 1481379659.1530972,
                    'script': 'end.sh',
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'yyy': [56, 78, 90],
                    },
                },
            ],
        }

        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
            '12 R 45:33 (None)\n'
            '56 R 27:01 (None)\n'
            '90 R 23:07 (None)\n'
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual(set([12, 56, 90]),
                         sps.unfinishedJobs(sps.specification))

    @patch('subprocess.check_output')
    def testToStr(self, subprocessMock):
        """
        The toStr method must return a complete summary of the status
        specification.
        """
        status = {
            'firstStep': 'panel',
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': [],
            'skip': [],
            'startAfter': None,
            'steps': [
                {
                    'cwd': '00-start',
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': '00-start/start.sh',
                    'simulate': True,
                    'skip': False,
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {}
                },
                {
                    'cwd': '01-split',
                    'dependencies': [
                        'start'
                    ],
                    'name': 'split',
                    'scheduledAt': 1481379664.184737,
                    'script': '01-split/sbatch.sh',
                    'simulate': True,
                    'skip': False,
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {
                        'chunk-aaaaa': [],
                        'chunk-aaaab': [],
                        'chunk-aaaac': [],
                    }
                },
                {
                    'cwd': '02-blastn',
                    'dependencies': [
                        'split'
                    ],
                    'name': 'blastn',
                    'scheduledAt': 1481379722.3996398,
                    'script': '02-blastn/sbatch.sh',
                    'simulate': True,
                    'skip': False,
                    'stdout': '',
                    'taskDependencies': {
                        'chunk-aaaaa': [],
                        'chunk-aaaab': [],
                        'chunk-aaaac': [],
                    },
                    "tasks": {
                        "chunk-aaaaa": [
                            4416231
                        ],
                        "chunk-aaaab": [
                            4416232
                        ],
                        "chunk-aaaac": [
                            4416233
                        ],
                    },
                },
                {
                    'collect': True,
                    'cwd': '03-panel',
                    'dependencies': [
                        'blastn'
                    ],
                    'name': 'panel',
                    'scheduledAt': 1481379722.5036008,
                    'script': '03-panel/sbatch.sh',
                    'simulate': False,
                    'skip': False,
                    'stdout': 'TASK: panel 4417615\n',
                    'taskDependencies': {
                        'chunk-aaaaa': [
                            4416231
                        ],
                        'chunk-aaaab': [
                            4416232
                        ],
                        'chunk-aaaac': [
                            4416233
                        ],
                    },
                    'tasks': {
                        'panel': [
                            4417615
                        ]
                    }
                },
                {
                    'cwd': '04-stop',
                    'dependencies': [
                        'panel'
                    ],
                    'name': 'stop',
                    'scheduledAt': 1481379722.5428307,
                    'script': '04-stop/sbatch.sh',
                    'simulate': False,
                    'skip': False,
                    'stdout': 'TASK: stop 4417616\n',
                    'taskDependencies': {
                        'panel': [
                            4417615
                        ]
                    },
                    'tasks': {
                        'stop': [
                            4417616
                        ]
                    }
                }
            ]
        }

        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
            '4417616 R 4:27 cpu-3\n'
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual(
            '''\
Scheduled at: 2016-12-10 14:20:58
Scheduling arguments:
  First step: panel
  Force: False
  Last step: None
  Script arguments: <None>
  Skip: <None>
  Start after: <None>
5 jobs emitted in total, of which 4 (80.00%) are finished
Step summary:
  start: no jobs emitted
  split: no jobs emitted
  blastn: 3 jobs emitted, 3 (100.00%) finished
  panel: 1 job emitted, 1 (100.00%) finished
  stop: 1 job emitted, 0 (0.00%) finished
Step 1: start
  No dependencies.
  No tasks emitted by this step
  Working directory: 00-start
  Scheduled at: 2016-12-10 14:20:59
  Script: 00-start/start.sh
  Simulate: True
  Skip: False
Step 2: split
  1 step dependency: start
    Dependent on 0 tasks emitted by the dependent step
  3 tasks emitted by this step
    0 jobs started by these tasks
    Tasks:
      chunk-aaaaa
      chunk-aaaab
      chunk-aaaac
  Working directory: 01-split
  Scheduled at: 2016-12-10 14:21:04
  Script: 01-split/sbatch.sh
  Simulate: True
  Skip: False
Step 3: blastn
  1 step dependency: split
    Dependent on 3 tasks emitted by the dependent step
    0 jobs started by the dependent tasks
    Dependent tasks:
      chunk-aaaaa
      chunk-aaaab
      chunk-aaaac
  3 tasks emitted by this step
    3 jobs started by this task, of which 3 (100.00%) are finished
    Tasks:
      chunk-aaaaa
        Job 4416231: Finished
      chunk-aaaab
        Job 4416232: Finished
      chunk-aaaac
        Job 4416233: Finished
  Working directory: 02-blastn
  Scheduled at: 2016-12-10 14:22:02
  Script: 02-blastn/sbatch.sh
  Simulate: True
  Skip: False
Step 4: panel
  1 step dependency: blastn
    Dependent on 3 tasks emitted by the dependent step
    3 jobs started by the dependent task, of which 3 (100.00%) are finished
    Dependent tasks:
      chunk-aaaaa
        Job 4416231: Finished
      chunk-aaaab
        Job 4416232: Finished
      chunk-aaaac
        Job 4416233: Finished
  1 task emitted by this step
    1 job started by this task, of which 1 (100.00%) are finished
    Tasks:
      panel
        Job 4417615: Finished
  Working directory: 03-panel
  Scheduled at: 2016-12-10 14:22:02
  Script: 03-panel/sbatch.sh
  Simulate: False
  Skip: False
Step 5: stop
  1 step dependency: panel
    Dependent on 1 task emitted by the dependent step
    1 job started by the dependent task, of which 1 (100.00%) are finished
    Dependent tasks:
      panel
        Job 4417615: Finished
  1 task emitted by this step
    1 job started by this task, of which 0 (0.00%) are finished
    Tasks:
      stop
        Job 4417616: Status=R Time=4:27 Nodelist=cpu-3
  Working directory: 04-stop
  Scheduled at: 2016-12-10 14:22:02
  Script: 04-stop/sbatch.sh
  Simulate: False
  Skip: False''',
            sps.toStr())

    @patch('subprocess.check_output')
    def testToStrWithScriptArgsSkipAndStartAfter(self, subprocessMock):
        """
        The toStr method must return a complete summary of the status
        specification when scriptArgs, skip, and startAfter are specified.
        """
        status = {
            'firstStep': None,
            'force': False,
            'lastStep': None,
            'scheduledAt': 1481379658.5455897,
            'scriptArgs': ['hey', 'you'],
            'skip': ['skip', 'this'],
            'startAfter': ['34', '56'],
            'steps': [
                {
                    'cwd': '00-start',
                    'name': 'start',
                    'scheduledAt': 1481379659.1530972,
                    'script': '00-start/start.sh',
                    'simulate': True,
                    'skip': False,
                    'stdout': '',
                    'taskDependencies': {},
                    'tasks': {}
                },
            ]
        }

        subprocessMock.return_value = (
            'JOBID ST TIME NODELIST(REASON)\n'
            '4417616 R 4:27 cpu-3\n'
        )

        sps = SlurmPipelineStatus(status)
        self.assertEqual(
            '''\
Scheduled at: 2016-12-10 14:20:58
Scheduling arguments:
  First step: None
  Force: False
  Last step: None
  Script arguments: hey you
  Skip: skip, this
  Start after: 34, 56
0 jobs emitted in total, of which 0 (100.00%) are finished
Step summary:
  start: no jobs emitted
Step 1: start
  No dependencies.
  No tasks emitted by this step
  Working directory: 00-start
  Scheduled at: 2016-12-10 14:20:59
  Script: 00-start/start.sh
  Simulate: True
  Skip: False''',
            sps.toStr())


class TestSecondsToTime(TestCase):
    """
    Tests for the secondsToTime function.
    """
    def testArbitraryTime(self):
        """
        The secondsToTime function must return the expected value.
        """
        self.assertEqual('2016-12-10 14:20:58',
                         secondsToTime(1481379658.5455897))
