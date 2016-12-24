#!/usr/bin/env python

from __future__ import print_function

"""
Use the SlurmPipelineStatus class to print a status report of a job
that has already been scheduled, given an in-progress job specification
status, as printed by slurm-pipeline.py.
"""

import argparse

from slurm_pipeline import SlurmPipelineStatus


parser = argparse.ArgumentParser(
    description=('Print the status of the execution of a scheduled SLURM '
                 'pipeline.'),
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument(
    '--specification', '-s', metavar='specification.json', required=True,
    help=('The name of the file containing the pipeline status, '
          'in JSON format.'))

parser.add_argument(
    '--squeueArgs', nargs='*', default=None,
    help=("A list of arguments to pass to squeue (including the squeue "
          "command itself). If not specified, the user's login name will "
          "be appended to squeue -u."))

args = parser.parse_args()

status = SlurmPipelineStatus(args.specification)

print(status.toStr(args.squeueArgs))
