#!/usr/bin/env python

import sys
import argparse
import subprocess
import os
import bz2
from os import environ
from os.path import exists, join
from tempfile import mkdtemp
from time import time, ctime
from json import dumps
from typing import Optional, Iterator, Iterable, Union

CONDITION_NAMES = {
    "after": "finally",
    "afterok": "then",
    "afternotok": "else",
    None: "initial",
}


def makeParser() -> argparse.ArgumentParser:
    """
    Make an argparse parser for the command line.

    @return: An C{argparse} parser.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Use sbatch to run a command on data read from standard "
            "input, optionally split into multiple jobs."
        ),
    )

    parser.add_argument(
        "command",
        metavar="COMMAND",
        nargs="+",
        help=(
            "An executable command to schedule for running via sbatch, "
            "passing it lines of standard input. If the command contains "
            "shell metacharacters it will need to be quoted. If "
            "--linesPerJob is given, standard input will be broken into "
            "groups of lines and each group will be passed to a separate "
            "invocation of the command. All files related to the running "
            "of the command (input, output, error, SLURM output) will be "
            "created in the --dir directory."
        ),
    )

    parser.add_argument(
        "--linesPerJob",
        "-N",
        type=int,
        default=0,
        metavar="N",
        help=(
            "The number of lines of standard input to give to each "
            "invocation of the command. The final invocation will likely "
            "receive fewer lines of input when the original standard input "
            "empties. If zero or not specified, all lines of standard input "
            "are passed to the command."
        ),
    )

    parser.add_argument(
        "--dir",
        metavar="DIR",
        help=(
            "The directory where command input (if --inline is not used), "
            "output, and error files will be created, along with scripts to "
            "run sbatch (if --dryRun is used) scripts. The directory will "
            "be created if it does not already exist, and if this argument "
            "is omitted the path to a newly-created directory will be "
            "printed to standard error."
        ),
    )

    parser.add_argument(
        "--prefix",
        default="",
        help=(
            "The prefix to use for input, output, error, and sbatch files "
            "written to --dir."
        ),
    )

    parser.add_argument(
        "--afterok",
        nargs="*",
        help=(
            "An optional list of SLURM job ids that must all finish "
            "successully before running the command. If the given jobs do "
            "not all finish successully, the SLURM job(s) to run the main "
            "command will not execute (but any --else and --finally "
            "commands will run)."
        ),
    )

    parser.add_argument(
        "--mem",
        default="8G",
        help=(
            "The amount of memory to request from sbatch for each run of "
            "the command."
        ),
    )

    parser.add_argument(
        "--cpus",
        default=1,
        metavar="N",
        help=(
            "The number of cpus per task to ask sbatch for via the "
            "--cpus-per-task argument."
        ),
    )

    parser.add_argument(
        "--digits",
        default=5,
        metavar="N",
        help=(
            "The number of digits to use in (zero-padded) file names "
            "written to --dir.  Only used if --noArray is given."
        ),
    )

    parser.add_argument(
        "--timePerJob",
        default="10:00",
        help=(
            "The amount of time to request from SLURM for each sbatch job. "
            'From man sbatch: acceptable time formats include  "minutes", '
            '"minutes:seconds", "hours:minutes:seconds", "days-hours", '
            '"days-hours:minutes", and "days-hours:minutes:seconds".'
        ),
    )

    parser.add_argument(
        "--partition", default="medium", help="The SLURM partition to use."
    )

    parser.add_argument(
        "--then",
        action="append",
        metavar="COMMAND",
        help=(
            "Specify a command to run after all SLURM jobs are finished "
            "(assuming they all finish without error). May be repeated, in "
            "which case the commands are run (by SLURM) in the order "
            "given on the command line once the previous command has "
            "finished."
        ),
    )

    parser.add_argument(
        "--else",
        action="append",
        dest="else_",
        metavar="COMMAND",
        help=(
            "Specify a command to run if any of the SLURM jobs finishes "
            "with an error (i.e., exits with a non-zero status). May be "
            "repeated, in which case the commands are all run (by "
            "SLURM) at once, not sequentially as with --then. I.e., "
            "following the failure of any job, SLURM can immediately "
            "schedule all --else commands."
        ),
    )

    parser.add_argument(
        "--finally",
        action="append",
        dest="finally_",
        metavar="COMMAND",
        help=(
            "Specify a command to run when all SLURM jobs (the original "
            "command and any --then or --else jobs) have finished, "
            "regardless of their exit status. May be repeated, in which "
            "case the commands are all run (by SLURM) at once, not "
            "sequentially as with --then. I.e., following the termination "
            "of all jobs, SLURM can immediately schedule all --finally "
            "commands."
        ),
    )

    parser.add_argument(
        "--jobNamePrefix",
        "-J",
        default="",
        metavar="PREFIX",
        help=(
            'The job name prefix. This will have a stage ("initial", '
            '"then", "else", or "finally") and a numeric count appended for '
            "each job submitted to SLURM."
        ),
    )

    parser.add_argument(
        "--dryRun",
        "-n",
        action="store_true",
        help="Do not actually do anything, just print what would be done.",
    )

    parser.add_argument(
        "--noArray",
        action="store_false",
        dest="array",
        help="Do not use a SLURM job array.",
    )

    parser.add_argument(
        "--arrayMax",
        type=int,
        metavar="N",
        help=(
            "The maximum number of simultaneously running tasks SLURM "
            "should allow when scheduling an array job."
        ),
    )

    parser.add_argument(
        "--keepInputs",
        action="store_false",
        dest="removeInputs",
        help=(
            "Remove temporary input files (note that these are not created "
            "if --inline is used) upon successful completion of jobs. "
            "For jobs that end in error, the temporary input file is always "
            "left in place."
        ),
    )

    parser.add_argument(
        "--keepErrorFiles",
        action="store_true",
        help=(
            "Keep .err files in --dir when each command run by "
            "SLURM is completed. These files are otherwise automatically "
            "removed - but only if they are empty."
        ),
    )

    parser.add_argument(
        "--keepSlurmFiles",
        action="store_true",
        help=(
            "Keep .slurm files in --dir when each command run by "
            "SLURM is completed. These files are otherwise automatically "
            "removed - but only if they are empty."
        ),
    )

    parser.add_argument(
        "--makeDoneFiles",
        action="store_true",
        help=(
            "Create .done files in --dir when each command run by "
            "SLURM is successfully completed. If commands do not complete "
            "successfully (exit with status zero), the .done files are "
            "not created, and the standard output and error of the command "
            "will be found in the corresponding .out and .err files in the "
            "--dir directory."
        ),
    )

    parser.add_argument(
        "--inline",
        action="store_true",
        help=(
            "Put the input for each invocation of the command into a shell "
            '"here" document (as opposed to using a separate input file for '
            "each invocation). This results in one less file being created "
            "for each invocation of the command, which may help avoid "
            "reaching a filesystem inode quota. If not given, input for "
            'each call to the command is written to a file ending in ".in" '
            "in the --dir directory. Note that these input files must be "
            "left in place until SLURM actually runs the jobs. The input "
            "files will be removed when the command completes, unless "
            "--keepInputs is used. This option is ignored unless --noArray "
            "is used, because an array job requires that inputs are in "
            "separate files."
        ),
    )

    parser.add_argument(
        "--header",
        action="store_true",
        help=(
            "Treat the first line of standard input as a header and include "
            "it as the first line in all groups of lines passed to "
            "the command.  The header is not given to any subsequent "
            "commands run using --then, --else, or --finally."
        ),
    )

    parser.add_argument(
        "--noJobIds",
        action="store_false",
        dest="printJobIds",
        help=(
            "Do not print SLURM job ids. Normally, job ids are printed in "
            "JSON format (you might want to later use a tool like jq (see "
            "https://stedolan.github.io/jq/) to post-process this output, "
            "for example to pass job ids to squeue or scancel."
        ),
    )

    parser.add_argument(
        "--uncompressed", action="store_true", help="Do not compress input files."
    )

    parser.add_argument(
        "--randomSleep",
        type=int,
        metavar="SECONDS",
        help=(
            "If given, SLURM jobs will sleep for a random number of seconds "
            "(after being launched by SLURM) before starting to process "
            "their input. This can be used to avoid overwhelming the I/O "
            "system on a cluster if many jobs are simultaneously trying to "
            "read their input. The sleep time will be a uniform value from "
            "1 to the given value."
        ),
    )

    parser.add_argument(
        "--compressLevel",
        type=int,
        metavar="N",
        choices=list(range(1, 10)),
        default=9,
        help=(
            "The bzip2 compression level for compressing input files. 1 is "
            "lowest (fastest) and 9 is highest (slowest). See man bzip2 for "
            "details. Ignored if --uncompressed is used."
        ),
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Report progress on making input files.",
    )

    return parser


def filePrefix(
    count: Optional[int],
    args: argparse.Namespace,
    condition: Optional[str] = None,
    array: bool = True,
    slurmHeader: bool = False,
    digits: int = 0,
) -> str:
    """
    Make a file path prefix.

    @param count: An C{int} count for numbering output files or C{None}
        if the file should not be numbered.
    @param args: An argparse C{Namespace} with command-line options.
    @param condition: A C{str} dependency condition that would be given
        to sbatch via --dependency (see 'man sbatch').
    @param slurmHeader: If C{True} and C{array} is C{True}, the file prefix
        should be for use in a '#SBATCH' script header. Otherwise, the
        prefix should use the SLURM environment variable SLURM_ARRAY_TASK_ID.
    @param digits: An C{int} count for numbering output files or C{None}
        if the file should not be numbered.
    @raise KeyError: if C{condition} is unknown (see 'names' below).
    @return: A C{str} file path prefix.
    """
    if array:
        suffix = "-%a" if slurmHeader else "-${SLURM_ARRAY_TASK_ID}"
    else:
        suffix = "" if count is None else f"-{count:0{digits}d}"

    return join(args.dir, f"{args.prefix}{CONDITION_NAMES[condition]}{suffix}")


def creationInfo() -> str:
    """
    Produce information regarding the creation of a script.

    @return: A C{str} with the date and id of the user.
    """
    return f'Generated {ctime(time())} by {environ.get("USER", "unknown")}.'


def writeInputFiles(
    chunks: Iterable[list[str]], args: argparse.Namespace, header: Optional[str] = None
) -> int:
    """
    Write out input files.

    @param chunks: An iterable that produces iterables of C{str} lines
        for each block of input.
    @param args: An argparse C{Namespace} with command-line options.
    @param header: A C{str} header line for the input to be given to the
        command, including trailing newline, or C{None} for no header.
    @return: The C{int} count of the number of files written.
    """
    count = 0
    for count, lines in enumerate(chunks, start=1):
        prefix = filePrefix(count, args, array=False)
        stdin = (header or "") + ("".join(lines) if lines else "")
        start = time()

        if args.uncompressed:
            filename = prefix + ".in"
            detail = f"{len(stdin):,} chars"
            with open(filename, "w") as fp:
                fp.write(stdin)
        else:
            filename = prefix + ".in.bz2"
            data = stdin.encode("utf-8")
            detail = f"{len(data):,} bytes"
            with bz2.open(filename, "wb", compresslevel=args.compressLevel) as fp:
                fp.write(data)

        if args.verbose:
            print(
                f"Wrote input file {filename!r} ({len(lines):,} lines, "
                f"{detail}, in {time() - start:.2f} seconds).",
                file=sys.stderr,
            )

    return count


def sbatchTextJobArray(
    nJobs: int,
    command: str,
    args: argparse.Namespace,
    after: Optional[Iterator[Union[str, int]]] = None,
    condition: Optional[str] = None,
) -> str:
    """
    Produce shell script text suitable for passing to sbatch to run the
    command using a job array.

    @param nJobs: The C{int} number of jobs in the array.
    @param command: The C{str} command to run.
    @param args: An argparse C{Namespace} with command-line options.
    @param after: An iterable of C{str} or C{int} job ids that need to complete
        (successully) before this job is run. When this is non-empty, the
        script filename will have the condition in it.
    @param condition: A C{str} dependency condition that would have been given
        to sbatch via --dependency (see 'man sbatch') if --dryRun had not been
        used.
    @return: A C{str} with shell script text.
    """
    prefix = filePrefix(None, args, condition)
    prefixNoZeroes = filePrefix(None, args, condition, digits=0)
    headerPrefix = filePrefix(None, args, condition, slurmHeader=True)
    if args.uncompressed:
        inputFile = f"{prefixNoZeroes}.in"
        input_ = f'< "{inputFile}"'
    else:
        inputFile = f"{prefixNoZeroes}.in.bz2"
        # There can be no space between the < and the ( in the following.
        input_ = f'< <(bzcat "{inputFile}")'
    out = f"{prefix}.out"
    err = f"{prefix}.err"
    slurmOutHeader = f"{headerPrefix}.slurm"
    slurmOut = f"{prefix}.slurm"
    jobName = f"{args.jobNamePrefix}{CONDITION_NAMES[condition]}"

    if args.makeDoneFiles:
        done = f"{prefix}.done"
        rmDone = f'rm -f "{done}"'
        touchDone = f'touch "{done}"'
    else:
        rmDone = touchDone = ""

    if after:
        dependencies = (
            f"# Would be run with sbatch --dependency "
            f'{condition or "afterok"}:' + ":".join(map(str, after))
        )
    else:
        dependencies = ""

    # Each job in the array must compute its own sleep time.
    sleep = f"sleep $(( 1 + RANDOM % {args.randomSleep} ))" if args.randomSleep else ""

    removeInput = f'rm "{inputFile}"' if args.removeInputs else ""

    arrayMax = f"%{args.arrayMax}" if args.arrayMax is not None else ""

    removeErrors = "" if args.keepErrorFiles else 'test -s "$err_" || rm "$err_"'

    removeSlurm = (
        ""
        if args.keepSlurmFiles
        else f'test -e "{slurmOut}" && ( test -s "{slurmOut}" || rm "{slurmOut}" )'
    )

    return f"""#!/bin/bash

