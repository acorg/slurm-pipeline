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

args, scriptArgs = parser.parse_known_args()

sp = SlurmPipeline(args.specification, args.force, scriptArgs=scriptArgs)
sp.schedule()

print(sp.toJSON())
