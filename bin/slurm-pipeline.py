#!/usr/bin/env python

import argparse

from slurm_pipeline import SlurmPipeline


parser = argparse.ArgumentParser(
    description='Schedule the execution of a pipeline on SLURM',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument(
    '--specification', '-s', metavar='specification.json',
    help=('The name of the file containing the pipeline specification, '
          'in JSON format'))

parser.add_argument(
    '--force', '-f', action='store_true', default=False,
    help=('If specified, indicate to step scripts that they may overwrite '
          'pre-existing results files.'))

parser.add_argument(
    '--firstStep', metavar='step-name', default=None,
    help=('The name of the first specification step to execute. Earlier '
          'steps will actually be executed but they will have SP_SIMULATE=1 '
          'in their environment, allowing them to skip doing actual work '
          '(while still emitting task names without job numbers so that '
          'later steps receive the correct tasks to operate on).'))

parser.add_argument(
    '--lastStep', metavar='step-name', default=None,
    help=('The name of the last specification step to execute. See the '
          'help text for --first-step for how this affects the environment '
          'in which step scripts are executed.'))

parser.add_argument(
    '--sleep', type=float, default=0.0,
    help=('Specify the (floating point) number of seconds to sleep for '
          'between running step scripts. This can be used to allow a '
          'distributed file system to settle, so that jobs that have been '
          'scheduled can be seen when used as dependencies in later '
          'invocations of sbatch.'))

args, scriptArgs = parser.parse_known_args()

sp = SlurmPipeline(args.specification, force=args.force,
                   firstStep=args.firstStep, lastStep=args.lastStep,
                   sleep=args.sleep, scriptArgs=scriptArgs)
sp.schedule()

print(sp.toJSON())
