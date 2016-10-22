from os import X_OK
from unittest import TestCase
from six.moves import builtins
from six import assertRaisesRegex, PY3
from json import dumps
import subprocess

from slurm_pipeline.pipeline import (
    SlurmPipeline, SpecificationError, SchedulingError)

try:
    from unittest.mock import ANY, call, patch
except ImportError:
    from mock import ANY, call, patch

from .mocking import mockOpen


class TestRunner(TestCase):
    """
    Tests for the pipeline.runner.SlurmPipeline class.
    """

    def testEmptyJSON(self):
        """
        If the specification file is empty, a ValueError must be raised.
        """
        data = ''
        mockOpener = mockOpen(read_data=data)
        with patch.object(builtins, 'open', mockOpener):
            if PY3:
                error = '^Expecting value: line 1 column 1 \(char 0\)$'
            else:
                error = '^No JSON object could be decoded$'
            assertRaisesRegex(self, ValueError, error, SlurmPipeline, 'file')

    def testInvalidJSON(self):
        """
        If the specification file does not contain valid JSON, a ValueError
        must be raised.
        """
        data = '{'
        mockOpener = mockOpen(read_data=data)
        with patch.object(builtins, 'open', mockOpener):
            if PY3:
                error = ('^Expecting property name enclosed in double '
                         'quotes: line 1 column 2 \(char 1\)$')
            else:
                error = '^Expecting object: line 1 column 1 \(char 0\)$'
            assertRaisesRegex(self, ValueError, error, SlurmPipeline, 'file')

    def testJSONList(self):
        """
        If the specification file contains valid JSON but is a list instead
        of a JSON object, a SpecificationError must be raised.
        """
        data = '[]'
        mockOpener = mockOpen(read_data=data)
        with patch.object(builtins, 'open', mockOpener):
            error = ('^The specification must be a dict \(i\.e\., a JSON '
                     'object when loaded from a file\)$')
            assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                              'file')

    def testList(self):
        """
        If the specification is passed a list directly instead of a dict, a
        SpecificationError must be raised.
        """
        error = ('^The specification must be a dict \(i\.e\., a JSON '
                 'object when loaded from a file\)$')
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline, [])

    def testNoSteps(self):
        """
        If the specification dict does not contain a 'steps' key, a
        SpecificationError must be raised.
        """
        error = '^The specification must have a top-level "steps" key$'
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline, {})

    def testStepsMustBeAList(self):
        """
        If the specification dict does not contain a 'steps' key whose value
        is a list, a SpecificationError must be raised.
        """
        error = '^The "steps" key must be a list$'
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {'steps': None})

    def testNonDictionaryStep(self):
        """
        If the specification steps contains a step that is not a dict, a
        SpecificationError must be raised.
        """
        error = '^Step 1 is not a dictionary$'
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {
                              'steps': [
                                  None,
                              ]
                          })

    @patch('os.access')
    @patch('os.path.exists')
    def testAccessAndExistsAreCalled(self, existsMock, accessMock):
        """
        Both os.access and os.path.exists must be called as expected
        as the specification is checked.
        """
        SlurmPipeline(
            {
                'steps': [
                    {
                        'name': 'name',
                        'script': 'script',
                    },
                ]
            })
        existsMock.assert_called_once_with('script')
        accessMock.assert_called_once_with('script', X_OK)

    @patch('os.access')
    @patch('os.path.exists')
    def testStepWithoutScript(self, existsMock, accessMock):
        """
        If the specification steps contains a step that does not have a
        'script' key, a SpecificationError must be raised.
        """
        error = '^Step 2 does not have a "script" key$'
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {
                              'steps': [
                                  {
                                      'name': 'name',
                                      'script': 'script',
                                  },
                                  {
                                  },
                              ]
                          })

    def testNonStringScript(self):
        """
        If a step has a 'script' key that is not a string, a SpecificationError
        must be raised.
        """
        error = '^The "script" key in step 1 is not a string$'
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {
                              'steps': [
                                  {
                                      'script': None,
                                  },
                              ]
                          })

    def testNonexistentScript(self):
        """
        If a step has a 'script' key that mentions a non-existent file, a
        SpecificationError must be raised.
        """
        error = "^The script 'script' in step 1 does not exist$"
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {
                              'steps': [
                                  {
                                      'script': 'script',
                                  },
                              ]
                          })

    @patch('os.access')
    @patch('os.path.exists')
    def testStepWithoutName(self, existsMock, accessMock):
        """
        If the specification steps contains a step that does not have a
        'name' key, a SpecificationError must be raised.
        """
        error = '^Step 1 does not have a "name" key$'
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {
                              'steps': [
                                  {
                                      'script': 'script',
                                  },
                              ]
                          })

    @patch('os.access')
    @patch('os.path.exists')
    def testNonStringName(self, existsMock, accessMock):
        """
        If a step has a 'name' key that is not a string, a SpecificationError
        must be raised.
        """
        error = '^The "name" key in step 1 is not a string$'
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {
                              'steps': [
                                  {
                                      'name': None,
                                      'script': 'script',
                                  },
                              ]
                          })

    @patch('os.access')
    @patch('os.path.exists')
    def testDuplicateName(self, existsMock, accessMock):
        """
        If two steps have the same name, a SpecificationError must be raised.
        specification.
        """
        error = ("^The name 'name' of step 2 was already used in an "
                 "earlier step$")
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {
                              'steps': [
                                  {
                                      'name': 'name',
                                      'script': 'script1',
                                  },
                                  {
                                      'name': 'name',
                                      'script': 'script2',
                                  },
                              ],
                          })

    @patch('os.access')
    @patch('os.path.exists')
    def testNonListDependencies(self, existsMock, accessMock):
        """
        If a step has a 'dependencies' key that is not a list, a
        SpecificationError must be raised.
        """
        error = '^Step 1 has a non-list "dependencies" key$'
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {
                              'steps': [
                                  {
                                      'dependencies': None,
                                      'name': 'name',
                                      'script': 'script',
                                  },
                              ]
                          })

    @patch('os.access')
    @patch('os.path.exists')
    def testNonExistentDependency(self, existsMock, accessMock):
        """
        If a step has a 'dependencies' key that mentions an unknown step,
        a SpecificationError must be raised.
        """
        error = ("^Step 2 depends on a non-existent \(or not-yet-"
                 "defined\) step: 'unknown'$")
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {
                              'steps': [
                                  {
                                      'name': 'name1',
                                      'script': 'script',
                                  },
                                  {
                                      'dependencies': ['unknown'],
                                      'name': 'name2',
                                      'script': 'script',
                                  },
                              ]
                          })

    @patch('os.access')
    @patch('os.path.exists')
    def testNonYetDefinedDependency(self, existsMock, accessMock):
        """
        If a step has a 'dependencies' key that mentions a step that exists
        but that has not yet been defined in the specification steps, a
        SpecificationError must be raised.
        """
        error = ("^Step 1 depends on a non-existent \(or not-yet-"
                 "defined\) step: 'name2'$")
        assertRaisesRegex(self, SpecificationError, error, SlurmPipeline,
                          {
                              'steps': [
                                  {
                                      'dependencies': ['name2'],
                                      'name': 'name1',
                                      'script': 'script',
                                  },
                                  {
                                      'name': 'name2',
                                      'script': 'script',
                                  },
                              ]
                          })

    @patch('os.access')
    @patch('os.path.exists')
    def testSpecificationIsStored(self, existsMock, accessMock):
        """
        If well-formed JSON is passed, it must be read and stored as the
        specification.
        """
        specification = {
            'steps': [
                {
                    'name': 'name1',
                    'script': 'script1',
                },
                {
                    'name': 'name2',
                    'script': 'script2',
                },
            ],
        }
        data = dumps(specification)
        mockOpener = mockOpen(read_data=data)
        with patch.object(builtins, 'open', mockOpener):
            runner = SlurmPipeline('file')
            self.assertEqual(specification, runner.specification)

    def testScheduledTime(self):
        """
        After a specification is scheduled, a float 'scheduledAt' key must be
        added to the specification.
        """
        runner = SlurmPipeline(
            {
                'steps': [],
            })
        self.assertNotIn('scheduledAt', runner.specification)
        runner.schedule()
        self.assertIsInstance(runner.specification['scheduledAt'], float)

    @patch('os.access')
    @patch('os.path.exists')
    def testReSchedule(self, existsMock, accessMock):
        """
        Trying to re-schedule an execution that has already been scheduled must
        result in a SchedulingError.
        """
        with patch.object(subprocess, 'check_output',
                          return_value='Submitted batch job 4\n'):
            runner = SlurmPipeline(
                    {
                        'steps': [
                            {
                                'name': 'name1',
                                'script': 'script1',
                            },
                        ],
                    })
            runner.schedule()
            error = '^Specification has already been scheduled$'
            assertRaisesRegex(self, SchedulingError, error,
                              runner.schedule)

    @patch('os.access')
    @patch('os.path.exists')
    def testRepeatedTaskName(self, existsMock, accessMock):
        """
        If a step script outputs a duplicated task name, the job ids
        it outputs must be collected correctly.
        """
        with patch.object(subprocess, 'check_output',
                          return_value=('TASK: xxx 123 456\n'
                                        'TASK: xxx 123 567\n')):
            runner = SlurmPipeline(
                {
                    'steps': [
                        {
                            'name': 'name1',
                            'script': 'script1',
                        },
                    ],
                })
            runner.schedule()
            self.assertEqual(
                {
                    'xxx': {123, 456, 567},
                },
                runner.steps['name1']['tasks'])

    @patch('os.access')
    @patch('os.path.exists')
    def testRepeatedTaskJobId(self, existsMock, accessMock):
        """
        If a step script outputs a duplicated job id for a task name, a
        SchedulingError must be raised.
        """
        with patch.object(subprocess, 'check_output',
                          return_value='TASK: xxx 123 123\n'):
            runner = SlurmPipeline(
                {
                    'steps': [
                        {
                            'name': 'name1',
                            'script': 'script1',
                        },
                    ],
                })
            error = ("^Task name 'xxx' was output with a duplicate in "
                     "its job ids \[123, 123\] by 'script1' script in "
                     "step named 'name1'$")
            assertRaisesRegex(self, SchedulingError, error,
                              runner.schedule)

    @patch('os.access')
    @patch('os.path.exists')
    def testTasksFollowingSchedule(self, existsMock, accessMock):
        """
        If a step script outputs information about tasks it has started, these
        must be correctly recorded in the step dictionary.
        """
        with patch.object(subprocess, 'check_output',
                          return_value=('TASK: xxx 123 456\n'
                                        'TASK: yyy 234 567\n')):
            runner = SlurmPipeline(
                {
                    'steps': [
                        {
                            'name': 'name1',
                            'script': 'script1',
                        },
                    ],
                })
            runner.schedule()
            self.assertEqual(
                {
                    'xxx': {123, 456},
                    'yyy': {234, 567},
                },
                runner.steps['name1']['tasks'])

    @patch('os.access')
    @patch('os.path.exists')
    def testTaskScheduleTime(self, existsMock, accessMock):
        """
        After a step script is scheduled, a float 'scheduledAt' key must be
        added to its step dict.
        """
        with patch.object(subprocess, 'check_output',
                          return_value=('TASK: xxx 123 456\n'
                                        'TASK: yyy 234 567\n')):
            runner = SlurmPipeline(
                {
                    'steps': [
                        {
                            'name': 'name1',
                            'script': 'script1',
                        },
                    ],
                })
            step = runner.steps['name1']
            self.assertNotIn('scheduledAt', step)
            runner.schedule()
            self.assertIsInstance(step['scheduledAt'], float)

    @patch('os.access')
    @patch('os.path.exists')
    def testStepImplicitCwd(self, existsMock, accessMock):
        """
        When a step script is scheduled and no current working directory (cwd)
        is explicitly set, the cwd must be '.'.
        """
        with patch.object(subprocess, 'check_output', return_value=''):
            runner = SlurmPipeline(
                {
                    'steps': [
                        {
                            'name': 'name1',
                            'script': '/usr/local/bin/script',
                        },
                    ],
                })
            runner.schedule()
            self.assertEqual('.', runner.steps['name1']['cwd'])

    @patch('os.access')
    @patch('os.path.exists')
    def testStepStdout(self, existsMock, accessMock):
        """
        When a step script is scheduled its standard output must be stored.
        """
        with patch.object(subprocess, 'check_output',
                          return_value=('TASK: xxx 123 456\n'
                                        'Hello\n'
                                        'TASK: yyy 234 567\n')):
            runner = SlurmPipeline(
                {
                    'steps': [
                        {
                            'name': 'name1',
                            'script': 'script1',
                        },
                    ],
                })
            runner.schedule()
            self.assertEqual(
                'TASK: xxx 123 456\nHello\nTASK: yyy 234 567\n',
                runner.steps['name1']['stdout'])

    @patch('os.access')
    @patch('os.path.exists')
    def testStepsDict(self, existsMock, accessMock):
        """
        The specification must correctly set its 'steps' convenience dict.
        """
        runner = SlurmPipeline(
            {
                'steps': [
                    {
                        'name': 'name1',
                        'script': 'script1',
                    },
                    {
                        'name': 'name2',
                        'script': 'script2',
                    },
                ],
            })
        self.assertEqual(
            {
                'name1': {
                    'name': 'name1',
                    'script': 'script1',
                },
                'name2': {
                    'name': 'name2',
                    'script': 'script2',
                },
            },
            runner.steps)

    @patch('os.access')
    @patch('os.path.exists')
    def testSingleDependencyTaskNamesJobIdsAndCalls(self, existsMock,
                                                    accessMock):
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
                    return ('TASK: aaa 127 450\n'
                            'TASK: bbb 238 560\n')
                else:
                    return ''

        sideEffect = SideEffect()

        with patch.object(subprocess, 'check_output') as mockMethod:
            mockMethod.side_effect = sideEffect.sideEffect
            runner = SlurmPipeline(
                {
                    'steps': [
                        {
                            'name': 'name1',
                            'script': 'script1',
                        },
                        {
                            'dependencies': ['name1'],
                            'name': 'name2',
                            'script': '/bin/script2',
                        },
                    ],
                })
            runner.schedule()

            # Step 1 tasks and dependencies.
            self.assertEqual(
                {
                    'aaa': {127, 450},
                    'bbb': {238, 560},
                },
                runner.steps['name1']['tasks'])
            self.assertEqual({}, runner.steps['name1']['taskDependencies'])

            # Step 2 tasks and dependencies.
            self.assertEqual({}, runner.steps['name2']['tasks'])
            self.assertEqual(
                {
                    'aaa': {127, 450},
                    'bbb': {238, 560},
                },
                runner.steps['name2']['taskDependencies'])

            mockMethod.assert_has_calls([
                call(['script1'], cwd='.', universal_newlines=True, env=ANY),
                # /bin/script2 is run twice because it depends on
                # 'name1', which starts two jobs (and name2 is not a
                # collector step).
                call(['/bin/script2'], cwd='.', universal_newlines=True,
                     env=ANY),
                call(['/bin/script2'], cwd='.', universal_newlines=True,
                     env=ANY),
            ])

            # Check that the two environment variables are correct in
            # all calls.
            env1 = mockMethod.mock_calls[0][2]['env']
            self.assertNotIn('SP_TASK_NAME', env1)
            self.assertNotIn('SP_DEPENDENCY_ARG', env1)

            env2 = mockMethod.mock_calls[1][2]['env']
            self.assertEqual('aaa', env2['SP_TASK_NAME'])
            self.assertEqual('--dependency=afterok:127,afterok:450',
                             env2['SP_DEPENDENCY_ARG'])

            env3 = mockMethod.mock_calls[2][2]['env']
            self.assertEqual('bbb', env3['SP_TASK_NAME'])
            self.assertEqual('--dependency=afterok:238,afterok:560',
                             env3['SP_DEPENDENCY_ARG'])

    @patch('os.access')
    @patch('os.path.exists')
    def testSingleCollectorDependencyTaskNamesAndJobIds(self, existsMock,
                                                        accessMock):
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
                    return ('TASK: aaa 127 450\n'
                            'TASK: bbb 238 560\n')
                elif self.count == 2:
                    return ('TASK: xxx 123 456\n'
                            'TASK: yyy 234 567\n')
                else:
                    return '\n'

        sideEffect = SideEffect()

        with patch.object(subprocess, 'check_output') as mockMethod:
            mockMethod.side_effect = sideEffect.sideEffect
            runner = SlurmPipeline(
                {
                    'steps': [
                        {
                            'name': 'name1',
                            'script': 'script1',
                        },
                        {
                            'name': 'name2',
                            'script': 'script2',
                        },
                        {
                            'collect': True,
                            'dependencies': ['name1', 'name2'],
                            'name': 'name3',
                            'script': 'script3',
                        },
                    ],
                })
            runner.schedule()

            # Step 1 tasks and dependencies.
            self.assertEqual(
                {
                    'aaa': {127, 450},
                    'bbb': {238, 560},
                },
                runner.steps['name1']['tasks'])
            self.assertEqual({}, runner.steps['name1']['taskDependencies'])

            # Step 2 tasks and dependencies.
            self.assertEqual(
                {
                    'xxx': {123, 456},
                    'yyy': {234, 567},
                },
                runner.steps['name2']['tasks'])
            self.assertEqual({}, runner.steps['name2']['taskDependencies'])

            # Step 3 tasks and dependencies.
            self.assertEqual({}, runner.steps['name3']['tasks'])
            self.assertEqual(
                {
                    'aaa': {127, 450},
                    'bbb': {238, 560},
                    'xxx': {123, 456},
                    'yyy': {234, 567},
                },
                runner.steps['name3']['taskDependencies'])

            # Check that check_output was called 3 times, with the
            # expected arguments.
            mockMethod.assert_has_calls([
                call(['script1'], cwd='.', universal_newlines=True, env=ANY),
                call(['script2'], cwd='.', universal_newlines=True, env=ANY),
                call(['script3'], cwd='.', universal_newlines=True, env=ANY),
            ])

            # Check that the environment variables we set were correct
            # in all calls.
            env1 = mockMethod.mock_calls[0][2]['env']
            self.assertNotIn('SP_TASK_NAME', env1)
            self.assertNotIn('SP_DEPENDENCY_ARG', env1)

            env2 = mockMethod.mock_calls[1][2]['env']
            self.assertNotIn('SP_TASK_NAME', env2)
            self.assertNotIn('SP_DEPENDENCY_ARG', env2)

            env3 = mockMethod.mock_calls[2][2]['env']
            self.assertEqual('aaa bbb xxx yyy', env3['SP_TASK_NAMES'])
            self.assertEqual(
                ('--dependency='
                 'afterok:123,afterok:127,afterok:234,afterok:238,'
                 'afterok:450,afterok:456,afterok:560,afterok:567'),
                env3['SP_DEPENDENCY_ARG'])

    @patch('os.path.abspath')
    @patch('os.access')
    @patch('os.path.exists')
    def testCwdWithRelativeScriptPath(self, existsMock, accessMock,
                                      abspathMock):
        """
        If a step has a cwd set and its script is a relative path, the path of
        the executed script that is executed must be adjusted to be absolute.
        """

        abspathMock.return_value = '/fictional/path'

        with patch.object(subprocess, 'check_output') as mockMethod:
            mockMethod.return_value = 'hey\n'
            runner = SlurmPipeline(
                {
                    'steps': [
                        {
                            'cwd': '/tmp',
                            'name': 'name1',
                            'script': 'script1',
                        },
                    ],
                })
            runner.schedule()

            mockMethod.assert_has_calls([
                call(['/fictional/path'], cwd='/tmp', universal_newlines=True,
                     env=ANY),
            ])
