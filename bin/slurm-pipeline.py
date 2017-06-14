#!/usr/bin/env python

"""
Use the SlurmPipeline class to schedule the running of a pipeline job from its
specification, printing (to stdout) a detailed specification that includes job
ids. The status can be saved to a file and later given to
slurm-pipeline-status.py to monitor job progress.
"""

from __future__ import print_function

import sys
import os
import argparse
from tempfile import mkstemp

from slurm_pipeline import SlurmPipeline


parser = argparse.ArgumentParser(
    description='Schedule the execution of a pipeline on SLURM.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument(
    '--specification', '-s', metavar='specification.json', required=True,
    help=('The name of the file containing the pipeline specification, '
          'in JSON format.'))

parser.add_argument(
    '--force', '-f', action='store_true', default=False,
    help=('If specified, indicate to step scripts that they may overwrite '
          'pre-existing results files.'))

parser.add_argument(
    '--firstStep', metavar='step-name',
    help=('The name of the first specification step to execute. Earlier '
          'steps will actually be executed but they will have SP_SIMULATE=1 '
          'in their environment, allowing them to skip doing actual work '
          '(while still emitting task names without job numbers so that '
          'later steps receive the correct tasks to operate on).'))

parser.add_argument(
    '--lastStep', metavar='step-name',
    help=('The name of the last specification step to execute. See the '
          'help text for --first-step for how this affects the environment '
          'in which step scripts are executed.'))

parser.add_argument(
    '--skip', metavar='step-name', action='append',
    help='Name a step that should be skipped. May be repeated.')

parser.add_argument(
    '--sleep', type=float, default=0.0,
    help=('Specify the (floating point) number of seconds to sleep for '
          'between running step scripts. This can be used to allow a '
          'distributed file system to settle, so that jobs that have been '
          'scheduled can be seen when used as dependencies in later '
          'invocations of sbatch.'))

parser.add_argument(
    '--startAfter', nargs='*',
    help=('Give a list of SLURM job ids that must complete (in any state - '
          'either successfully or in error) before the initial step(s), '
          'i.e., those with no dependencies, in the current specification may '
          'begin.'))

parser.add_argument(
    '--nice', type=int,
    help=('A numeric nice (priority) value, in the range -10000 (highest '
          'priority) to 10000 (lowest priority). Note that only privileged '
          'users can specify a negative adjustment.'))

args, scriptArgs = parser.parse_known_args()

sp = SlurmPipeline(args.specification)

startAfter = list(map(int, args.startAfter)) if args.startAfter else None

status = sp.schedule(
    force=args.force, firstStep=args.firstStep, lastStep=args.lastStep,
    sleep=args.sleep, scriptArgs=scriptArgs, skip=args.skip,
    startAfter=startAfter, nice=args.nice)

statusAsJSON = sp.specificationToJSON(status)

print(statusAsJSON)

# If the user forgot to redirect output to a file, save it to a tempfile
# for them and let them know where it is. We do this because without the
# status they will have no way to examine the job with
# slurm-pipeline-status.py
if os.isatty(1):
    fd, filename = mkstemp(prefix='slurm-pipeline-status-', suffix='.json')
    print('WARNING: You did not save stdout to a file, so I have '
          'saved the specification status to %r for you.' % filename,
          file=sys.stderr)
    os.write(fd, statusAsJSON)
    os.write(fd, '\n')
