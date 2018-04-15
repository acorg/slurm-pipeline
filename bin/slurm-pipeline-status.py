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
from slurm_pipeline.sacct import SAcct


parser = argparse.ArgumentParser(
    description=('Print information about the execution status of a '
                 'scheduled SLURM pipeline.'),
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument(
    '--specification', '-s', metavar='specification.json', required=True,
    help=('The name of the file containing the pipeline status, '
          'in JSON format.'))

parser.add_argument(
    '--fieldNames', default=SAcct.DEFAULT_FIELD_NAMES,
    help=('A comma-separated list of SLURM job field names to obtain from '
          'sacct for listing job status information. See man sacct for the '
          'full list of possible field names.'))

# Only one of --printUnfinished, --printFinished, or --printFinal can be given.
group = parser.add_mutually_exclusive_group()

group.add_argument(
    '--printUnfinished', default=False, action='store_true',
    help=('Print a list of job ids that have not yet finished. This can be '
          'used to cancel a job, e.g., with: '
          '%s --printUnfinished -s status.json | xargs scancel' % sys.argv[0]))

group.add_argument(
    '--printFinished', default=False, action='store_true',
    help='Print a list of job ids that are finished.')

group.add_argument(
    '--printFinal', default=False, action='store_true',
    help=('Print a list of job ids issued by the final steps of a '
          'specification. This can be used with the --startAfter option in a '
          'subsequent call to slurm-pipeline.py to have it arrange that a '
          'different specification only run after the given specification is '
          'completely finished.'))

args = parser.parse_args()

status = SlurmPipelineStatus(args.specification, fieldNames=args.fieldNames)

if args.printFinal:
    print('\n'.join(map(str, status.finalJobs())))

elif args.printFinished:
    print('\n'.join(map(str, status.finishedJobs())))

elif args.printUnfinished:
    print('\n'.join(map(str, status.unfinishedJobs())))

else:
    print(status.toStr())