#SBATCH -J {jobName}
#SBATCH -o {slurmOutHeader}
#SBATCH -p {args.partition}
#SBATCH --array=1-{nJobs}{arrayMax}
#SBATCH --nodes=1
#SBATCH --cpus-per-task={args.cpus}
#SBATCH --mem={args.mem}
#SBATCH --time={args.timePerJob}

set -Eeuo pipefail

# {creationInfo()}
{dependencies}

{sleep}

count_=$(printf '%*d' {args.digits} $SLURM_ARRAY_TASK_ID | tr ' ' 0)
out_=$(echo "{out}" | sed -e "s/-$SLURM_ARRAY_TASK_ID\\.out\\$/-$count_.out/")
err_=$(echo "{err}" | sed -e "s/-$SLURM_ARRAY_TASK_ID\\.err\\$/-$count_.err/")

{rmDone}

exec > "$out_" 2> "$err_"

{command} {input_}

{touchDone}
{removeInput}
{removeErrors}
{removeSlurm}
"""


def sbatchText(
    lines: Optional[Iterable[str]],
    command: str,
    count: int,
    args: argparse.Namespace,
    header: Optional[str] = None,
    after: Optional[Iterable[Union[str, int]]] = None,
    condition: Optional[str] = None,
) -> str:
    """
    Produce shell script text suitable for passing to sbatch to run the
    command on the input in C{lines}.

    @param lines: An iterable of C{str} input lines to be passed to the
        command.
    @param command: The C{str} command to run.
    @param count: An C{int} count for numbering output files.
    @param args: An argparse C{Namespace} with command-line options.
    @param header: A C{str} header line for the input to be given to the
        command, including trailing newline, or C{None} for no header.
    @param after: An iterable of C{str} or C{int} job ids that need to complete
        (successully) before this job is run. When this is non-empty, the
        script filename will have the condition in it.
    @param condition: A C{str} dependency condition that would have been given
        to sbatch via --dependency (see 'man sbatch') if --dryRun had not been
        used.
    @return: A C{str} with shell script text.
    """
    prefix = filePrefix(count, args, condition, array=False, digits=args.digits)
    err = f"{prefix}.err"
    out = f"{prefix}.out"
    slurmOut = f"{prefix}.slurm"
    stdin = (header or "") + ("".join(lines) if lines else "")
    jobName = (
        f"{args.jobNamePrefix}" f"{CONDITION_NAMES[condition]}-{count:0{args.digits}d}"
    )

    if args.makeDoneFiles:
        done = f"{prefix}.done"
        rmDone = f"rm -f {done!r}"
        touchDone = f"touch {done!r}"
    else:
        rmDone = touchDone = ""

    if after:
        dependencies = (
            f"# Would be run with sbatch --dependency "
            f'{condition or "afterok"}:' + ":".join(map(str, after))
        )
    else:
        dependencies = ""

    sleep = f"sleep $(( 1 + RANDOM % {args.randomSleep} ))" if args.randomSleep else ""

    removeInput = ""

    if stdin:
        if args.inline:
            # Use a shell 'here' document to provide the input.
            delim = "EOT-" * 10
            assert delim not in stdin
            nl = "" if stdin.endswith("\n") else "\n"
            input_ = f"<<{delim!r}\n{stdin}{nl}{delim}"
        else:
            if args.uncompressed:
                inputFile = f"{prefix}.in"
                input_ = f"< {inputFile!r}"
                with open(inputFile, "w") as fp:
                    fp.write(stdin)
            else:
                inputFile = f"{prefix}.in.bz2"
                # There can be no space between the < and the ( in the
                # following.
                input_ = f"< <(bzcat {inputFile!r})"
                with bz2.open(inputFile, "wb", compresslevel=args.compressLevel) as fp:
                    fp.write(stdin.encode("utf-8"))

            if args.removeInputs:
                removeInput = f"rm {inputFile!r}"
    else:
        input_ = ""

    removeErrors = "" if args.keepErrorFiles else f"test -s {err!r} || rm {err!r}"

    removeSlurm = (
        ""
        if args.keepSlurmFiles
        else f"test -e {slurmOut!r} && ( test -s {slurmOut!r} || rm {slurmOut!r} )"
    )

    return f"""#!/bin/bash

