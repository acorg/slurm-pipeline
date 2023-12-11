from os import X_OK, path
from unittest import TestCase
from unittest.mock import ANY, call, patch
from json import dumps
import platform
from subprocess import CalledProcessError
from sys import version_info
from getpass import getuser

from slurm_pipeline.pipeline import SlurmPipeline, DEVNULL
from slurm_pipeline.error import SchedulingError, SpecificationError

PYPY = platform.python_implementation() == "PyPy"


class TestSlurmPipeline(TestCase):
    """
    Tests for the slurm_pipeline.pipeline.SlurmPipeline class.
    """

    @patch("os.path.isdir")
    def testNonexistentDir(self, isdirMock):
        """
        If a step has a 'cwd' key that mentions a non-existent directory, a
        SpecificationError must be raised.
        """
        isdirMock.return_value = False
        error = (
            r"^Specification step 1 specifies a working directory "
            r"\('dir'\) that does not exist"
        )
        self.assertRaisesRegex(
            SpecificationError,
            error,
            SlurmPipeline,
            {
                "steps": [
                    {
                        "cwd": "dir",
                        "name": "name",
                        "script": "script",
                    },
                ]
            },
        )

    @patch("os.access")
    @patch("os.path.exists")
    def testNonexecutableScript(self, existsMock, accessMock):
        """
        If os.access fails, a SpecificationError must be raised.
        """
        accessMock.return_value = False

        error = "^The script 'script' in step 1 is not executable$"
        self.assertRaisesRegex(
            SpecificationError,
            error,
            SlurmPipeline,
            {
                "steps": [
                    {
                        "name": "name",
                        "script": "script",
                    },
                ]
            },
        )

    @patch("os.access")
    @patch("os.path.exists")
    def testNonexistentScript(self, existsMock, accessMock):
        """
        If a step has a 'script' key that mentions a non-existent file, a
        SpecificationError must be raised.
        """
        existsMock.return_value = False
        error = "^The script 'script' in step 1 does not exist$"
        self.assertRaisesRegex(
            SpecificationError,
            error,
            SlurmPipeline,
            {
                "steps": [
                    {
                        "name": "name",
                        "script": "script",
                    },
                ]
            },
        )

    @patch("os.access")
    @patch("os.path.exists")
    def testAccessAndExistsAreCalled(self, existsMock, accessMock):
        """
        Both os.access and os.path.exists must be called as expected
        as the specification is checked.
        """
        SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name",
                        "script": "script",
                    },
                ]
            }
        )
        existsMock.assert_called_once_with("script")
        accessMock.assert_called_once_with("script", X_OK)

    @patch("os.access")
    @patch("os.path.exists")
    @patch("os.path.isabs")
    @patch("os.path.isdir")
    def testAccessAndExistsAreCalledWithCwd(
        self, isdirMock, isabsMock, existsMock, accessMock
    ):
        """
        os.access, os.path.exists, and os.path.isabs must all be called as
        expected, including the cwd from the step, as the specification is
        checked.
        """
        isabsMock.return_value = False
        SlurmPipeline(
            {
                "steps": [
                    {
                        "cwd": "dir",
                        "name": "name",
                        "script": "script",
                    },
                ]
            }
        )
        script = path.join("dir", "script")
        isabsMock.assert_called_once_with("script")
        existsMock.assert_called_once_with(script)
        accessMock.assert_called_once_with(script, X_OK)

    @patch("os.access")
    @patch("os.path.exists")
    @patch("os.path.isabs")
    @patch("os.path.isdir")
    def testAccessAndExistsAreCalledWithAbsolutePathScript(
        self, isdirMock, isabsMock, existsMock, accessMock
    ):
        """
        os.access, os.path.exists, and os.path.isabs must all be called as
        expected when the script path is absolute, as the specification is
        checked.
        """
        SlurmPipeline(
            {
                "steps": [
                    {
                        "cwd": "dir",
                        "name": "name",
                        "script": "/bin/script",
                    },
                ]
            }
        )
        isabsMock.assert_called_once_with("/bin/script")
        existsMock.assert_called_once_with("/bin/script")
        accessMock.assert_called_once_with("/bin/script", X_OK)

    @patch("os.access")
    @patch("os.path.exists")
    def testCollectStepWithNoDependencies(self, existsMock, accessMock):
        """
        If a specification has a 'collect' step with no dependencies,
        a SpecificationError must be raised.
        """
        error = (
            r"^Step 2 \('name2'\) is a 'collect' step but does not have "
            r"any dependencies$"
        )
        self.assertRaisesRegex(
            SpecificationError,
            error,
            SlurmPipeline,
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "collect": True,
                        "name": "name2",
                        "script": "script2",
                    },
                ]
            },
        )

    @patch("os.access")
    @patch("os.path.exists")
    def testCollectStepWithEmptyDependencies(self, existsMock, accessMock):
        """
        If a specification has a 'collect' step with a 'dependencies' key
        whose value is the empty list, a SpecificationError must be raised.
        """
        error = (
            r"^Step 2 \('name2'\) is a 'collect' step but does not have "
            r"any dependencies$"
        )
        self.assertRaisesRegex(
            SpecificationError,
            error,
            SlurmPipeline,
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "collect": True,
                        "dependencies": [],
                        "name": "name2",
                        "script": "script2",
                    },
                ]
            },
        )

    @patch("os.access")
    @patch("os.path.exists")
    def testNonexistentFirstStep(self, existsMock, accessMock):
        """
        If SlurmPipeline is passed a firstStep value that doesn't match
        any of the specification steps, a SpecificationError must be raised.
        """
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script",
                    },
                ]
            }
        )
        error = "^First step 'xxx' not found in specification$"
        self.assertRaisesRegex(SchedulingError, error, sp.schedule, firstStep="xxx")

    @patch("os.access")
    @patch("os.path.exists")
    def testNonexistentLastStep(self, existsMock, accessMock):
        """
        If SlurmPipeline is passed a lastStep value that doesn't match
        any of the specification steps, a SpecificationError must be raised.
        """
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script",
                    },
                ]
            }
        )
        error = "^Last step 'xxx' not found in specification$"
        self.assertRaisesRegex(SchedulingError, error, sp.schedule, lastStep="xxx")

    @patch("os.access")
    @patch("os.path.exists")
    def testLastStepBeforeFirstStep(self, existsMock, accessMock):
        """
        If SlurmPipeline is passed a lastStep value that occurs before the
        first step, a SpecificationError must be raised.
        """
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                ]
            }
        )
        error = (
            r"^Last step \('name1'\) occurs before first step "
            r"\('name2'\) in the specification$"
        )
        self.assertRaisesRegex(
            SchedulingError, error, sp.schedule, firstStep="name2", lastStep="name1"
        )

    def testScheduledTime(self):
        """
        After a specification is scheduled, a float 'scheduledAt' key must be
        added to the specification.
        """
        sp = SlurmPipeline(
            {
                "steps": [],
            }
        )
        self.assertNotIn("scheduledAt", sp.specification)
        specification = sp.schedule()
        self.assertIsInstance(specification["scheduledAt"], float)

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testTaskNameNotPrecededBySpace(self, existsMock, accessMock, subprocessMock):
        """
        If a step script outputs a task name that does not have a space before
        it, the job ids it prints must still be collected correctly.
        """
        subprocessMock.return_value = "TASK:xxx 123 456\n"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        specification = sp.schedule()
        self.assertEqual(
            {
                "xxx": {123, 456},
            },
            specification["steps"]["name1"]["tasks"],
        )

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testTaskOutputFollowedBySpace(self, existsMock, accessMock, subprocessMock):
        """
        If a step script outputs a task line that has trailing space, the job
        ids it prints must still be collected correctly.
        """
        subprocessMock.return_value = "TASK: xxx 123  \n"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        specification = sp.schedule()
        self.assertEqual(
            {
                "xxx": {123},
            },
            specification["steps"]["name1"]["tasks"],
        )

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testTaskOutputFollowedByNonNumber(self, existsMock, accessMock, subprocessMock):
        """
        If a step script outputs a task line that has trailing non-numeric
        text, a SchedulingError must be raised.
        """
        subprocessMock.return_value = "TASK: xxx 123 hello\n"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        error = (
            "^Task name 'xxx' was output with non-numeric job ids by "
            "'script1' script in step named 'name1'. Output line was "
            "'TASK: xxx 123 hello'$"
        )
        self.assertRaisesRegex(SchedulingError, error, sp.schedule)

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testRepeatedTaskName(self, existsMock, accessMock, subprocessMock):
        """
        If a step script outputs a duplicated task name, the job ids
        it outputs must be collected correctly.
        """
        subprocessMock.return_value = "TASK: xxx 123 456\n" "TASK: xxx 123 567\n"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        specification = sp.schedule()
        self.assertEqual(
            {
                "xxx": {123, 456, 567},
            },
            specification["steps"]["name1"]["tasks"],
        )

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testRepeatedTaskJobId(self, existsMock, accessMock, subprocessMock):
        """
        If a step script outputs a duplicated job id for a task name, a
        SchedulingError must be raised.
        """
        subprocessMock.return_value = "TASK: xxx 123 123\n"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        error = (
            r"^Task name 'xxx' was output with a duplicate in "
            r"its job ids \[123, 123\] by 'script1' script in "
            r"step named 'name1'$"
        )
        self.assertRaisesRegex(SchedulingError, error, sp.schedule)

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testTasksFollowingSchedule(self, existsMock, accessMock, subprocessMock):
        """
        If a step script outputs information about tasks it has started, these
        must be correctly recorded in the step dictionary.
        """
        subprocessMock.return_value = "TASK: xxx 123 456\n" "TASK: yyy 234 567\n"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        specification = sp.schedule()
        self.assertEqual(
            {
                "xxx": {123, 456},
                "yyy": {234, 567},
            },
            specification["steps"]["name1"]["tasks"],
        )

    @patch("time.time")
    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testTaskScheduleTime(self, existsMock, accessMock, subprocessMock, timeMock):
        """
        After a step script is scheduled, a float 'scheduledAt' key must be
        added to its step dict.
        """
        timeMock.return_value = 10.0
        subprocessMock.return_value = "TASK: xxx 123 456\n" "TASK: yyy 234 567\n"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        specification = sp.schedule()
        self.assertEqual(specification["steps"]["name1"]["scheduledAt"], 10.0)

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testStepStdout(self, existsMock, accessMock, subprocessMock):
        """
        When a step script is scheduled its standard output must be stored.
        """
        subprocessMock.return_value = (
            "TASK: xxx 123 456\n" "Hello\n" "TASK: yyy 234 567\n"
        )
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        specification = sp.schedule()
        self.assertEqual(
            "TASK: xxx 123 456\nHello\nTASK: yyy 234 567\n",
            specification["steps"]["name1"]["stdout"],
        )

    @patch("time.time")
    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testStepsDict(self, existsMock, accessMock, subprocessMock, timeMock):
        """
        The specification must correctly set its 'steps' convenience dict.
        """
        subprocessMock.return_value = "output"
        timeMock.return_value = 10.0

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                ],
            }
        )
        specification = sp.schedule()
        self.assertEqual(
            {
                "name1": {
                    "environ": {
                        "SP_FORCE": "0",
                        "SP_NICE_ARG": "--nice",
                        "SP_ORIGINAL_ARGS": "",
                        "SP_SKIP": "0",
                    },
                    "name": "name1",
                    "script": "script1",
                    "scheduledAt": 10.0,
                    "skip": False,
                    "stdout": "output",
                    "taskDependencies": {},
                    "tasks": {},
                },
                "name2": {
                    "environ": {
                        "SP_FORCE": "0",
                        "SP_NICE_ARG": "--nice",
                        "SP_ORIGINAL_ARGS": "",
                        "SP_SKIP": "0",
                    },
                    "name": "name2",
                    "scheduledAt": 10.0,
                    "script": "script2",
                    "skip": False,
                    "stdout": "output",
                    "taskDependencies": {},
                    "tasks": {},
                },
            },
            specification["steps"],
        )

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testSingleDependencyTaskNamesJobIdsAndCalls(
        self, existsMock, accessMock, subprocessMock
    ):
        """
        If a step has a dependency on one other step then after scheduling
        it must have its task dependency names and SLURM job ids set correctly
        and the scripts involved must have been called with the expected
        arguments.
        """

        class SideEffect(object):
            def __init__(self):
                self.first = True

            def sideEffect(self, *args, **kwargs):
                if self.first:
                    self.first = False
                    return "TASK: aaa 127 450\n" "TASK: bbb 238 560\n"
                else:
                    return ""

        subprocessMock.side_effect = SideEffect().sideEffect

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "dependencies": ["name1"],
                        "name": "name2",
                        "script": "/bin/script2",
                    },
                ],
            }
        )
        specification = sp.schedule()

        # Step 1 tasks and dependencies.
        self.assertEqual(
            {
                "aaa": {127, 450},
                "bbb": {238, 560},
            },
            specification["steps"]["name1"]["tasks"],
        )
        self.assertEqual({}, specification["steps"]["name1"]["taskDependencies"])

        # Step 2 tasks and dependencies.
        self.assertEqual({}, specification["steps"]["name2"]["tasks"])
        self.assertEqual(
            {
                "aaa": {127, 450},
                "bbb": {238, 560},
            },
            specification["steps"]["name2"]["taskDependencies"],
        )

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                # /bin/script2 is run twice because it depends on
                # 'name1', which starts two jobs (and name2 is not a
                # collector step).
                call(
                    ["/bin/script2", "aaa"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["/bin/script2", "bbb"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        # Check that the dependency environment variable is correct in
        # all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertNotIn("SP_DEPENDENCY_ARG", env1)

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual(
            "--dependency=afterok:127,afterok:450", env2["SP_DEPENDENCY_ARG"]
        )

        env3 = subprocessMock.mock_calls[2][2]["env"]
        self.assertEqual(
            "--dependency=afterok:238,afterok:560", env3["SP_DEPENDENCY_ARG"]
        )

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testSingleDependencySynchronousTaskNamesJobIdsAndCalls(
        self, existsMock, accessMock, subprocessMock
    ):
        """
        If a step has a dependency on one other step then, after scheduling,
        it must have its task dependency names and SLURM job ids set correctly
        and the scripts involved must have been called with the expected
        arguments. In this case, the task names are emitted with no job ids
        because they are completed synchronously. So the dependent task should
        have no SP_DEPENDENCY_ARG set.
        """

        class SideEffect(object):
            def __init__(self):
                self.first = True

            def sideEffect(self, *args, **kwargs):
                if self.first:
                    self.first = False
                    return "TASK: aaa\n" "TASK: bbb\n"
                else:
                    return ""

        subprocessMock.side_effect = SideEffect().sideEffect

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "dependencies": ["name1"],
                        "name": "name2",
                        "script": "/bin/script2",
                    },
                ],
            }
        )
        specification = sp.schedule()

        # Step 1 tasks and dependencies. Two tasks were emitted, but
        # they did not have job ids.
        self.assertEqual(
            {
                "aaa": set(),
                "bbb": set(),
            },
            specification["steps"]["name1"]["tasks"],
        )
        self.assertEqual({}, specification["steps"]["name1"]["taskDependencies"])

        # Step 2 tasks and dependencies. Two tasks were emitted by the
        # step that is depended on, but they did not have job ids.
        self.assertEqual({}, specification["steps"]["name2"]["tasks"])
        self.assertEqual(
            {
                "aaa": set(),
                "bbb": set(),
            },
            specification["steps"]["name2"]["taskDependencies"],
        )

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                # /bin/script2 is run twice because it depends on
                # 'name1', which starts two jobs (and name2 is not a
                # collector step).
                call(
                    ["/bin/script2", "aaa"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["/bin/script2", "bbb"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        # Check that the dependency environment variable is not set in
        # any call.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertNotIn("SP_DEPENDENCY_ARG", env1)

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertNotIn("SP_DEPENDENCY_ARG", env2)

        env3 = subprocessMock.mock_calls[2][2]["env"]
        self.assertNotIn("SP_DEPENDENCY_ARG", env3)

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testSingleCollectorDependencyTaskNamesAndJobIds(
        self, existsMock, accessMock, subprocessMock
    ):
        """
        If a collect step has a dependency on two other steps then after
        scheduling it must have its task dependency names and SLURM job ids
        set correctly.
        """

        class SideEffect(object):
            def __init__(self):
                self.count = 0

            def sideEffect(self, *args, **kwargs):
                self.count += 1
                if self.count == 1:
                    return "TASK: aaa 127 450\n" "TASK: bbb 238 560\n"
                elif self.count == 2:
                    return "TASK: xxx 123 456\n" "TASK: yyy 234 567\n"
                else:
                    return "\n"

        subprocessMock.side_effect = SideEffect().sideEffect

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "collect": True,
                        "dependencies": ["name1", "name2"],
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        specification = sp.schedule()

        # Step 1 tasks and dependencies.
        self.assertEqual(
            {
                "aaa": {127, 450},
                "bbb": {238, 560},
            },
            specification["steps"]["name1"]["tasks"],
        )
        self.assertEqual({}, specification["steps"]["name1"]["taskDependencies"])

        # Step 2 tasks and dependencies.
        self.assertEqual(
            {
                "xxx": {123, 456},
                "yyy": {234, 567},
            },
            specification["steps"]["name2"]["tasks"],
        )
        self.assertEqual({}, specification["steps"]["name2"]["taskDependencies"])

        # Step 3 tasks and dependencies.
        self.assertEqual({}, specification["steps"]["name3"]["tasks"])
        self.assertEqual(
            {
                "aaa": {127, 450},
                "bbb": {238, 560},
                "xxx": {123, 456},
                "yyy": {234, 567},
            },
            specification["steps"]["name3"]["taskDependencies"],
        )

        # Check that check_output was called 3 times, with the
        # expected arguments.
        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script2"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script3", "aaa", "bbb", "xxx", "yyy"],
                    cwd=".",
                    stdin=DEVNULL,
                    universal_newlines=True,
                    env=ANY,
                ),
            ]
        )

        # Check that the dependency environment variable we set is correct
        # in all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertNotIn("SP_DEPENDENCY_ARG", env1)

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertNotIn("SP_DEPENDENCY_ARG", env2)

        env3 = subprocessMock.mock_calls[2][2]["env"]
        self.assertEqual(
            (
                "--dependency="
                "afterok:123,afterok:127,afterok:234,afterok:238,"
                "afterok:450,afterok:456,afterok:560,afterok:567"
            ),
            env3["SP_DEPENDENCY_ARG"],
        )
        self.assertEqual("", env3["SP_ORIGINAL_ARGS"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testSingleCollectorDependencyNoJobIds(
        self, existsMock, accessMock, subprocessMock
    ):
        """
        If a collect step has a dependency on two other steps but those steps
        emit no jobs then the script for the step must be run with no
        SP_DEPENDENCY_ARG value.
        """

        subprocessMock.return_value = ""

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "collect": True,
                        "dependencies": ["name1", "name2"],
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        sp.schedule()
        env = subprocessMock.mock_calls[2][2]["env"]
        self.assertNotIn("SP_DEPENDENCY_ARG", env)

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testStartAfter(self, existsMock, accessMock, subprocessMock):
        """
        If a step has no dependencies but a startAfter value is passed to
        schedule, it must have the expected SP_DEPENDENCY_ARG value set
        in its environment.
        """
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name",
                        "script": "script",
                    },
                ],
            }
        )
        sp.schedule(startAfter=[35, 36])

        # Check that the dependency environment variable is correct.
        env = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("--dependency=afterok:35,afterok:36", env["SP_DEPENDENCY_ARG"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testDependencyEmitsNoTasksButThereIsAStartAfterList(
        self, existsMock, accessMock, subprocessMock
    ):
        """
        If a step has a dependency and the dependency emits no tasks but there
        is a startAfter list of jobs ids, the value of SP_DEPENDENCY_ARG must
        contain the start after jobs.
        """
        subprocessMock.return_value = ""

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "dependencies": ["name1"],
                        "name": "name2",
                        "script": "script2",
                    },
                ],
            }
        )
        sp.schedule(startAfter=(1, 3))

        # Check that the dependency environment variable is correct in
        # all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("--dependency=afterok:1,afterok:3", env1["SP_DEPENDENCY_ARG"])

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual("--dependency=afterok:1,afterok:3", env2["SP_DEPENDENCY_ARG"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testDependencyEmitsNoTasksButThereIsAStartAfterListErrorStep(
        self, existsMock, accessMock, subprocessMock
    ):
        """
        If an error step has a dependency and the dependency emits no tasks
        but there is a startAfter list of jobs ids, the value of
        SP_DEPENDENCY_ARG must contain the start after jobs and use afternotok.
        """
        subprocessMock.return_value = ""

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "dependencies": ["name1"],
                        "error step": True,
                        "name": "name2",
                        "script": "script2",
                    },
                ],
            }
        )
        sp.schedule(startAfter=(1, 3))

        # Check that the dependency environment variable is correct in
        # all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("--dependency=afterok:1,afterok:3", env1["SP_DEPENDENCY_ARG"])

        # The second step must be have afternotok in its SP_DEPENDENCY_ARG
        # variable.
        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual(
            "--dependency=afternotok:1?afternotok:3", env2["SP_DEPENDENCY_ARG"]
        )

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    @patch("os.path.isdir")
    def testCwdWithRelativeScriptPath(
        self, isdirMock, existsMock, accessMock, subprocessMock
    ):
        """
        If a step has a cwd set and its script is a relative path, the path of
        the script that is executed must be as specified (not converted to an
        absolute path).
        """
        subprocessMock.return_value = ""

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "cwd": "/tmp",
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        sp.schedule()

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd="/tmp",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testScriptArgWithSingleQuote(self, existsMock, accessMock, subprocessMock):
        """
        If a script argument contains a single quote, a SchedulingError must
        be raised.
        """
        subprocessMock.return_value = ""

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script",
                    },
                ]
            }
        )
        error = (
            r"^Script argument \"don't ask me\" contains a single "
            r"quote, which is currently not supported\.$"
        )
        self.assertRaisesRegex(
            SchedulingError, error, sp.schedule, scriptArgs=["don't ask me", 3]
        )

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testScriptArgs(self, existsMock, accessMock, subprocessMock):
        """
        If script arguments are given to SlurmPipeline, they must be passed
        to the executed scripts that have no dependencies. Steps that have
        dependencies must be called with the name of the task on the command
        line and the correct job numbers. The script args must also appear
        (single quoted) in the SP_ORIGINAL_ARGS variable in the environment
        of all scripts.
        """

        class SideEffect(object):
            def __init__(self):
                self.count = 0

            def sideEffect(self, *args, **kwargs):
                self.count += 1
                if self.count == 1:
                    return "TASK: aaa 127 450\n" "TASK: bbb 238 560\n"
                else:
                    return "\n"

        subprocessMock.side_effect = SideEffect().sideEffect

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "dependencies": ["name1"],
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        sp.schedule(scriptArgs=["hey", 3])

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1", "hey", "3"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script2", "hey", "3"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script3", "aaa"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script3", "bbb"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        # Check that the environment variables we set were correct
        # in all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertNotIn("SP_DEPENDENCY_ARG", env1)
        self.assertEqual("'hey' '3'", env1["SP_ORIGINAL_ARGS"])

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertNotIn("SP_DEPENDENCY_ARG", env2)
        self.assertEqual("'hey' '3'", env1["SP_ORIGINAL_ARGS"])

        env3 = subprocessMock.mock_calls[2][2]["env"]
        self.assertEqual(
            "--dependency=afterok:127,afterok:450", env3["SP_DEPENDENCY_ARG"]
        )
        self.assertEqual("'hey' '3'", env1["SP_ORIGINAL_ARGS"])

        env4 = subprocessMock.mock_calls[3][2]["env"]
        self.assertEqual(
            "--dependency=afterok:238,afterok:560", env4["SP_DEPENDENCY_ARG"]
        )
        self.assertEqual("'hey' '3'", env1["SP_ORIGINAL_ARGS"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testForce(self, existsMock, accessMock, subprocessMock):
        """
        If force=True is given to SlurmPipeline, SP_FORCE must be set to '1'
        in the step execution environment.
        """
        subprocessMock.return_value = ""

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        sp.schedule(force=True)

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        env = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("1", env["SP_FORCE"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testDefaultNice(self, existsMock, accessMock, subprocessMock):
        """
        If no nice value is given to schedule, SP_NICE_ARG must be set to
        '--nice' in the step execution environment.
        """
        subprocessMock.return_value = ""

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        sp.schedule()

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        env = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("--nice", env["SP_NICE_ARG"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testSpecificNice(self, existsMock, accessMock, subprocessMock):
        """
        If a specific nice value is given to schedule, SP_NICE_ARG must be set
        to the expected value in the step execution environment.
        """
        subprocessMock.return_value = ""

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        sp.schedule(nice=40)

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        env = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("--nice=40", env["SP_NICE_ARG"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testFirstStepOnly(self, existsMock, accessMock, subprocessMock):
        """
        If firstStep (bot not lastStep) is specified for a SlurmPipeline the
        correct SP_SKIP value must be set in the environment.
        """
        subprocessMock.return_value = ""
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                ],
            }
        )
        sp.schedule(firstStep="name2")

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script2"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        # Check that the SP_SKIP environment variable is correct in all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("1", env1["SP_SKIP"])

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual("0", env2["SP_SKIP"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testLastStepOnly(self, existsMock, accessMock, subprocessMock):
        """
        If lastStep (but not firstStep) is specified for a SlurmPipeline the
        correct SP_SKIP value must be set in the environment.
        """
        subprocessMock.return_value = ""
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        sp.schedule(lastStep="name2")

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script2"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script3"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        # Check that the SP_SKIP environment variable is correct in all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("0", env1["SP_SKIP"])

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual("0", env2["SP_SKIP"])

        env2 = subprocessMock.mock_calls[2][2]["env"]
        self.assertEqual("1", env2["SP_SKIP"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testFirstStepAndLastStepDifferent(self, existsMock, accessMock, subprocessMock):
        """
        If firstStep and lastStep are specified for a SlurmPipeline and the
        steps are not the same, the correct SP_SKIP value must be set
        correctly in the environment.
        """
        subprocessMock.return_value = ""
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "name": "name3",
                        "script": "script3",
                    },
                    {
                        "name": "name4",
                        "script": "script4",
                    },
                ],
            }
        )
        sp.schedule(firstStep="name2", lastStep="name3")

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script2"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script3"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script4"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        # Check that the SP_SKIP environment variable is correct in all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("1", env1["SP_SKIP"])

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual("0", env2["SP_SKIP"])

        env3 = subprocessMock.mock_calls[2][2]["env"]
        self.assertEqual("0", env3["SP_SKIP"])

        env4 = subprocessMock.mock_calls[3][2]["env"]
        self.assertEqual("1", env4["SP_SKIP"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testFirstStepAndLastStepSame(self, existsMock, accessMock, subprocessMock):
        """
        If firstStep and lastStep are specified for a SlurmPipeline and the
        steps are the same, the correct SP_SKIP value must be set
        correctly in the environment.
        """
        subprocessMock.return_value = ""
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        sp.schedule(firstStep="name2", lastStep="name2")

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script2"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script3"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        # Check that the SP_SKIP environment variable is correct in all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("1", env1["SP_SKIP"])

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual("0", env2["SP_SKIP"])

        env3 = subprocessMock.mock_calls[2][2]["env"]
        self.assertEqual("1", env3["SP_SKIP"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testFirstStepAndNoLastStep(self, existsMock, accessMock, subprocessMock):
        """
        If firstStep is specified and lastStep is not, the correct SP_SKIP
        value must be set correctly in the environment.
        """
        subprocessMock.return_value = ""
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        sp.schedule(firstStep="name2")

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script2"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script3"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        # Check that the SP_SKIP environment variable is correct in all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("1", env1["SP_SKIP"])

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual("0", env2["SP_SKIP"])

        env3 = subprocessMock.mock_calls[2][2]["env"]
        self.assertEqual("0", env3["SP_SKIP"])

    @patch("subprocess.check_output")
    @patch("time.sleep")
    @patch("os.access")
    @patch("os.path.exists")
    def testSleep(self, existsMock, accessMock, sleepMock, subprocessMock):
        """
        If a sleep argument is given to SlurmPipeline, sleep must be called
        between steps with the expected number of seconds.
        """
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "dependencies": ["name1"],
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        sp.schedule(sleep=1.0)

        sleepMock.assert_has_calls([call(1.0), call(1.0)])

    @patch("subprocess.check_output")
    @patch("time.sleep")
    @patch("os.access")
    @patch("os.path.exists")
    def testSleepNotCalledByDefault(
        self, existsMock, accessMock, sleepMock, subprocessMock
    ):
        """
        If no sleep argument is given to SlurmPipeline, sleep must not be
        called.
        """
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "dependencies": ["name1"],
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        sp.schedule()

        self.assertFalse(sleepMock.called)

    @patch("subprocess.check_output")
    @patch("time.sleep")
    @patch("os.access")
    @patch("os.path.exists")
    def testSleepNotCalledWhenZero(
        self, existsMock, accessMock, sleepMock, subprocessMock
    ):
        """
        If a sleep argument of 0.0 is given to SlurmPipeline, sleep must not be
        called.
        """
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "dependencies": ["name1"],
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        sp.schedule(sleep=0.0)

        self.assertFalse(sleepMock.called)

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testSkipNonexistentStep(self, existsMock, accessMock, subprocessMock):
        """
        If the passed skip argument contains a non-existent step name, a
        SchedulingError must be raised.
        """
        error = r"^Unknown skip step \(xxx\) passed to schedule$"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name",
                        "script": "script",
                    },
                ]
            }
        )
        self.assertRaisesRegex(SchedulingError, error, sp.schedule, skip={"xxx"})

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testSkipNonexistentSteps(self, existsMock, accessMock, subprocessMock):
        """
        If the passed skip argument contains two non-existent step names, a
        SchedulingError must be raised.
        """
        error = r"^Unknown skip steps \(xxx, yyy\) passed to schedule$"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name",
                        "script": "script",
                    },
                ]
            }
        )
        self.assertRaisesRegex(SchedulingError, error, sp.schedule, skip={"xxx", "yyy"})

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testSkipNone(self, existsMock, accessMock, subprocessMock):
        """
        If no steps are skipped, the SP_SKIP environment variable must be 0
        in each step script.
        """
        subprocessMock.return_value = ""
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        sp.schedule()

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script2"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script3"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        # Check that the SP_SKIP environment variable is 0 in all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("0", env1["SP_SKIP"])

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual("0", env2["SP_SKIP"])

        env3 = subprocessMock.mock_calls[2][2]["env"]
        self.assertEqual("0", env3["SP_SKIP"])

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testSkipTwo(self, existsMock, accessMock, subprocessMock):
        """
        If two steps are skipped, the SP_SKIP variable in their environments
        must be set to 1.
        """
        subprocessMock.return_value = ""
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "name": "name2",
                        "script": "script2",
                    },
                    {
                        "name": "name3",
                        "script": "script3",
                    },
                ],
            }
        )
        sp.schedule(skip={"name2", "name3"})

        subprocessMock.assert_has_calls(
            [
                call(
                    ["script1"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script2"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
                call(
                    ["script3"],
                    cwd=".",
                    universal_newlines=True,
                    stdin=DEVNULL,
                    env=ANY,
                ),
            ]
        )

        # Check that the SP_SKIP environment variable is 0 in all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertEqual("0", env1["SP_SKIP"])

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual("1", env2["SP_SKIP"])

        env3 = subprocessMock.mock_calls[2][2]["env"]
        self.assertEqual("1", env3["SP_SKIP"])

    @patch("subprocess.check_output")
    @patch("time.time")
    @patch("os.access")
    @patch("os.path.exists")
    def testJSON(self, existsMock, accessMock, timeMock, subprocessMock):
        """
        It must be possible to convert a scheduled specification to JSON.
        """
        subprocessMock.return_value = "TASK: xxx 123\n"
        timeMock.return_value = 10.0

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "dependencies": ["name1"],
                        "name": "name2",
                        "script": "script2",
                    },
                ]
            }
        )
        specification = sp.schedule(firstStep="name2", force=True)
        expected = dumps(
            {
                "user": getuser(),
                "firstStep": "name2",
                "lastStep": None,
                "nice": None,
                "force": True,
                "scheduledAt": 10.0,
                "scriptArgs": None,
                "skip": [],
                "sleep": 0.0,
                "startAfter": None,
                "steps": [
                    {
                        "environ": {
                            "SP_FORCE": "1",
                            "SP_NICE_ARG": "--nice",
                            "SP_ORIGINAL_ARGS": "",
                            "SP_SKIP": "1",
                        },
                        "name": "name1",
                        "scheduledAt": 10.0,
                        "script": "script1",
                        "skip": True,
                        "stdout": "TASK: xxx 123\n",
                        "taskDependencies": {},
                        "tasks": {
                            "xxx": [
                                123,
                            ],
                        },
                    },
                    {
                        "environ": {
                            "SP_DEPENDENCY_ARG": "--dependency=afterok:123",
                            "SP_FORCE": "1",
                            "SP_NICE_ARG": "--nice",
                            "SP_ORIGINAL_ARGS": "",
                            "SP_SKIP": "0",
                        },
                        "dependencies": ["name1"],
                        "name": "name2",
                        "scheduledAt": 10.0,
                        "script": "script2",
                        "skip": False,
                        "stdout": "TASK: xxx 123\n",
                        "taskDependencies": {
                            "xxx": [
                                123,
                            ],
                        },
                        "tasks": {
                            "xxx": [
                                123,
                            ],
                        },
                    },
                ],
            },
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
        self.assertEqual(expected, sp.specificationToJSON(specification))

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testErrorStep(self, existsMock, accessMock, subprocessMock):
        """
        If a step is an error step its script must be run with the expected
        value of SP_DEPENDENCY_ARG.
        """

        class SideEffect(object):
            def __init__(self):
                self.first = True

            def sideEffect(self, *args, **kwargs):
                if self.first:
                    self.first = False
                    return "TASK: aaa 127 450\n" "TASK: bbb 238 560\n"
                else:
                    return ""

        subprocessMock.side_effect = SideEffect().sideEffect

        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                    {
                        "dependencies": ["name1"],
                        "error step": True,
                        "name": "name2",
                        "script": "script2",
                    },
                ],
            }
        )
        sp.schedule()

        # Check that the dependency environment variable is correct in
        # all calls.
        env1 = subprocessMock.mock_calls[0][2]["env"]
        self.assertNotIn("SP_DEPENDENCY_ARG", env1)

        env2 = subprocessMock.mock_calls[1][2]["env"]
        self.assertEqual(
            "--dependency=afternotok:127?afternotok:450", env2["SP_DEPENDENCY_ARG"]
        )

        env3 = subprocessMock.mock_calls[2][2]["env"]
        self.assertEqual(
            "--dependency=afternotok:238?afternotok:560", env3["SP_DEPENDENCY_ARG"]
        )

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testStringNice(self, existsMock, accessMock, subprocessMock):
        """
        If a string nice value is passed to schedule, a SchedulingError
        must be raised.
        """
        subprocessMock.return_value = "TASK: xxx 123\n"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        error = r"^Nice \(priority\) value 'x' is not numeric$"
        self.assertRaisesRegex(SchedulingError, error, sp.schedule, nice="x")

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testNiceTooBig(self, existsMock, accessMock, subprocessMock):
        """
        If a nice value that is too big (> 10000) is passed to schedule, a
        SchedulingError must be raised.
        """
        subprocessMock.return_value = "TASK: xxx 123\n"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        error = (
            r"^Nice \(priority\) value 10001 is outside the allowed "
            r"\[-10000, 10000\] range$"
        )
        self.assertRaisesRegex(SchedulingError, error, sp.schedule, nice=10001)

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    def testNiceTooSmall(self, existsMock, accessMock, subprocessMock):
        """
        If a nice value that is too small (< -10000) is passed to schedule, a
        SchedulingError must be raised.
        """
        subprocessMock.return_value = "TASK: xxx 123\n"
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )
        error = (
            r"^Nice \(priority\) value -10001 is outside the allowed "
            r"\[-10000, 10000\] range$"
        )
        self.assertRaisesRegex(SchedulingError, error, sp.schedule, nice=-10001)

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    @patch("os.path.isdir")
    def testSubprocessExecRaisesCalledProcessError(
        self, isdirMock, existsMock, accessMock, subprocessMock
    ):
        """
        If subprocess.check_output raises CalledProcessError, we must
        raise a corresponding SchedulingError.
        """
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "cwd": "dir",
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )

        if version_info >= (3, 5):
            subprocessMock.side_effect = CalledProcessError(
                3, "command.sh", output="the stdout", stderr="the stderr"
            )

            error = (
                r"^Could not execute step 'name1' script 'script1' in "
                r"directory 'dir'\. Attempted command: 'command.sh'\. "
                r"Exit status: 3\. Standard output: 'the stdout'\. "
                r"Standard error: 'the stderr'\.$"
            )
        else:
            subprocessMock.side_effect = CalledProcessError(3, "command.sh")

            error = (
                r"^Could not execute step 'name1' script 'script1' in "
                r"directory 'dir'\. Attempted command: 'command.sh'\. "
                r"Exit status: 3\.$"
            )

        self.assertRaisesRegex(SchedulingError, error, sp.schedule)

    @patch("subprocess.check_output")
    @patch("os.access")
    @patch("os.path.exists")
    @patch("os.path.isdir")
    def testSubprocessExecRaisesOSError(
        self, isdirMock, existsMock, accessMock, subprocessMock
    ):
        """
        If subprocess.check_output raises CalledProcessError, we must
        raise a corresponding SchedulingError.
        """
        sp = SlurmPipeline(
            {
                "steps": [
                    {
                        "cwd": "dir",
                        "name": "name1",
                        "script": "script1",
                    },
                ],
            }
        )

        subprocessMock.side_effect = OSError("No such file or directory: script1")

        error = (
            r"^Could not execute step 'name1' script 'script1' in directory "
            r"'dir'\. Attempted command: 'script1'\. Error: No such file or "
            r"directory: script1$"
        )

        self.assertRaisesRegex(SchedulingError, error, sp.schedule)
