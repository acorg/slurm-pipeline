#!/usr/bin/env python

import sys
import argparse
import subprocess
import os
from os.path import exists, join
from tempfile import mkdtemp

CONDITION_NAMES = {
    'after': 'finally',
    'afterok': 'then',
    'afternotok': 'else',
    None: 'initial',
}


def makeParser():
    """
    Make an argparse parser for the command line.

    @return: An C{argparse} parser.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('Use sbatch to run a command on data read from standard '
                     'input, optionally split into multiple jobs.'))

    parser.add_argument(
        'command', metavar='COMMAND', nargs='+',
        help=('An executable command to schedule for running via sbatch, '
              'passing it lines of standard input. If the command contains '
              'shell metacharacters it will need to be quoted. If '
              '--linesPerJob is given, standard input will be broken into '
              'groups of lines and each group will be passed to a separate '
              'invocation of the command.'))

    parser.add_argument(
        '--linesPerJob', '-N', type=int, metavar='N',
        help=('The number of lines of standard input to give to each '
              'invocation of the command. The final job will likely be given '
              'fewer lines of input when the original standard input '
              'empties. If not specified, all lines of standard input are '
              'passed to the command.'))

    parser.add_argument(
        '--outDir', metavar='DIR',
        help=('The directory where command input (if --noInline is used), '
              'output, and error files will be created, along with sbatch '
              '(if --dryRun is used). The directory will be created if it '
              'does not already exist, and if this argument is omitted the '
              'path to a newly-created directory will be printed to standard '
              'error.'))

    parser.add_argument(
        '--prefix', default='',
        help=('The prefix to use for input, output, and sbatch files written '
              'to --outDir.'))

    parser.add_argument(
        '--afterok', nargs='*',
        help=('An (optional) list of job ids to run after, assuming they all '
              'finish successully. If the listed jobs do not finish '
              'successully, the job(s) to run the main command will not '
              'execute (but --else and --finally commands will run).'))

    parser.add_argument(
        '--mem', default='8G',
        help=('The amount of memory to request from sbatch for each run of '
              'the command.'))

    parser.add_argument(
        '--cpus', default=1, metavar='N',
        help=('The number of cpus per task to ask sbatch for via the '
              '--cpus-per-task argument.'))

    parser.add_argument(
        '--digits', default=5, metavar='N',
        help=('The total number of digits to use in (zero-padded) file names '
              'written to --outDir.'))

    parser.add_argument(
        '--timePerJob', default='10:00',
        help=('The amount of time to request from SLURM for each sbatch job. '
              'From man sbatch: acceptable time formats include  "minutes", '
              '"minutes:seconds", "hours:minutes:seconds", "days-hours", '
              '"days-hours:minutes", and "days-hours:minutes:seconds".'))

    parser.add_argument(
        '--partition', default='medium',
        help='The SLURM partition to use.')

    parser.add_argument(
        '--then', action='append', metavar='COMMAND',
        help=('Specify a command to run after all SLURM jobs are finished '
              '(assuming they all finish without error). May be repeated, in '
              'which case the commands are run (by SLURM) in the order '
              'given on the command line once the previous command has '
              'finished.'))

    parser.add_argument(
        '--else', action='append', dest='else_',
        metavar='COMMAND',
        help=('Specify a command to run if any of the SLURM jobs finishes '
              'with an error (i.e., exits with a non-zero status). May be '
              'repeated, in which case the commands are all run (by '
              'SLURM) at once, not sequentially as with --then. I.e., '
              'following the failure of any job, SLURM can immediately '
              'schedule all --else commands.'))

    parser.add_argument(
        '--finally', action='append', dest='finally_',
        metavar='COMMAND',
        help=('Specify a command to run when all SLURM jobs (the original '
              'command and any --then or --else jobs) have finished, '
              'regardless of their exit status. May be repeated, in which '
              'case the commands are all run (by SLURM) at once, not '
              'sequentially as with --then. I.e., following the termination '
              'of all jobs, SLURM can immediately schedule all --finally '
              'commands.'))

    parser.add_argument(
        '--jobNamePrefix', '-J', default='sbatch-stdin-', metavar='PREFIX',
        help=('The job name prefix. This will have a numeric count appended '
              'to it for each job submitted to SLURM.'))

    parser.add_argument(
        '--dryRun', '-n', action='store_true',
        help='Do not actually do anything, just print what would be done.')

    parser.add_argument(
        '--makeDoneFiles', action='store_true',
        help=('Create empty .done files in --outDir when each command run by '
              'SLURM is complete.'))

    parser.add_argument(
        '--noInline', action='store_false', dest='inline',
        help=('Put the input for each invocation of the command into a '
              'separate file (as opposed to using a shell "here" document. '
              'This will obviously result in one additional file being '
              'created for each invocation of the command, which may not be '
              'acceptable due to filesystem inode quota. If given, input for '
              'each call to the command is written to a file ending in ".in" '
              'in the --outDir directory. Note that these input files must be '
              'left in place until SLURM actually runs the jobs.'))

    parser.add_argument(
        '--header', action='store_true',
        help=('Treat the first line of standard input as a header and include '
              'it as the first line in all groups of lines passed to '
              'the command.  The header is not given to any subsequent '
              'commands run using --then, --else, or --finally.'))

    parser.add_argument(
        '--printJobIds', action='store_true',
        help=('Print the ids (one per line) of any initial jobs submitted to '
              'SLURM.'))

    return parser


def filePrefix(count, args, after=None, condition=None):
    """
    Make a file path prefix.

    @param count: An C{int} count for numbering output files.
    @param args: An argparse C{Namespace} with command-line options.
    @param after: An iterable of C{str} job ids that need to complete
        (successully) before this job is run. When this non-empty, the
        filename will have the condition in it.
    @param condition: A C{str} dependency condition that would be given
        to sbatch via --dependency (see 'man sbatch').
    @raise KeyError: if C{condition} is unknown (see 'names' below).
    @return: A C{str} file path prefix.
    """
    return join(args.outDir,
                f'{args.prefix}{CONDITION_NAMES[condition]}-'
                f'{count:0{args.digits}d}')


def sbatchText(lines, command, count, args, header=None, after=None,
               condition=None):
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
    @param after: An iterable of C{str} job ids that need to complete
        (successully) before this job is run. When this is non-empty, the
        script filename will have the condition in it.
    @param condition: A C{str} dependency condition that would have been given
        to sbatch via --dependency (see 'man sbatch') if --dryRun had not been
        used.
    @return: A C{str} with shell script text.
    """
    prefix = filePrefix(count, args, after, condition)
    err = f'{prefix}.err'
    out = f'{prefix}.out'
    slurmOut = f'{prefix}.slurm'
    stdin = (header or '') + (''.join(lines) if lines else '')
    jobName = (f'{args.jobNamePrefix}'
               f'{CONDITION_NAMES[condition]}-{count:0{args.digits}d}')

    if args.makeDoneFiles:
        done = f'{prefix}.done'
        rmDone = f'rm -f {done!r}'
        touchDone = f'touch {done!r}'
    else:
        rmDone = touchDone = ''

    if after:
        dependencies = (
            f'# Would be run with sbatch --dependency '
            f'{condition or "afterok"}:' + ':'.join(map(str, after)))
    else:
        dependencies = ''

    if stdin:
        if args.inline:
            # Use a shell 'here' document to provide the input.
            delim = 'EOT-' * 10
            assert delim not in stdin
            nl = '' if stdin.endswith('\n') else '\n'
            input_ = f'<<{delim!r}\n{stdin}{nl}{delim}'
        else:
            in_ = f'{prefix}.in'
            with open(in_, 'w') as fp:
                print(stdin, end='', file=fp)
            input_ = f'< {in_!r}'
    else:
        input_ = ''

    return (f'''#!/bin/bash

#SBATCH --cpus-per-task={args.cpus}
#SBATCH -J {jobName}
#SBATCH -o {slurmOut}
#SBATCH -p {args.partition}
#SBATCH --nodes=1
#SBATCH --mem={args.mem}
#SBATCH --time={args.timePerJob}

set -Eeuo pipefail

{dependencies}

{rmDone}

( {command} ) > {out!r} 2> {err!r} {input_}

test -s {err!r} || rm {err!r}
test -e {slurmOut!r} && ( test -s {slurmOut!r} || rm {slurmOut!r} )

{touchDone}
''')


