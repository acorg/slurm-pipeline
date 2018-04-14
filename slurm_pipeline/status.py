from __future__ import division

from .base import SlurmPipelineBase
from .error import SpecificationError
from .sacct import SAcct
from .utils import secondsToTime


class SlurmPipelineStatus(SlurmPipelineBase):
    """
    Read a pipeline execution status specification and supply methods for
    examining job ids, step status, etc.

    @param specification: Either a C{str} giving the name of a file containing
        a JSON execution specification, or a C{dict} holding a correctly
        formatted execution specification.
    @param fieldNames: A C{list} of C{str} job field names to obtain from
        sacct. If C{None}, a default set will be used (determined by sacct.py).
        See man sacct for the full list of possible field names.
    """
    def __init__(self, specification, fieldNames=None):
        SlurmPipelineBase.__init__(self, specification)
        self.sacct = SAcct(specification, fieldNames=fieldNames)

    @staticmethod
    def checkSpecification(specification):
        """
        Check an execution specification is syntactically as expected.

        @param specification: A C{dict} containing an execution specification.
        @raise SpecificationError: if there is anything wrong with the
            specification.
        """
        if 'scheduledAt' not in specification:
            raise SpecificationError(
                "The specification status has no top-level 'scheduledAt' key")

        SlurmPipelineBase.checkSpecification(specification)

    def finalJobs(self):
        """
        Get the job ids emitted by the final steps of a specification.

        @return: A C{set} of C{int} job ids.
        """
        steps = self.specification['steps']
        result = set()
        for stepName in self.finalSteps():
            for jobIds in steps[stepName]['tasks'].values():
                result.update(jobIds)
        return result

    def finishedJobs(self):
        """
        Get the ids of finished jobs emitted by a specification.

        @return: A C{set} of C{int} finished job ids.
        """
        finished = self.sacct.finished
        result = set()
        for step in self.specification['steps'].values():
            for jobIds in step['tasks']:
                result.update([jobid for jobid in jobIds if finished(jobid)])
        return result

    def unfinishedJobs(self):
        """
        Get the ids of unfinished jobs emitted by a specification.

        @return: A C{set} of C{int} unfinished job ids.
        """
        finished = self.sacct.finished
        result = set()
        for stepName in self.specification['steps']:
            jobIds = self.stepJobIds(stepName)
            result.update([jobid for jobid in jobIds if not finished(jobid)])
        return result

    def stepDependentJobIds(self, stepName):
        """
        Which dependent jobs must a step wait on?

        @param stepName: The C{str} name of a step.
        @return: A C{set} of C{int} job ids that a step is dependent on.
        """
        step = self.specification['steps'][stepName]
        jobIds = set()
        for taskJobIds in step['taskDependencies'].values():
            jobIds.update(taskJobIds)
        return jobIds

    def stepJobIds(self, stepName):
        """
        Which jobs did a step emit?

        @param stepName: The C{str} name of a step.
        @return: A C{set} of C{int} emitted job ids for the step.
        """
        jobIds = set()
        step = self.specification['steps'][stepName]
        for taskJobIds in step['tasks'].values():
            jobIds.update(taskJobIds)
        return jobIds

    def toStr(self):
        """
        Get a printable summary of a status specification, including job
        status.

        @raises SAcctError: If job status information cannot be read from
            sacct.
        @return: A C{str} representation of the status specification.
        """
        specification = self.specification
        # Use specification.get to get the username so we don't break if
        # we're run on a status file created before the username was being
        # stored (added in 1.1.14).
        result = [
            'Scheduled by: %s' % specification.get('user', 'UNKNOWN'),
            'Scheduled at: %s' % secondsToTime(specification['scheduledAt']),
            'Scheduling arguments:',
            '  First step: %s' % specification['firstStep'],
            '  Force: %s' % specification['force'],
            '  Last step: %s' % specification['lastStep'],
        ]
        append = result.append

        append('  Nice: %s' % specification.get('nice', '<None>'))

        if specification['scriptArgs']:
            append('  Script arguments: %s' %
                   ' '.join(specification['scriptArgs']))
        else:
            append('  Script arguments: <None>')

        if specification['skip']:
            append('  Skip: %s' % ', '.join(specification['skip']))
        else:
            append('  Skip: <None>')

        if specification['startAfter']:
            append('  Start after: %s' % ', '.join(
                specification['startAfter']))
        else:
            append('  Start after: <None>')

        steps = specification['steps']
        stepSummary = ['Step summary:']
        totalJobIdsEmitted = 0
        totalJobIdsFinished = 0
        for count, stepName in enumerate(steps, start=1):
            jobIdsEmitted = self.stepJobIds(stepName)
            jobIdsEmittedCount = len(jobIdsEmitted)
            jobIdsFinished = [jobId for jobId in jobIdsEmitted
                              if self.sacct.finished(jobId)]
            jobIdsFinishedCount = len(jobIdsFinished)
            totalJobIdsEmitted += jobIdsEmittedCount
            totalJobIdsFinished += jobIdsFinishedCount

            if jobIdsEmittedCount:
                percent = (0.0 if jobIdsEmittedCount == 0 else
                           jobIdsFinishedCount / jobIdsEmittedCount * 100.0)
                stepSummary.append(
                    '  %s: %d job%s emitted, %d (%.2f%%) finished' %
                    (stepName, jobIdsEmittedCount,
                     '' if jobIdsEmittedCount == 1 else 's',
                     jobIdsFinishedCount, percent))
            else:
                stepSummary.append('  %s: no jobs emitted' % stepName)

        percent = (100.0 if totalJobIdsEmitted == 0 else
                   totalJobIdsFinished / totalJobIdsEmitted * 100.0)

        append('%d job%s emitted in total, of which %d (%.2f%%) are finished' %
               (totalJobIdsEmitted, '' if totalJobIdsEmitted == 1 else 's',
                totalJobIdsFinished, percent))

        result.extend(stepSummary)

        for count, stepName in enumerate(steps, start=1):
            step = steps[stepName]
            append('Step %d: %s' % (count, stepName))

            try:
                dependencyCount = len(step['dependencies'])
            except KeyError:
                dependencyCount = 0

            if dependencyCount:
                append(
                    '  %d step %s: %s' %
                    (dependencyCount,
                     'dependency' if dependencyCount == 1 else 'dependencies',
                     ', '.join(step['dependencies'])))

                taskDependencyCount = len(step['taskDependencies'])

                jobIds = self.stepDependentJobIds(stepName)
                jobIdsCount = len(jobIds)
                jobIdsFinished = [jobId for jobId in jobIds
                                  if self.sacct.finished(jobId)]
                jobIdsFinishedCount = len(jobIdsFinished)

                append(
                    '    Dependent on %d task%s emitted by the dependent '
                    'step%s' %
                    (taskDependencyCount,
                     '' if taskDependencyCount == 1 else 's',
                     '' if dependencyCount == 1 else 's'))

                if jobIdsCount:
                    append(
                        '    %d job%s started by the dependent task%s, of '
                        'which %d (%.2f%%) are finished' %
                        (jobIdsCount, '' if jobIdsCount == 1 else 's',
                         '' if dependencyCount else 's',
                         jobIdsFinishedCount,
                         100.0 if jobIdsCount == 0 else
                         (jobIdsFinishedCount / jobIdsCount * 100.0)))
                elif taskDependencyCount:
                    append('    0 jobs started by the dependent task%s' % (
                        '' if taskDependencyCount == 1 else 's'))

                if taskDependencyCount:
                    append('    Dependent tasks:')
                    for taskName in sorted(step['taskDependencies']):
                        jobIds = step['taskDependencies'][taskName]
                        append('      %s' % taskName)
                        for jobId in sorted(jobIds):
                            append('        Job %d: %s' %
                                   (jobId, self.sacct.summarize(jobId)))
            else:
                assert len(step['taskDependencies']) == 0
                append('  No dependencies.')

            # Tasks launched by this step.
            taskCount = len(step['tasks'])

            if taskCount:
                append(
                    '  %d task%s emitted by this step' %
                    (taskCount, '' if taskCount == 1 else 's'))

                jobIds = self.stepJobIds(stepName)
                jobIdsCount = len(jobIds)
                jobIdsFinishedCount = [jobId for jobId in jobIds
                                       if self.sacct.finished(jobId)]
                jobIdsFinishedCount = len(jobIdsFinishedCount)

                if jobIdsCount:
                    append(
                        '    %d job%s started by %s, of which %d (%.2f%%) '
                        'are finished' %
                        (jobIdsCount, '' if jobIdsCount == 1 else 's',
                         'this task' if taskCount else 'these tasks',
                         jobIdsFinishedCount,
                         100.0 if jobIdsCount == 0 else
                         jobIdsFinishedCount / jobIdsCount * 100.0))
                else:
                    append('    0 jobs started by %s' %
                           ('this task' if taskCount == 1 else 'these tasks'))

                if taskCount:
                    append('    Tasks:')
                    for taskName in sorted(step['tasks']):
                        jobIds = step['tasks'][taskName]
                        append('      %s' % taskName)
                        for jobId in sorted(jobIds):
                            append('        Job %d: %s' %
                                   (jobId, self.sacct.summarize(jobId)))
            else:
                assert len(step['tasks']) == 0
                append('  No tasks emitted by this step')

            result.extend([
                '  Working directory: %s' % step.get('cwd', '.'),
                '  Scheduled at: %s' % secondsToTime(step['scheduledAt']),
                '  Script: %s' % step['script'],
                '  Simulate: %s' % step['simulate'],
                '  Skip: %s' % step['skip'],
            ])

        return '\n'.join(result)
