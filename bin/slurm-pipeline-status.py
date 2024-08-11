#!/usr/bin/env python

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
    description=(
        "Print information about the execution status of a scheduled SLURM pipeline."
    )
)

parser.add_argument(
    "--specification",
    "-s",
    metavar="specification.json",
    required=True,
    help="The name of the file containing the pipeline status, in JSON format.",
)

parser.add_argument(
    "--fieldNames",
    metavar="FIELD1,FIELD2,FIELD3",
    help=(
        "A comma-separated list of SLURM job field names to obtain from "
        "sacct (using its --format option) for listing job status "
        "information. See man sacct for the full list of possible field "
        "names. If not given, defaults to the value of "
        "SP_STATUS_FIELD_NAMES in your environment (if set), otherwise %s."
        % SAcct.DEFAULT_FIELD_NAMES
    ),
)

# Only one of --printUnfinished, --printFinished, or --printFinal can be given.
group = parser.add_mutually_exclusive_group()

group.add_argument(
    "--printUnfinished",
    action="store_true",
    help=(
        "Print a list of job ids that have not yet finished. This can be "
        "used to cancel a job, e.g., with: "
        "%s --printUnfinished --spec status.json | xargs scancel" % sys.argv[0]
    ),
)

group.add_argument(
    "--printFinished",
    action="store_true",
    help="Print a list of job ids that are finished.",
)

group.add_argument(
    "--printFinal",
    action="store_true",
    help=(
        "Print a list of job ids issued by the final steps of a "
        "pipeline. This can be used with the --startAfter option in a "
        "subsequent call to slurm-pipeline.py to have it arrange that a "
        "later pipeline only run after the given pipeline is "
        "completely finished e.g., with: slurm-pipeline.py --spec spec.json "
        "--startAfter $(%s --spec status.json --printFinal)" % sys.argv[0]
    ),
)

args = parser.parse_args()

status = SlurmPipelineStatus(args.specification, fieldNames=args.fieldNames)

if args.printFinal:
    jobsFunc = status.finalJobs
elif args.printFinished:
    jobsFunc = status.finishedJobs
elif args.printUnfinished:
    jobsFunc = status.unfinishedJobs
else:
    jobsFunc = None

if jobsFunc:
    jobs = jobsFunc()
    if jobs:
        print("\n".join(map(str, jobs)))
else:
    print(status.toStr())
