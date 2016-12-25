#!/usr/bin/env python

"""
Use the SlurmPipeline class to schedule the running of a pipeline job from its
specification, printing (to stdout) a detailed specification that includes job
ids. The status can be saved to a file and later given to
slurm-pipeline-status.py to monitor job progress.
"""

import argparse

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

args, scriptArgs = parser.parse_known_args()

sp = SlurmPipeline(args.specification, status=False)

startAfter = list(map(int, args.startAfter)) if args.startAfter else None

status = sp.schedule(
    force=args.force, firstStep=args.firstStep, lastStep=args.lastStep,
    sleep=args.sleep, scriptArgs=scriptArgs, skip=args.skip,
    startAfter=startAfter)

print(sp.specificationToJSON(status))
