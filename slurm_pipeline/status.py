from __future__ import division

from time import gmtime, strftime

from .base import SlurmPipelineBase
from .error import SpecificationError
from .squeue import SQueue


def secondsToTime(seconds):
    """
    Convert a number of seconds to a time string.

    @param seconds: A C{float} number of seconds since the epoch, in UTC.
    @return: A C{str} giving the date/time corresponding to C{seconds}.
    """
    return strftime('%Y-%m-%d %H:%M:%S', gmtime(seconds))


class SlurmPipelineStatus(SlurmPipelineBase):
    """
    Read a pipeline execution status specification and supply methods for
    examining job ids, step status, etc.
    """

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

    def finalJobs(self, specification):
        """
        Get the job ids emitted by the final steps of a specification.

        @param specification: A C{dict} containing an execution specification.
        @return: A C{set} of C{int} job ids.
        """
        steps = specification['steps']
        result = set()
        for stepName in self.finalSteps(specification):
            for jobIds in steps[stepName]['tasks'].values():
                result.update(jobIds)
        return result

    def unfinishedJobs(self, specification, squeueArgs=None):
        """
        Get the ids of unfinished jobs emitted by a specification.

        @param specification: A C{dict} containing an execution specification.
        @param squeueArgs: A C{list} of C{str} arguments to pass to squeue
            (including the 'squeue' command itself). If C{None}, the user's
            login name will be appended to squeue -u.
        @return: A C{set} of C{int} unifinished job ids.
        """
        squeue = SQueue(squeueArgs)
        result = set()
        for stepName in specification['steps']:
            jobIds, jobIdsFinished = self.stepJobIdSummary(stepName, squeue)
            result.update(jobIds - jobIdsFinished)
        return result

    def stepDependentJobIdSummary(self, stepName, squeue):
        """
        Which dependent jobs must a step wait on and which are finished?

        @param stepName: The C{str} name of a step.
        @param squeue: An C{SQueue} instance.
        @return: A C{tuple} of two C{set}s, holding the emitted and finished
            C{int} job ids.
        """
        step = self.specification['steps'][stepName]

        # Tasks depended on by this step.
        taskCount = len(step['taskDependencies'])

        jobIdsCompleted = set()
        jobIds = set()
        if taskCount:
            for taskJobIds in step['taskDependencies'].values():
                jobIds.update(taskJobIds)
            for jobId in jobIds:
                if squeue.finished(jobId):
                    jobIdsCompleted.add(jobId)
        return jobIds, jobIdsCompleted

    def stepJobIdSummary(self, stepName, squeue):
        """
        Which jobs did a step emit and which are finished?

        @param stepName: The C{str} name of a step.
        @param squeue: An C{SQueue} instance.
        @return: A C{tuple} of two C{set}s, holding the emitted and finished
            C{int} job ids.
        """
        step = self.specification['steps'][stepName]

        # Tasks launched by this step.
        taskCount = len(step['tasks'])

        jobIdsCompleted = set()
        jobIds = set()
        if taskCount:
            for taskJobIds in step['tasks'].values():
                jobIds.update(taskJobIds)
            for jobId in jobIds:
                if squeue.finished(jobId):
                    jobIdsCompleted.add(jobId)
        return jobIds, jobIdsCompleted

    def toStr(self, squeueArgs=None):
        """
        Get a printable summary of a status specification, including job
        status.

        @param squeueArgs: A C{list} of C{str} arguments to pass to squeue
            (including the 'squeue' command itself). If C{None}, the user's
            login name will be appended to squeue -u.
        @raises SQueueError: If job status information cannot be read from
            squeue.
        @return: A C{str} representation of the status specification.
        """
        specification = self.specification
        result = [
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

        squeue = SQueue(squeueArgs)
        steps = specification['steps']

        stepSummary = ['Step summary:']
        totalJobIdsEmitted = 0
        totalJobIdsFinished = 0
        for count, stepName in enumerate(steps, start=1):
            jobIdsEmitted, jobIdsFinished = map(
                len, self.stepJobIdSummary(stepName, squeue))
            totalJobIdsEmitted += jobIdsEmitted
            totalJobIdsFinished += jobIdsFinished

            percent = (0.0 if jobIdsEmitted == 0 else
                       jobIdsFinished / jobIdsEmitted * 100.0)
            if jobIdsEmitted:
                stepSummary.append(
                    '  %s: %d job%s emitted, %d (%.2f%%) finished' %
                    (stepName, jobIdsEmitted,
                     '' if jobIdsEmitted == 1 else 's', jobIdsFinished,
                     percent))
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

                jobIds, jobIdsFinished = self.stepDependentJobIdSummary(
                    stepName, squeue)

                jobIdCount = len(jobIds)
                jobIdCompletedCount = len(jobIdsFinished)

                append(
                    '    Dependent on %d task%s emitted by the dependent '
                    'step%s' %
                    (taskDependencyCount,
                     '' if taskDependencyCount == 1 else 's',
                     '' if dependencyCount == 1 else 's'))

                if jobIdCount:
                    append(
                        '    %d job%s started by the dependent task%s, of '
                        'which %d (%.2f%%) are finished' %
                        (jobIdCount, '' if jobIdCount == 1 else 's',
                         '' if dependencyCount else 's',
                         jobIdCompletedCount,
                         100.0 if jobIdCount == 0 else
                         (jobIdCompletedCount / jobIdCount * 100.0)))
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
                                   (jobId, squeue.summarize(jobId)))
            else:
                assert len(step['taskDependencies']) == 0
                append('  No dependencies.')

            # Tasks launched by this step.
            taskCount = len(step['tasks'])

            if taskCount:
                append(
                    '  %d task%s emitted by this step' %
                    (taskCount, '' if taskCount == 1 else 's'))

                jobIds, jobIdsCompleted = self.stepJobIdSummary(stepName,
                                                                squeue)

                jobIdCount = len(jobIds)
                jobIdCompletedCount = len(jobIdsCompleted)

                if jobIdCount:
                    append(
                        '    %d job%s started by %s, of which %d (%.2f%%) '
                        'are finished' %
                        (jobIdCount, '' if jobIdCount == 1 else 's',
                         'this task' if taskCount else 'these tasks',
                         jobIdCompletedCount,
                         100.0 if jobIdCount == 0 else
                         jobIdCompletedCount / jobIdCount * 100.0))
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
                                   (jobId, squeue.summarize(jobId)))
            else:
                assert len(step['tasks']) == 0
                append('  No tasks emitted by this step')

            result.extend([
                '  Working directory: %s' % step['cwd'],
                '  Scheduled at: %s' % secondsToTime(step['scheduledAt']),
                '  Script: %s' % step['script'],
                '  Simulate: %s' % step['simulate'],
                '  Skip: %s' % step['skip'],
            ])

        return '\n'.join(result)
