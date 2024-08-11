#!/usr/bin/env python

"""
Use the SlurmPipeline class to schedule the running of a pipeline job from its
specification, printing (to stdout or to the file named by --output) a detailed
specification that includes job ids. The printed status can be saved to a file
and later given to slurm-pipeline-status.py to monitor job progress.
"""

import sys
import os
import argparse
from itertools import chain

from slurm_pipeline import SlurmPipeline


parser = argparse.ArgumentParser(
    description="Schedule the execution of a pipeline on SLURM.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument(
    "--specification",
    "-s",
    metavar="specification.json",
    required=True,
    help=(
        "The name of the file containing the pipeline specification, " "in JSON format."
    ),
)

parser.add_argument(
    "--force",
    "-f",
    action="store_true",
    help=(
        "If specified, indicate to step scripts that they may overwrite "
        "pre-existing results files."
    ),
)

parser.add_argument(
    "--firstStep",
    metavar="step-name",
    help=(
        "The name of the first pipeline step to execute. Earlier "
        "steps will actually be executed but they will have SP_SIMULATE=1 "
        "in their environment, allowing them to skip doing actual work "
        "(while still emitting task names without job numbers so that "
        "later steps receive the correct tasks to operate on)."
    ),
)

parser.add_argument(
    "--lastStep",
    metavar="step-name",
    help=(
        "The name of the last pipeline step to execute. See the "
        "help text for --first-step for how this affects the environment "
        "in which step scripts are executed."
    ),
)

parser.add_argument(
    "--skip",
    metavar="step-name",
    action="append",
    help="Name a pipeline step that should be skipped. May be repeated.",
)

parser.add_argument(
    "--sleep",
    type=float,
    default=0.0,
    help=(
        "Specify the (floating point) number of seconds to sleep for "
        "between running step scripts. This can be used to allow a "
        "distributed file system to settle, so that jobs that have been "
        "scheduled can be seen when used as dependencies in later "
        "invocations of sbatch."
    ),
)

parser.add_argument(
    "--startAfter",
    nargs="*",
    help=(
        "Give a list of SLURM job ids that must complete (in any state - "
        "either successfully or in error) before the initial step(s), "
        "i.e., those with no dependencies, in the current pipeline may "
        "begin."
    ),
)

parser.add_argument(
    "--nice",
    type=int,
    help=(
        "A numeric nice (priority) value, in the range -10000 (highest "
        "priority) to 10000 (lowest priority). Note that only privileged "
        "users can specify a negative adjustment."
    ),
)

parser.add_argument(
    "--output",
    "-o",
    default=sys.stdout,
    type=argparse.FileType("w"),
    nargs="?",
    help=(
        "The name of the file to write the pipeline status to (in JSON "
        "format). Default is standard output."
    ),
)

parser.add_argument(
    "--printOutput",
    action="store_true",
    help="Print the output of each pipeline step that is run.",
)

parser.add_argument(
    "--scriptArgs",
    nargs="+",
    action="append",
    help=(
        "Specify arguments to be passed to the initial pipeline step "
        "scripts. Initial steps are those that have no dependencies "
        "in the JSON specification."
    ),
)

args = parser.parse_args()

sp = SlurmPipeline(args.specification)

startAfter = list(map(int, args.startAfter)) if args.startAfter else None

if args.scriptArgs:
    # Flatten lists of lists that we get from using both nargs='+' and
    # action='append'. We use both because it allows people to use
    # --scriptArgs on the command line either via "--scriptArgs arg1
    # --scriptArgs arg2 or "--scriptArgs arg1 arg2", or a combination of
    # these. That way it's not necessary to remember which way you're
    # supposed to use it and you can't be hit by the subtle problem
    # encountered in https://github.com/acorg/dark-matter/issues/453
    scriptArgs = list(chain.from_iterable(args.scriptArgs))
else:
    scriptArgs = None

status = sp.schedule(
    force=args.force,
    firstStep=args.firstStep,
    lastStep=args.lastStep,
    sleep=args.sleep,
    scriptArgs=scriptArgs,
    skip=args.skip,
    startAfter=startAfter,
    nice=args.nice,
    printOutput=args.printOutput,
)

statusAsJSON = sp.specificationToJSON(status)

print(statusAsJSON, file=args.output)


# If the user did not redirect output to a file or specify an output file,
# save the status to a tempfile for them and let them know where it is. We
# do this because without the status they will have no way to examine the
# job with slurm-pipeline-status.py
if os.isatty(1) and args.output is sys.stdout:
    from tempfile import mkstemp

    fd, filename = mkstemp(prefix="slurm-pipeline-status-", suffix=".json")
    print(
        "WARNING: You did not save stdout to a file, so I have "
        "saved the specification status to %r for you." % filename,
        file=sys.stderr,
    )
    os.write(fd, statusAsJSON.encode("utf-8") + b"\n")
