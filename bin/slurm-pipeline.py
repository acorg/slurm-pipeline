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

args, scriptArgs = parser.parse_known_args()

SlurmPipeline(args.specification, scriptArgs=scriptArgs).schedule()
