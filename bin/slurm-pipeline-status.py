#!/usr/bin/env python

from __future__ import print_function
import sys

"""
Uses the SlurmPipelineStatus class to print information about a
specification that has already been scheduled, given an in-progress job
specification status, as originally printed by slurm-pipeline.py.
"""

import argparse

from slurm_pipeline import SlurmPipelineStatus


parser = argparse.ArgumentParser(
    description=('Print information about the execution status of a '
                 'scheduled SLURM pipeline.'),
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument(
    '--specification', '-s', metavar='specification.json', required=True,
    help=('The name of the file containing the pipeline status, '
          'in JSON format.'))

parser.add_argument(
    '--squeueArgs', nargs='*', default=None,
    help=('A list of arguments to pass to squeue (including the squeue '
          "command itself). If not specified, the user's login name will "
          'be appended to squeue -u.'))

parser.add_argument(
    '--printUnfinished', default=False, action='store_true',
    help=('If specified, print a list of job ids that have not yet finished. '
          'This can easily be used to cancel a job, via e.g., '
          '%s --printUnfinished -s spec.json | xargs scancel' % sys.argv[0]))

parser.add_argument(
    '--printFinal', default=False, action='store_true',
    help=('If specified, print a list of job ids issued by the final steps '
          'of a specification. This can be used with the --startAfter option '
          'to slurm-pipeline.py to make it schedule a different specification '
          'to run only after the given specification finishes.'))

args = parser.parse_args()

status = SlurmPipelineStatus(args.specification)

if args.printFinal:
    print('\n'.join(map(str, status.finalJobs())))
elif args.printUnfinished:
    print('\n'.join(map(str, status.unfinishedJobs(args.squeueArgs))))
else:
    print(status.toStr(args.squeueArgs))
