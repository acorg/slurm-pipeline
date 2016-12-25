from unittest import TestCase
from six.moves import builtins
from six import assertRaisesRegex, PY3
from json import dumps
import platform

from slurm_pipeline.base import SlurmPipelineBase
from slurm_pipeline.error import SpecificationError

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from .mocking import mockOpen

PYPY = platform.python_implementation() == 'PyPy'


class TestSlurmPipelineBase(TestCase):
    """
    Tests for the slurm_pipeline.pipeline.SlurmPipelineBase class.
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
            elif PYPY:
                # The error message in the exception has a NUL in it.
                error = ("^No JSON object could be decoded: unexpected "
                         "'\\000' at char 0$")
            else:
                error = '^No JSON object could be decoded$'
            assertRaisesRegex(self, ValueError, error, SlurmPipelineBase,
                              'file')

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
            elif PYPY:
                # The error message in the exception has a NUL in it.
                error = ("^No JSON object could be decoded: unexpected "
                         "'\\000' at char 0$")
            else:
                error = '^Expecting object: line 1 column 1 \(char 0\)$'
            assertRaisesRegex(self, ValueError, error, SlurmPipelineBase,
                              'file')

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
            assertRaisesRegex(self, SpecificationError, error,
                              SlurmPipelineBase, 'file')

    def testList(self):
        """
        If the specification is passed a list directly instead of a dict, a
        SpecificationError must be raised.
        """
        error = ('^The specification must be a dict \(i\.e\., a JSON '
                 'object when loaded from a file\)$')
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
                          [])

    def testNoSteps(self):
        """
        If the specification dict does not contain a 'steps' key, a
        SpecificationError must be raised.
        """
        error = "^The specification must have a top-level 'steps' key$"
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
                          {})

    def testStepsMustBeAList(self):
        """
        If the specification dict does not contain a 'steps' key whose value
        is a list, a SpecificationError must be raised.
        """
        error = "^The 'steps' key must be a list$"
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
                          {'steps': None})

    def testNonDictionaryStep(self):
        """
        If the specification steps contains a step that is not a dict, a
        SpecificationError must be raised.
        """
        error = '^Step 1 is not a dictionary$'
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
                          {
                              'steps': [
                                  None,
                              ]
                          })

    def testStepWithoutScript(self):
        """
        If the specification steps contains a step that does not have a
        'script' key, a SpecificationError must be raised.
        """
        error = "^Step 2 \('name2'\) does not have a 'script' key$"
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
                          {
                              'steps': [
                                  {
                                      'name': 'name1',
                                      'script': 'script',
                                  },
                                  {
                                      'name': 'name2',
                                  },
                              ]
                          })

    def testNonStringScript(self):
        """
        If a step has a 'script' key that is not a string, a SpecificationError
        must be raised.
        """
        error = "^The 'script' key in step 1 \('name'\) is not a string$"
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
                          {
                              'steps': [
                                  {
                                      'name': 'name',
                                      'script': None,
                                  },
                              ]
                          })

    def testStepWithoutName(self):
        """
        If the specification steps contains a step that does not have a
        'name' key, a SpecificationError must be raised.
        """
        error = "^Step 1 does not have a 'name' key$"
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
                          {
                              'steps': [
                                  {
                                      'script': 'script',
                                  },
                              ]
                          })

    def testNonStringName(self):
        """
        If a step has a 'name' key that is not a string, a SpecificationError
        must be raised.
        """
        error = "^The 'name' key in step 1 is not a string$"
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
                          {
                              'steps': [
                                  {
                                      'name': None,
                                      'script': 'script',
                                  },
                              ]
                          })

    def testDuplicateName(self):
        """
        If two steps have the same name, a SpecificationError must be raised.
        specification.
        """
        error = ("^The name 'name' of step 2 was already used in an "
                 "earlier step$")
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
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

    def testNonListDependencies(self):
        """
        If a step has a 'dependencies' key that is not a list, a
        SpecificationError must be raised.
        """
        error = "^Step 1 \('name'\) has a non-list 'dependencies' key$"
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
                          {
                              'steps': [
                                  {
                                      'dependencies': None,
                                      'name': 'name',
                                      'script': 'script',
                                  },
                              ]
                          })

    def testNonExistentDependency(self):
        """
        If a step has a 'dependencies' key that mentions an unknown step,
        a SpecificationError must be raised.
        """
        error = ("^Step 2 \('name2'\) depends on a non-existent \(or "
                 "not-yet-defined\) step: 'unknown'$")
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
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

    def testStepDependentOnItself(self):
        """
        If a step has a 'dependencies' key that mentions that same step,
        a SpecificationError must be raised.
        """
        error = ("^Step 1 \('name'\) depends itself$")
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
                          {
                              'steps': [
                                  {
                                      'dependencies': ['name'],
                                      'name': 'name',
                                      'script': 'script',
                                  },
                              ]
                          })

    def testNonYetDefinedDependency(self):
        """
        If a step has a 'dependencies' key that mentions a step that exists
        but that has not yet been defined in the specification steps, a
        SpecificationError must be raised.
        """
        error = ("^Step 1 \('name1'\) depends on a non-existent \(or "
                 "not-yet-defined\) step: 'name2'$")
        assertRaisesRegex(self, SpecificationError, error, SlurmPipelineBase,
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

    def testSpecificationIsStored(self):
        """
        If well-formed JSON is passed, it must be read and stored as the
        specification. The 'steps' list must be converted to a dict.
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
            spb = SlurmPipelineBase('file')
            expected = {
                'steps': {
                    'name1':
                        {
                            'name': 'name1',
                            'script': 'script1',
                        },
                    'name2':
                        {
                            'name': 'name2',
                            'script': 'script2',
                        },
                },
            }
            self.assertEqual(expected, spb.specification)

    def testFinalStepsWithOneStep(self):
        """
        If a specification has only one step, finalSteps must return that step.
        """
        specification = {
            'steps': [
                {
                    'name': 'name1',
                    'script': 'script1',
                },
            ],
        }
        spb = SlurmPipelineBase(specification)
        self.assertEqual(set(('name1',)), spb.finalSteps(spb.specification))

    def testFinalStepsWithTwoSteps(self):
        """
        If a specification has two steps with no dependencies, finalSteps must
        return both steps.
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
        spb = SlurmPipelineBase(specification)
        self.assertEqual(set(('name1', 'name2')),
                         spb.finalSteps(spb.specification))

    def testFinalStepsWithTwoStepsOneDependency(self):
        """
        If a specification has two steps and the second depends on the first,
        finalSteps must return just the second.
        """
        specification = {
            'steps': [
                {
                    'name': 'name1',
                    'script': 'script1',
                },
                {
                    'dependencies': ['name1'],
                    'name': 'name2',
                    'script': 'script2',
                },
            ],
        }
        spb = SlurmPipelineBase(specification)
        self.assertEqual(set(('name2',)), spb.finalSteps(spb.specification))

    def testFinalStepsWithFiveSteps(self):
        """
        If a specification has 5 steps and two of them are not depended on
        finalSteps must return those two.
        """
        specification = {
            'steps': [
                {
                    'name': 'name1',
                    'script': 'script1',
                },
                {
                    'dependencies': ['name1'],
                    'name': 'name2',
                    'script': 'script2',
                },
                {
                    'name': 'name3',
                    'script': 'script3',
                },
                {
                    'name': 'name4',
                    'script': 'script4',
                },
                {
                    'dependencies': ['name3', 'name4'],
                    'name': 'name5',
                    'script': 'script5',
                },
            ],
        }
        spb = SlurmPipelineBase(specification)
        self.assertEqual(set(('name2', 'name5')),
                         spb.finalSteps(spb.specification))

    def testFinalStepsWithSixSteps(self):
        """
        If a specification has 6 steps and one of them is not depended on
        finalSteps must return that one.
        """
        specification = {
            'steps': [
                {
                    'name': 'name1',
                    'script': 'script1',
                },
                {
                    'dependencies': ['name1'],
                    'name': 'name2',
                    'script': 'script2',
                },
                {
                    'name': 'name3',
                    'script': 'script3',
                },
                {
                    'name': 'name4',
                    'script': 'script4',
                },
                {
                    'dependencies': ['name3', 'name4'],
                    'name': 'name5',
                    'script': 'script5',
                },
                {
                    'dependencies': ['name2', 'name5'],
                    'name': 'name6',
                    'script': 'script6',
                },
            ],
        }
        spb = SlurmPipelineBase(specification)
        self.assertEqual(set(('name6',)), spb.finalSteps(spb.specification))