#SBATCH -J {jobName}
#SBATCH -o {slurmOut}
#SBATCH -p {args.partition}
#SBATCH --nodes=1
#SBATCH --cpus-per-task={args.cpus}
#SBATCH --mem={args.mem}
#SBATCH --time={args.timePerJob}

set -Eeuo pipefail

# {creationInfo()}
{dependencies}

{sleep}

{rmDone}

exec > {out!r} 2> {err!r}

{command} {input_}

{touchDone}

{removeInput}
{removeErrors}
{removeSlurm}
"""


def writeSbatchFile(
    text: str,
    count: Optional[int],
    args: argparse.Namespace,
    condition: Optional[str] = None,
    digits: int = 0,
) -> None:
    """
    Write a shell script suitable for passing to sbatch to run C{command} on
    the input in C{lines}.

    @param text: The C{str} sbatch command text.
    @param count: An C{int} count for numbering output files.
    @param args: An argparse C{Namespace} with command-line options.
    @param condition: A C{str} dependency condition that would have been given
        to sbatch via --dependency (see 'man sbatch') if --dryRun had not been
        used (may be C{None} if there are no dependencies).
    @param digits: An C{int} count for numbering output files or C{None}
        if the file should not be numbered.
    """
    prefix = filePrefix(count, args, condition, array=False, digits=digits)
    filename = prefix + ".sbatch"

    with open(filename, "w") as fp:
        print(text, file=fp)

    # Give execute permission to anyone who had read permission.
    mode = os.stat(filename).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(filename, mode)


def runSbatch(
    text: str,
    args: argparse.Namespace,
    count: Optional[int] = None,
    header: Optional[str] = None,
    after: Optional[Iterable[Union[str, int]]] = None,
    condition: Optional[str] = None,
    digits: int = 0,
) -> Optional[int]:
    """
    Pass shell script text to sbatch.

    @param text: The C{str} sbatch script text.
    @param count: An C{int} count for numbering output files.
    @param args: An argparse C{Namespace} with command-line options.
    @param header: A C{str} header line for the input to be given to the
        command, including trailing newline, or C{None} for no header.
    @param after: An iterable of C{str} or C{int} job ids that need to complete
        (successully) before this job is run.
    @param condition: A C{str} dependency condition to give to sbatch via
        --dependency (see 'man sbatch') (may be C{None} if there are no
        dependencies).
    @raises ValueError: If a the job id in the sbatch output is not numeric.
    @return: An C{int} SLURM job id if a job is submitted, else C{None} (if
        --dryRun was used).
    """
    if args.dryRun:
        writeSbatchFile(text, count, args, condition, digits=digits)
        return None

    sbatchCommand = ["sbatch", "--kill-on-invalid-dep=yes"]
    if after:
        sbatchCommand.extend(
            ["--dependency", f'{condition or "afterok"}:' + ":".join(map(str, after))]
        )

    proc = subprocess.Popen(
        sbatchCommand, text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )

    stdout, stderr = proc.communicate(input=text)

    if proc.returncode:
        filename = (
            filePrefix(count, args, condition, array=False, digits=digits)
            + ".sbatch-error"
        )

        with open(filename, "w") as fp:
            print(text, file=fp)

        print(
            f"sbatch submission failed (exit status {proc.returncode})! "
            f"sbatch input left in {filename!r}. Exiting.",
            file=sys.stderr,
        )

        if stdout:
            print("sbatch standard output: {stdout!r}.", file=sys.stderr)

        if stderr:
            print("sbatch standard error: {stderr!r}.", file=sys.stderr)

        sys.exit(proc.returncode)
    else:
        # sbatch prints one line of output, with the job id in the 4th field.
        return int(stdout.split()[3])


def take(lines: Iterator[str], n: int, header: Optional[str]) -> Iterable[list[str]]:
    """
    Read and yield lines from C{lines} in groups of C{n}, ignoring any header
    lines.

    @param lines: An iterable of C{str} lines.
    @param n: An C{int} number of lines per group. If zero, all lines are returned
        as a single group.
    @param header: A C{str} header line to ignore (may be C{None}).
    @return: A generator that produces C{list}s containing C{n} lines, with
        the final list possibly containing fewer, depending on len(lines) % n.
    """
    while True:
        count = 0
        result: list[str] = []
        while n == 0 or count < n:
            try:
                line = next(lines)
            except StopIteration:
                if result:
                    yield result
                return
            else:
                if line != header:
                    result.append(line)
                    count += 1
                    if count == n:
                        yield result
                        break


def main(args) -> None:
    """
    Read standard input and arrange for groups of lines to be passed to a
    command via sbatch and for additional commands to be scheduled to run
    after the main processing completes.
    """
    if args.inline and args.array:
        print("--inline makes no sense unless you also use --noArray.", file=sys.stderr)
        sys.exit(1)

    if args.dir is None:
        args.dir = mkdtemp(prefix="sbatch-stdin")
        print(f"sbatch files will be stored in {args.dir!r}.", file=sys.stderr)
    else:
        if not exists(args.dir):
            os.makedirs(args.dir, exist_ok=False)

    header = next(sys.stdin) if args.header else None
    chunks = take(sys.stdin, args.linesPerJob, header)

    # Submit the initial jobs.
    initialJobIds = []
    command = " ".join(args.command)
    if args.array:
        nFiles = writeInputFiles(chunks, args, header)
        stdin = sbatchTextJobArray(nFiles, command, args, after=args.afterok)
        jobId = runSbatch(stdin, args, header=header, after=args.afterok)
        if jobId:
            initialJobIds.append(jobId)
    else:
        for count, lines in enumerate(chunks):
            stdin = sbatchText(lines, command, count, args, header, after=args.afterok)
            jobId = runSbatch(
                stdin,
                args,
                count=count,
                header=header,
                after=args.afterok,
                digits=args.digits,
            )
            if jobId:
                initialJobIds.append(jobId)

    # Submit the '--then' jobs to run (in order) after all initial jobs
    # (if all initial jobs succeed).
    pendingJobIds = initialJobIds[:]
    thenJobIds = []
    for count, command in enumerate(args.then or []):
        stdin = sbatchText(
            None, command, count, args, after=pendingJobIds, condition="afterok"
        )
        jobId = runSbatch(
            stdin,
            args,
            count=count,
            after=pendingJobIds,
            condition="afterok",
            digits=args.digits,
        )
        if jobId:
            pendingJobIds = [jobId]
            thenJobIds.append(jobId)

    # Submit the '--else' jobs to all run at once if anything fails.
    elseJobIds = []
    for count, command in enumerate(args.else_ or []):
        stdin = sbatchText(
            None, command, count, args, after=pendingJobIds, condition="afternotok"
        )
        jobId = runSbatch(
            stdin,
            args,
            count=count,
            after=pendingJobIds,
            condition="afternotok",
            digits=args.digits,
        )
        if jobId:
            elseJobIds.append(jobId)

    # Submit the '--finally' jobs to run after everything, regardless of
    # success or failure of the earlier steps.
    finalJobIds = []
    for count, command in enumerate(args.finally_ or []):
        stdin = sbatchText(
            None, command, count, args, after=pendingJobIds, condition="after"
        )
        jobId = runSbatch(
            stdin,
            args,
            count=count,
            after=pendingJobIds + elseJobIds,
            condition="after",
            digits=args.digits,
        )
        if jobId:
            finalJobIds.append(jobId)

    if not args.dryRun and args.printJobIds:
        print(
            dumps(
                {
                    "initial": initialJobIds,
                    "then": thenJobIds,
                    "else": elseJobIds,
                    "finally": finalJobIds,
                    "all": initialJobIds + thenJobIds + elseJobIds + finalJobIds,
                },
                indent=2,
                separators=(", ", ": "),
            )
        )


if __name__ == "__main__":
    main(makeParser().parse_args())