def writeSbatchFile(lines, command, count, args, header=None, after=None,
                    condition=None):
    """
    Write a shell script suitable for passing to sbatch to run C{command} on
    the input in C{lines}.

    @param lines: An iterable of C{str} input lines to be passed to the
        command.
    @param command: The C{str} command to run.
    @param count: An C{int} count for numbering output files.
    @param args: An argparse C{Namespace} with command-line options.
    @param header: A C{str} header line for the input to be given to the
        command, including trailing newline, or C{None} for no header.
    @param after: An iterable of C{str} job ids that need to complete
        (successully) before this job is run. When this non-empty, the
        script filename will have the condition in it.
    @param condition: A C{str} dependency condition that would have been given
        to sbatch via --dependency (see 'man sbatch') if --dryRun had not been
        used (may be C{None} if there are no dependencies).
    """
    filename = filePrefix(count, args, after, condition) + '.sbatch'

    with open(filename, 'w') as fp:
        print(sbatchText(lines, command, count, args, header, after,
                         condition), file=fp)

    # Give execute permission to anyone who had read permission.
    mode = os.stat(filename).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(filename, mode)


def runSbatch(lines, command, count, args, header=None, after=None,
              condition=None):
    """
    Create and pass a shell script to sbatch to run the command on the input in
    C{lines}.

    @param lines: An iterable of C{str} input lines to be passed to the
        command.
    @param command: The C{str} command to run.
    @param count: An C{int} count for numbering output files.
    @param args: An argparse C{Namespace} with command-line options.
    @param header: A C{str} header line for the input to be given to the
        command, including trailing newline, or C{None} for no header.
    @param after: An iterable of C{str} job ids that need to complete
        (successully) before this job is run.
    @param condition: A C{str} dependency condition to give to sbatch via
        --dependency (see 'man sbatch') (may be C{None} if there are no
        dependencies).
    @return: A C{str} SLURM job id if a job is submitted, else C{None} (if
        --dryRun was used).
    """
    if args.dryRun:
        writeSbatchFile(lines, command, count, args, header, after, condition)
        return

    stdin = sbatchText(lines, command, count, args, header, after, condition)

    sbatchCommand = ['sbatch', '--kill-on-invalid-dep=yes']
    if after:
        sbatchCommand.extend([
            '--dependency',
            f'{condition or "afterok"}:' + ':'.join(map(str, after))])

    proc = subprocess.Popen(sbatchCommand, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    stdout, stderr = proc.communicate(input=stdin)

    if proc.returncode:
        filename = filePrefix(count, args, after, condition) + '.sbatch-error'

        with open(filename, 'w') as fp:
            print(stdin, file=fp)

        print(f'sbatch submission failed! sbatch input left in {filename!r}. '
              f'Exiting.', file=sys.stderr)

        if stdout:
            print('sbatch standard output: {stdout!r}.', file=sys.stderr)

        if stderr:
            print('sbatch standard error: {stderr!r}.', file=sys.stderr)

        sys.exit(proc.returncode)
    else:
        # sbatch prints one line of output, with the job id in the 4th field.
        # Note that although these are (currently) always integers, we are
        # returning a string.
        return stdout.split()[3]


def take(lines, n, header):
    """
    Read and yield lines from C{lines} in groups of C{n}, ignoring any header
    lines.

    @param lines: An iterable of C{str} lines.
    @param n: An C{int} number of lines per group.
    @param header: A C{str} header line to ignore (may be C{None}).
    @return: A generator that produces C{list}s containing C{n} lines, with
        the final list containing fewer depending on len(lines) % n.
    """
    while True:
        count = 0
        result = []
        while count < n:
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


def main(args):
    """
    Read standard input and arrange for groups of lines to be passed to a
    command via sbatch and for additional commands to be scheduled to run
    after the main processing completes.
    """
    if args.outDir is None:
        args.outDir = mkdtemp(prefix='sbatch-stdin')
        print(f'sbatch files will be stored in {args.outDir!r}.',
              file=sys.stderr)
    else:
        if not exists(args.outDir):
            os.makedirs(args.outDir, exist_ok=False)

    if args.linesPerJob is None:
        chunks = [sys.stdin]
        header = None
    else:
        header = next(sys.stdin) if args.header else None
        chunks = take(sys.stdin, args.linesPerJob, header)

    # Submit the initial jobs.
    jobIds = []
    for count, lines in enumerate(chunks):
        # We use 'condition=None' below so we end up with 'initial' in the
        # various file names, and rely on the sbatch --dependency condition
        # being set to 'afterok' (in runSbatch) in this case.
        jobId = runSbatch(lines, ' '.join(args.command), count, args, header,
                          after=args.afterok, condition=None)
        if jobId:
            jobIds.append(jobId)

    # Submit the '--then' jobs to run after all initial jobs (if they all
    # succeed).
    for count, command in enumerate(args.then or []):
        jobId = runSbatch(None, command, count, args, after=jobIds,
                          condition='afterok')
        if jobId:
            jobIds = [jobId]

    # Submit the '--else' jobs to all run at once if anything fails.
    elseJobIds = []
    for count, command in enumerate(args.else_ or []):
        jobId = runSbatch(None, command, count, args, after=jobIds,
                          condition='afternotok')
        if jobId:
            elseJobIds.append(jobId)

    # Submit the '--finally' jobs to run after everything, regardless of
    # success or failure of the earlier steps.
    finalJobIds = []
    for count, command in enumerate(args.finally_ or []):
        jobId = runSbatch(None, command, count, args,
                          after=jobIds + elseJobIds, condition='after')
        if jobId:
            finalJobIds.append(jobId)

    # It's not clear which set of job ids to print. So for now just print
    # those of the original jobs (or just the final --then job, if --then
    # was used).
    if args.printJobIds and jobIds:
        print('\n'.join(map(str, sorted(jobIds))))


if __name__ == '__main__':
    main(makeParser().parse_args())
