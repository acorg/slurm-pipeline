# slurm-pipeline

A [Python](https://www.python.org) class and utility scripts for scheduling
and examining [SLURM](http://slurm.schedmd.com/)
([wikipedia](https://en.wikipedia.org/wiki/Slurm_Workload_Manager)) jobs.

Runs under Python 3.6 to 3.9, and [pypy](http://pypy.org/)
[Change log](CHANGELOG.md).
[![Build Status](https://app.travis-ci.com/acorg/slurm-pipeline.svg?branch=master)](https://app.travis-ci.com/acorg/slurm-pipeline)

License: [MIT](https://mit-license.org/).

Funding for the original development of this package came from:

* the European Union Horizon 2020 research and innovation programme,
  [COMPARE](http://www.compare-europe.eu/) grant (agreement No. 643476), and
* U.S. Federal funds from the Department of Health and Human Services;
  Office of the Assistant Secretary for Preparedness and Response;
  Biomedical Advanced Research and Development Authority, under Contract
  No. HHSO100201500033C

## Installation

### From conda

Add the conda-forge channel if you don't have it already (check
with `conda config --show channels`):

```sh
$ conda config --add channels conda-forge
$ conda config --set channel_priority strict
```

slurm-pipeline can then be installed with:

```sh
$ conda install slurm-pipeline
```

### From PyPI using pip

Using [pip](https://pypi.python.org/pypi/pip):

```sh
$ pip install slurm-pipeline
```

### From Git sources

Using [git](https://git-scm.com/downloads):

```sh
# Clone repository.
$ git clone https://github.com/acorg/slurm-pipeline
$ cd slurm-pipeline

# Install, including development dependencies.
$ pip install -e '.[dev]'

# Run the tests.
$ pytest
```

## Scripts

The `bin` directory of this repo contains the following Python scripts:

* `slurm-pipeline.py` schedules programs to be run in an organized pipeline
  fashion on a Linux cluster that uses SLURM as a workload manager.
  `slurm-pipeline.py` must be given a JSON pipeline specification (see next
  section). It prints a corresponding JSON status that contains the
  original specification plus information about the scheduling (times, job
  ids, etc). By *pipeline*, I mean a collection of programs that are run in
  order, taking into account (possibly complex) inter-program dependencies.
* `slurm-pipeline-status.py` must be given a specification status (as
  produced by `slurm-pipeline.py`) and prints a summary of the status
  including job status (obtained from `sacct`). It can also be used to
  print a list of unfinished jobs (useful for canceling the jobs of a
  running specification) or a list of the final jobs of a scheduled
  pipeline (useful for making sure that jobs scheduled in a subsequent run
  of `slurm-pipeline.py` do not begin until the given pipeline has
  finished). See below for more information.
* `slurm-pipeline-status-plot.py` uses [plotly](https://plotly.com/python/)
  to produce an interactive HTML and/or a static image to show the progress
  of a number of pipeline runs.
* `slurm-pipeline-version.py` prints the version number.
* `sbatch.py`, a utility script (<a href="#sbatch.py">described below</a>)
  for _ad hoc_ scheduling of a command, optionally with its original
  standard input broken into chunks to be passed to the command and the
  specification of subsequent scripts to be run on completion of the
  original SLURM job(s).
* `remove-repeated-headers.py`, a simple helper script for post-processing
  output files created by SLURM following the use of `sbatch.py`.

## Pipeline specification

A pipeline run is scheduled according to a specification file in JSON
format which is passed to `slurm-pipeline.py`. Several examples of these can
be found under [`examples`](examples). Here's the one from
[`examples/word-count/specification.json`](examples/word-count/specification.json):

```json
{
    "steps": [
        {
            "name": "one-per-line",
            "script": "scripts/one-word-per-line.sh"
        },
        {
            "dependencies": ["one-per-line"],
            "name": "long-words",
            "script": "scripts/long-words-only.sh"
        },
        {
            "collect": true,
            "dependencies": ["long-words"],
            "name": "summarize",
            "script": "scripts/summarize.sh"
        }
    ]
}
```

The example specification above contains most of what you need to know to
set up your own pipeline. You'll still have to write the scripts though, of
course.

## Steps

A pipeline run is organized into a series of conceptual *steps*. These are
processed in the order they appear in the specification file. Step scripts
will typically use the SLURM
[`sbatch`](https://slurm.schedmd.com/sbatch.html) command to schedule the
later execution of other programs.

Each step must contain a `name` key. Names must be unique.

Each step must also contain a `script` step. This gives the file name of a
program to be run. The file must exist at the time of scheduling and must
be executable.

Optionally, a step may have a `dependencies` key which gives a list of step
names upon which the step depends. Any dependency named must have already
been defined in the specification.

Optionally, a script may specify `collect` with a `true` value. This will
cause the script to be run when all the *tasks* (see next section) started
by earlier dependent steps have completed.

The full list of specification directives is given <a
href="#directives">below</a>.

## Tasks

A step script may emit one or more *task*s. A task is really nothing more
than the name of a piece of work that is passed to successive (dependent)
scripts in the pipeline. The task name might correspond to a file, to an
entry in a database, to a URL - whatever it is that your scripts need to be
passed so they can do their work.

The script lets `slurm-pipeline.py` know about tasks by printing lines such
as `TASK: xxx 39749 39750` to its standard output. In this example, the
script is indicating that a task named `xxx` has been scheduled and that
two SLURM jobs (with ids `39749` and `39750`) have been scheduled (via
`sbatch`) to complete whatever work is needed for the task.

Any other output from a step script is ignored (it is however stored in the
JSON output produced by `slurm-pipeline.py`, provided you are using Python
version 3).

When a step depends on an earlier step (or steps), its `script` will be
called with a single argument: the name of a task emitted by the script of
the earlier step(s). If a step depends on multiple earlier steps that each
emit the same task name, the script will only be called once, with that
task name as an argument, once all the jobs from all the dependent steps
have finished.

So, for example, a step that starts the processing of 10 FASTA files could
just use the file names as task names. This will cause ten subsequent
invocations of any dependent step's script, called with each of the task
names (i.e., the file names in this example).

If a script emits `TASK: xxx` with no job id(s), the named task will be
passed along the pipeline but dependent steps will not need to wait for any
SLURM job to complete before being invoked. This is useful when a script
does its work synchronously (i.e., without scheduling anything via SLURM).

If a step specification uses `"collect": true`, its script will only be
called once. The script's arguments will be the names of all tasks emitted
by the steps it depends on.

Steps that have no dependencies are called with any additional (i.e.,
unrecognized) command-line arguments given to `slurm-pipeline.py`.  For
example, given the specification above,

```sh
$ cd examples/word-count
$ slurm-pipeline.py -s specification.json --scriptArgs texts/*.txt > status.json
```

will cause `one-word-per-line.sh` from the first specification step to be
called with the files matching `texts/*.txt`. The script of the second
step (`long-words-only.sh`) will be invoked multiple times (once for each
`.txt` file). The script will be invoked with the task names emitted by
`one-word-per-line.sh` (the names can be anything desired; in this case
they are the file names without the `.txt` suffix). The (`collect`) script
(`summarize.sh`) of the third step will be called with the names of *all*
the tasks emitted by its dependency (the second step).

The standard input of invoked scripts is closed.

The file `status.json` produced by the above will contain the original
specification, updated to contain information about the tasks that have
been scheduled, their SLURM job ids, script output, timestamps, etc. See
the `word-count` example below for sample output.

## slurm-pipeline.py options

`slurm-pipeline.py` accepts the following options:

* `--specification filename`: Described above. Required.
* `--output filename`: Specify the file to which pipeline status
  information should be written to (in JSON format). Defaults to standard
  output.
* `--force`: Will cause `SP_FORCE` to be set in the environment of step
  scripts with a value of `1`. It is up to the individual scripts to notice
  this and act accordingly. If `--force` is not used, `SP_FORCE` will be
  set to `0`.
* `--firstStep step-name`: Step scripts are always run with an environment
  variable called `SP_SKIP`. Normally this is set to `0` for all
  steps. Sometimes though, you may want to start a pipeline from one of its
  intermediate steps and not re-do the work of earlier steps. If you
  specify `--firstStep step-name`, the steps before `step-name` will be
  invoked with `SP_SKIP=1` in their environment. It is up to the scripts to
  decide how to act when `SP_SKIP=1`.
* `--lastStep step-name`: Corresponds to `--firstStep`, except it indicates
  that step execution should be skipped (i.e., it sets `SP_SKIP=1`) for
  steps after the named step. Note that `--firstStep` and `--lastStep` may
  specify an identical step, to just run one step.
* `--skip`: Used to tell `slurm-pipeline.py` to tell a step script that it
  should be skipped. When skipped, a script should make sure that
  subsequent steps in the pipeline can still proceed. Commonly this will
  mean just taking its expected input file and copying it unchanged to the
  place where it normally puts its output, or if the output is already
  present due to a prior run, just doing nothing. This argument may be
  repeated to skip multiple steps. See also the `skip` directive that can
  be used in a specification file for more permanent disabling of a script
  step.
* `--startAfter`: Specify one or more SLURM job ids that must be allowed to
  complete (in any state - successful or in error) before the initial steps
  of the current specification are allowed to run. If you have saved the
  output of a previous `slurm-pipeline.py` run, you can use
  `slurm-pipeline-status.py --printFinal` to output the final job ids of
  that previous run and give those job ids to a subsequent invocation of
  `slurm-pipeline.py` (see `slurm-pipeline-status.py` below for an
  example).
* `--scriptArgs`: Specify arguments that should appear on the command line
  when initial step scripts are run. The initial steps are those that do
  not have any dependencies.
* `--printOutput`: Print the output of running each step to standard
  output.  Note that the output of each step is also always contained in
  the JSON status output (which is also printed to standard output unless
  the `--output` option is used to redirect it).

It is important to understand that all script steps are *always* invoked,
including when `--firstStep` or `--skip` are used. See below for the
reasoning behind this.  It is up to the scripts to decide what to do (based
on the `SP_*` environment variables).

`slurm-pipeline.py` prints an updated specification to `stdout` or to the
file specified with `--output`. You will probably always want to save this
to a file so you can later pass it to `slurm-pipeline-status.py`. If you
forget to redirect `stdout` (and don't use `--output`), information about
the progress of the scheduled pipeline can be very difficult to recover
(you may have many other jobs already scheduled, so it can be very hard to
know which jobs were started by which run of `slurm-pipeline.py` or by any
other method).  So if `stdout` is a terminal, `slurm-pipeline.py` tries to
help by writing the status specification to a temporary file (as well as
`stdout`) and prints that file's location (to `stderr`).

### Why are all step scripts always executed?

All scripts are always executed because `slurm-pipeline.py` cannot know
what arguments to pass to intermediate step scripts to run them in
isolaion. In a normal run with no skipped steps, steps emit task names that
are passed through the pipeline to subsequent steps. If the earlier steps
are not run, `slurm-pipeline.py` cannot know what task arguments to pass to
the scripts for those later steps.

It is also conceptually easier to know that `slurm-pipeline.py` always runs
all pipeline step scripts, whether or not they are being skipped (see <a
href="#separation">Separation of concerns</a> below).  Skipped steps may
also want to log the fact that the pipeline ran and they were skipped, etc.

<a id="directives"></a>
## Specification file directives

You've already seen most of the specification file directives above. Here's
the full list:

* `name`: the name of the step (required).
* `script`: the script to run (required). If given as a relative path, it
   must be relative to the `cwd` specification, if any. Note that if your
   script value does not contain a `/` and you do not have `.` in your
   shell's `PATH` variable you will need to specify your script with a
   leading `./` (e.g., `./scriptname.sh`) or it will not be found (by
   Python's `subprocess` module).
* `cwd`: the directory to run the script in. If no directory is given, the
   script will be run in the directory where you invoke
   `slurm-pipeline.py`.
* `collect`: for scripts that should run only when all tasks from all their
  prerequisites have completed.
* `dependencies`: a list of previous steps that a step depends on.
* `error step`: if `true` the step script will only be run if one of its
  dependencies fails. Making a step an error step results in
  `--dependency=afternotok:JOBID` being put into the `SP_DEPENDENCY_ARG`
  environment variable your step scripts will receive (see below). You will
  need a recent version of SLURM installed to be able to use error steps.
  Check the `--dependencies` option in `man sbatch` to make sure
  `afternotok` is supported.
* `skip`: if `true`, the step script will be run with `SP_SKIP=1` in its
  environment. Otherwise, `SP_SKIP` will always be set and will be `0`.

## Step script environment variables

Step scripts inherit environment variables that are set when
`slurm-pipeline.py` is run. The following additional variables are set:

* `SP_ORIGINAL_ARGS` will contain the (space-separated) list of arguments
  originally passed to `slurm-pipeline.py` using the `--scriptArgs`
  argument. Most scripts will not need to know this information, but it
  might be useful. Scripts for initial steps (those that have no
  dependencies) will be run with these arguments on the command line.  Note
  that if an original command-line argument contained a space (or shell
  metacharacter), and you split `SP_ORIGINAL_ARGS` on spaces, you'll have
  two strings instead of one (or other unintended result). For this reason,
  `SP_ORIGINAL_ARGS` has each argument wrapped in single quotes. The best
  way to process this variable (in `bash`) is to use `eval set
  "$SP_ORIGINAL_ARGS"` and then examine `$1`, `$2`, etc. It is currently not
  possible to pass an argument containing a single quote to a step script.
* `SP_FORCE` will be set to `1` if `--force` is given on the
  `slurm-pipeline.py` command line. This can be used to inform step scripts
  that they may overwrite pre-existing result files if they wish. If
  `--force` is not specified, `SP_FORCE` will be set to `0`.
* `SP_SKIP` will be set to `1` if the step should be skipped, and `0` if
  not. See the description of `--firstStep` and `--lastStep` above for how
  to turn step skipping on and off. When a step is skipped, its script
  should just emit its task name(s) as usual, but without SLURM job
  ids. The presumption is that a pipeline is being re-run and that the work
  that would normally be done by a step that is now being skipped has
  already been done. A script that is called with `SP_SKIP=1` might
  want to check that its regular output does in fact already exist, but
  there's no need to exit if not.
* `SP_DEPENDENCY_ARG` contains a string that must be used when the script
  invokes `sbatch` to guarantee that the execution of the script does not
  begin until after the tasks from all dependent steps have finished
  successfully.
* `SP_NICE_ARG` contains a string that should be put on the command line when
  calling `sbatch`. This sets the priority level of the SLURM jobs. The numeric
  nice value can be set using the `--nice` option when running `slurm-pipeline.py`.
  See `man sbatch` for details on nice values. Note that calling `sbatch` with
  this value is not enforced. The `--nice` option simply provides a simple way
  to specify a priority value on the command line and to pass it to scripts.
  Scripts can always ignore it or use their own value. If no value is given,
  `SP_NICE_ARG` will contain just the string `--nice`, which will tell SLURM
  to use a default nice value. It is useful to use a default nice value as it
  allows a regular user to later submit jobs with a higher priority (lower nice
  value). A regular user cannot use a negative nice value, so if a default
  nice value was not used, all jobs get nice value `0` which prevents the user
  from submitting higher priority jobs later on.

## Calling sbatch with SP_DEPENDENCY_ARG and SP_NICE_ARG

The canonical way to use `SP_DEPENDENCY_ARG` and `SP_NICE_ARG` when calling
`sbatch` in a step (bash) shell script is as follows:

```sh
jobid=$(sbatch $SP_DEPENDENCY_ARG $SP_NICE_ARG script.sh | cut -f4 -d' ')
echo TASK: task-name $jobid
```

This calls `sbatch` with the dependency and nice arguments (if any) and
gets the job id from the `sbatch` output (`sbatch` prints a line like
`Submitted batch job 3779695`) and the `cut` in the above pulls out just
the job id. The task name (here `task-name`) is then output, along with
the SLURM job id.

<a id="separation"></a>
## Separation of concerns

`slurm-pipeline.py` doesn't actually interact with SLURM at all. Actually,
the *only* things it knows about SLURM is how to construct `--dependency`
and `--nice` arguments for `sbatch`. The `slurm-pipeline-status.py` command
will however run `sacct` to get job status information.

To use `slurm-pipeline.py` you need to make a specification file such as
the one above to indicate the steps in your pipeline, their scripts, and
their dependencies.

Secondly, you need to write the scripts and arrange for them to produce
output and find their inputs. How you do this is totally up to you.

If your pipeline will process a set of files, it will probably make sense
to have an initial script emit the file names (or their basenames) as task
names. That will make it simple for later scripts to find the files from
earlier processing and to make file names to hold their own output.

You can confirm that `slurm-pipeline.py` doesn't even require that SLURM is
installed on a machine by running the examples in the `examples` directory.
The scripts in the examples all do their work synchronously (they emit fake
SLURM job ids using the Bash shell's `RANDOM` variable, just to make it
look like they are submitting jobs to `sbatch`).

## slurm-pipeline-status.py options

`slurm-pipeline-status.py` accepts the following options:

* `--specification filename`: must contain a status specification, as
    printed by `slurm-pipeline.py`. Required.
* `--fieldNames`: A comma-separated list of job status field names. These
    will be passed directly to `sacct` using its `--format` argument (see
    `sacct --helpformat` for the full list of field names). The values of
    these fields will be printed in the summary of each job in the
    `slurm-pipeline-status.py` output. For convenience, you can store your
    preferred set of field names in an environment variable,
    `SP_STATUS_FIELD_NAMES`, to be used each time you run
    `slurm-pipeline-status.py`.
* `--printFinished`: If specified, print a list of job ids that have finished.
* `--printUnfinished`: If specified, print a list of job ids that have
    not yet finished. This can be used to cancel a job, via e.g.,

    ```sh
    $ slurm-pipeline-status.py --specification spec.json --printUnfinished  | xargs -r scancel
    ```
* `--printFinal`: If specified, print a list of job ids issued by the
    final steps of a pipeline. This can be used with the
    `--startAfter` option to `slurm-pipeline.py` to make it schedule a
    different pipeline to run only after the first one finishes. E.g.,

    ```sh
    # Start a first pipeline and save its status:
    $ slurm-pipeline.py --specification spec1.json > spec1-status.json

    # Start a second pipeline once the first has finished (this assumes your shell is bash):
    $ slurm-pipeline.py --specification spec2.json \
        --startAfter $(slurm-pipeline-status.py --specification spec1-status.json --printFinal) \
        > spec2-status.json
    ```

If none of `--printUnfinished`, `--printUnfinished`, or `--printFinal` is
given, `slurm-pipeline-status.py` will print a detailed summary of the
status of the specification it is given.  This will include the current
status (obtained from [`sacct`](https://slurm.schedmd.com/sacct.html)) of
all jobs launched.  Output will resemble the following example:

```sh
$ slurm-pipeline.py --specification spec.json > status.json
```

```sh
$ slurm-pipeline-status.py --specification status.json
Scheduled by: tcj25
Scheduled at: 2018-04-15 21:20:23
Scheduling arguments:
  First step: None
  Force: False
  Last step: None
  Nice: None
  Sleep: 0.00
  Script arguments: <None>
  Skip: <None>
  Start after: <None>
Steps summary:
  Number of steps: 3
  Jobs emitted in total: 5
  Jobs finished: 5 (100.00%)
    sleep: 1 job emitted, 1 (100.00%) finished
    multisleep: 3 jobs emitted, 3 (100.00%) finished
    error: 1 job emitted, 1 (100.00%) finished
Step 1: sleep
  No dependencies.
  1 task emitted by this step
    Summary: 1 job started by this task, of which 1 (100.00%) are finished
    Tasks:
      sleep
        Job 1349824: JobName=sleep, State=COMPLETED, Elapsed=00:00:46, Nodelist=cpu-e-131
  Collect step: False
  Working directory: 01-sleep
  Scheduled at: 2018-04-15 21:20:23
  Script: submit.sh
  Skip: False
  Slurm pipeline environment variables:
    SP_FORCE: 0
    SP_NICE_ARG: --nice
    SP_ORIGINAL_ARGS:
    SP_SKIP: 0
Step 2: multisleep
  1 step dependency: sleep
    Dependent on 1 task emitted by the dependent step
    Summary: 1 job started by the dependent task, of which 1 (100.00%) are finished
    Dependent tasks:
      sleep
        Job 1349824: JobName=sleep, State=COMPLETED, Elapsed=00:00:46, Nodelist=cpu-e-131
  3 tasks emitted by this step
    Summary: 3 jobs started by these tasks, of which 3 (100.00%) are finished
    Tasks:
      sleep-0
        Job 1349825: JobName=multisleep, State=COMPLETED, Elapsed=00:01:32, Nodelist=cpu-e-131
      sleep-1
        Job 1349826: JobName=multisleep, State=COMPLETED, Elapsed=00:01:32, Nodelist=cpu-e-131
      sleep-2
        Job 1349827: JobName=multisleep, State=COMPLETED, Elapsed=00:01:32, Nodelist=cpu-e-131
  Collect step: False
  Working directory: 02-multisleep
  Scheduled at: 2018-04-15 21:20:23
  Script: submit.sh
  Skip: False
  Slurm pipeline environment variables:
    SP_DEPENDENCY_ARG: --dependency=afterok:1349824
    SP_FORCE: 0
    SP_NICE_ARG: --nice
    SP_ORIGINAL_ARGS:
    SP_SKIP: 0
Step 3: error
  1 step dependency: multisleep
    Dependent on 3 tasks emitted by the dependent step
    Summary: 3 jobs started by the dependent task, of which 3 (100.00%) are finished
    Dependent tasks:
      sleep-0
        Job 1349825: JobName=multisleep, State=COMPLETED, Elapsed=00:01:32, Nodelist=cpu-e-131
      sleep-1
        Job 1349826: JobName=multisleep, State=COMPLETED, Elapsed=00:01:32, Nodelist=cpu-e-131
      sleep-2
        Job 1349827: JobName=multisleep, State=COMPLETED, Elapsed=00:01:32, Nodelist=cpu-e-131
  1 task emitted by this step
    Summary: 1 job started by this task, of which 1 (100.00%) are finished
    Tasks:
      sleep
        Job 1349828: JobName=error, State=CANCELLED, Elapsed=00:00:00, Nodelist=None assigned
  Collect step: True
  Working directory: 03-error
  Scheduled at: 2018-04-15 21:20:23
  Script: submit.sh
  Skip: False
  Slurm pipeline environment variables:
    SP_DEPENDENCY_ARG: --dependency=afternotok:1349825?afternotok:1349826?afternotok:1349827
    SP_FORCE: 0
    SP_NICE_ARG: --nice
    SP_ORIGINAL_ARGS:
    SP_SKIP: 0
```

## slurm-pipeline-status-plot.py

```
usage: slurm-pipeline-status-plot.py [-h] [--nameRegex REGEX]
    [--html FILE.html] [--image FILE.png]
    status1.json [status2.json, ...] [status1.json [status2.json, ...] ...]

Create a plot showing the progress of a SLURM pipeline run (or runs).

positional arguments:
  status1.json [status2.json, ...]
    The JSON (files previously created by slurm-pipeline.py) to examine.

options:
  -h, --help            show this help message and exit
  --nameRegex REGEX     A regex with a single capture group to use to extract
      the name to associate with each status file. The regex will be
      matched against the status filenames. If not given, the parent directory
      of each specification status file will be used as its name.
  --html FILE.html      The (optional) output HTML file.
  --title TITLE         The overall plot title.
  --xtitle TITLE        The x-axis title.
  --ytitle TITLE        The y-axis title.
  --image FILE.png      An (optional) output image file. Output format is set
      according to file suffix.
```

## Examples

There are some simple examples in the `examples` directory:

### Word counting

`examples/word-count` (whose `specification.json` file is shown above) ties
together three scripts to find the most commonly used long words in three
texts (see the `texts` directory). The scripts are in the `scripts`
directory, and each of them reads and/or writes to files in the `output`
directory. You can run the example via

```sh
$ cd examples/word-count
$ make
rm -f output/*
../../bin/slurm-pipeline.py -s specification.json --scriptArgs texts/*.txt > status.json
```

This example is more verbose in its output than would be typical. Here's
what the `output` directory contains after `slurm-pipeline.py` completes:

```sh
$ ls -l output/
total 104
-rw-r--r--  1 terry  staff  2027 Oct 24 01:02 1-karamazov.long-words
-rw-r--r--  1 terry  staff  3918 Oct 24 01:02 1-karamazov.words
-rw-r--r--  1 terry  staff  3049 Oct 24 01:02 2-trial.long-words
-rw-r--r--  1 terry  staff  7904 Oct 24 01:02 2-trial.words
-rw-r--r--  1 terry  staff  1295 Oct 24 01:02 3-ulysses.long-words
-rw-r--r--  1 terry  staff  2529 Oct 24 01:02 3-ulysses.words
-rw-r--r--  1 terry  staff   129 Oct 24 01:02 MOST-FREQUENT-WORDS
-rw-r--r--  1 terry  staff   168 Oct 24 01:02 long-words-1-karamazov.out
-rw-r--r--  1 terry  staff   163 Oct 24 01:02 long-words-2-trial.out
-rw-r--r--  1 terry  staff   166 Oct 24 01:02 long-words-3-ulysses.out
-rw-r--r--  1 terry  staff   169 Oct 24 01:02 one-word-per-line.out
-rw-r--r--  1 terry  staff   318 Oct 24 01:02 summarize.out
```

The `MOST-FREQUENT-WORDS` file is the final output (produced by
`scripts/summarize.sh`). The `.out` files contain output from the
scripts. The `.words` and `.long-words` files are intermediates made by
scripts. The intermediate files of one step would normally be cleaned up
after being used by a subsequent step.

If you want to check the processing of this pipeline, run `make sh` to see
the same thing done in a normal UNIX shell pipeline. The output should be
identical to that in `MOST-FREQUENT-WORDS`.

The file `status.json` produced by the above command contains an updated
status:

```json
{
  "user": "sally",
  "firstStep": null,
  "force": false,
  "lastStep": null,
  "scheduledAt": 1482709202.618517,
  "scriptArgs": [
    "texts/1-karamazov.txt",
    "texts/2-trial.txt",
    "texts/3-ulysses.txt"
  ],
  "skip": [],
  "startAfter": null,
  "steps": [
    {
      "name": "one-per-line",
      "scheduledAt": 1482709202.65294,
      "script": "scripts/one-word-per-line.sh",
      "skip": false,
      "stdout": "TASK: 1-karamazov 22480\nTASK: 2-trial 26912\nTASK: 3-ulysses 25487\n",
      "taskDependencies": {},
      "tasks": {
        "1-karamazov": [
          22480
        ],
        "2-trial": [
          26912
        ],
        "3-ulysses": [
          25487
        ]
      }
    },
    {
      "dependencies": [
        "one-per-line"
      ],
      "name": "long-words",
      "scheduledAt": 1482709202.68266,
      "script": "scripts/long-words-only.sh",
      "skip": false,
      "stdout": "TASK: 3-ulysses 1524\n",
      "taskDependencies": {
        "1-karamazov": [
          22480
        ],
        "2-trial": [
          26912
        ],
        "3-ulysses": [
          25487
        ]
      },
      "tasks": {
        "1-karamazov": [
          29749
        ],
        "2-trial": [
          15636
        ],
        "3-ulysses": [
          1524
        ]
      }
    },
    {
      "collect": true,
      "dependencies": [
        "long-words"
      ],
      "name": "summarize",
      "scheduledAt": 1482709202.7016,
      "script": "scripts/summarize.sh",
      "skip": false,
      "stdout": "",
      "taskDependencies": {
        "1-karamazov": [
          29749
        ],
        "2-trial": [
          15636
        ],
        "3-ulysses": [
          1524
        ]
      },
      "tasks": {}
    }
  ]
}
```

Each step in the output specification has a `tasks` key that holds the taks
that the step has scheduled and a `taskDependencies` key that holds the
tasks the step depends on.  Note that the job ids will differ on your
machine due to the use of the `$RANDOM` variable to make fake job id
numbers in the pipeline scripts.

### Word counting, skipping the long words step

The `examples/word-count-with-skipping` example is exactly the same as
`examples/word-count` but provides for the possibility of skipping the step
that filters out short words. If you execute `make run` in that directory,
you'll see `slurm-pipeline.py` called with `--skip long-words`. The
resulting `output/MOST-FREQUENT-WORDS` output file contains typical
frequent (short) English words such as `the`, `and`, etc.

`make run` actually runs the following command:

```
$ slurm-pipeline.py -s specification.json --scriptArgs  texts/*.txt > output/status.json
```

If you look in `output/status.json` you'll see JSON that holds information
about the pipeline submission. This is all the information that was in the
specification file (`specification.json`) plus the submission time,
arguments, job ids, script output, etc. In a real scenario (i.e., when
SLURM is actually invoked, not in this trivial example) you can give this
status file to `slurm-pipeline-status.py` and it will print it in a
readable form and also look up (using the `sacct` command) the status of
all the SLURM jobs that were submitted by your pipeline scripts.

### Simulated BLAST

`examples/blast` simulates the running of
[BLAST](https://blast.ncbi.nlm.nih.gov/Blast.cgi) on a FASTA file. This is
done in 5 steps:

1. Write an initial message and timestamp to a log file (`pipeline.log`).
1. Split the FASTA file into smaller pieces.
1. Run a simulated BLAST script on each piece.
1. Collect the results, sort them on BLAST bit score, and write them to a file (`BEST-HITS`).
1. Write a final message to the log file.

All the action takes place in the same directory and all intermediate files
are removed along the way (uncomment the clean up `rm` line in
`2-run-blast.sh` and `3-collect.sh` and re-run to see the 200 intermediate
files).

### Simulated BLAST with --force and --firstStep

`examples/blast-with-force-and-skipping` simulates the running of
[BLAST](https://blast.ncbi.nlm.nih.gov/Blast.cgi) on a FASTA file, as
above.

In this case the step scripts take the values of `SP_FORCE` and
`SP_SKIP` into account.

As in the `examples/blast` example, all the action takes place in the same
directory, but intermediate files are not removed along the way. This
allows the step scripts to avoid doing work when `SP_SKIP=1` and to
detect whether their output already exists, etc. A detailed log of the
actions taken is written to `pipeline.log`.

The `Makefile` has some convenient targets: `run`, `rerun`, and `force`.
You can (and should) of course run `slurm-pipeline.py` from the command
line yourself, with and without `--force` and using `--firstStep` and
`--lastStep` to control which steps are skipped (i.e., receive `SP_SKIP=1`
in their environment) and which are not.

 Use `make clean` to get rid of the intermediate files.

### Two collect scripts

Another scenario you may want to deal with might involve a first phase of
data processing, followed by grouping the initial processing, and then a
second phase based on these groups. The `examples/double-collect` example
illustrates such a situation.

In this example, we imagine we've run an experiment and have data on 5
species: cat, cow, dog, mosquito, and tick. We've taken some sort of
measurement on each and stored the results into files `data/cat`,
`data/cow`, etc. In the first phase we want to add up all the numbers for
each species and print the number of observations and their total. In the
second phase we want to compute the sum and mean for two categories, the
vertebrates and invertebrates.

The categories are defined in a simple text file, `categories`:

The `0-start.sh` script emits a task name for each species (based on files
found in the `data` directory).  `1-species-count.sh` receives a species
name and does the first phase of counting, leaving its output in
`output/NAME.result` where `NAME` is the species name. The next script,
`2-category-emit.sh`, a collect script, runs when all the tasks given to
`1-species-count.sh` have finished. This step just emits a set of new task
names, `vertebrate` and `invertebrate` (taken from the `categories`
file). It doesn't do any work, it's just acting as a coordination step
between the end of the first phase and the start of the second. The next
step `3-category-count.sh`, receives a category name as its task and looks
in the `categories` file to see which phase one files it should
examine. The final output is written to `output/SUMMARY`:

    Category vertebrate:
    10 observations, total 550, mean 55.00

    Category invertebrate:
    5 observations, total 75, mean 15.00

Note that in this example in the first phase task names are species names
but in the second phase they are category names. In the first phase there
are 5 tasks being worked on (cat, cow, dog, mosquito, and tick) and in the
second phase just two (vertebrate, invertebrate). You can think of the
`2-category-emit.sh` script as absorbing the initial five tasks and
generating two new ones. The initial tasks are absorbed because the
`2-category-emit.sh` does not emit their names.

Use `make` to run the example. Then look at the files in the `output`
directory. Run `make clean` to clean up.

### A real-life example

A much more realistic example pipeline can be seen in another of my repos,
[neo-pipeline-spec](https://github.com/acorg/neo-pipeline). You wont be
able to run that example unless you have various bioinformatics tools
installed. But it should be instructive to look at the specification file
and the scripts. The scripts use `sbatch` to submit SLURM jobs, unlike
those (described above) in the `examples` directory. Note the treatment of
the various `SP_*` variables in the `sbatch.sh` scripts and also the
conditional setting of `--exclusive` depending on whether steps are being
skipped or not.

## Limitations

SLURM allows users to submit scripts for later execution. Thus there are
two distinct phases of operation: the time of scheduling and the later
time(s) of script excecution. When using `slurm-pipeline.py` it is
very important to keep this distinction in mind.

The reason is that `slurm-pipeline.py` only examines the output of
*scheduling* scripts for task names and job ids. If a scheduling script
calls `sbatch` to execute a later script, the output of that later script
(when it is finally run by SLURM) cannot be checked for `TASK: xxx 97322`
style output because `slurm-pipeline.py` is completely unaware of the
existence of that script. In other words, *all tasks and job dependencies
must be established at the time of scheduling.*

Normally this is not an issue, as many pipelines fall nicely into the model
used by `slurm-pipeline.py`. But sometimes it is necessary to write a step
script that performs a slow synchronous operation in order to emit tasks.
For example, you might have a very large input file that you want to
process in smaller pieces. You can use `split` to break the file into
pieces and emit task names such as `xaa`, `xab` etc, but you must do this
synchronously (i.e., in the step script, not in a script submitted to
`sbatch` by the step script to be executed some time later). This is an
example of when you would not emit a job id for a task, seeing as no
further processing is needed to complete the tasks (i.e., the `split` has
already run) and the next step in the pipeline can be run immediately.

In such cases, it may be advisable to allocate a compute node (using
[`salloc`](https://slurm.schedmd.com/salloc.html)) to run
`slurm-pipeline.py` on (instead of tying up a SLURM login node), or at
least to run `slurm-pipeline.py` using `nice`.

You might also find the
[simple SLURM loop](https://github.com/acorg/simple-slurm-loop) scripts
useful as a way to run a slurm-pipeline repeatedly, testing after each
iteration whether it should be rescheduled. The
[README](https://github.com/acorg/simple-slurm-loop/blob/master/README.md)
shows how you could do that using the `--printFinal` argument to
`slurm-pipeline-status.py`.

<a id="sbatch.py"></a>
## sbatch.py

`sbatch.py` allows you to quickly run simple _ad hoc_ SLURM pipelines from
the command line with no need to for any configuration files. You give it a
command to run and, optionally, tell it how many lines of standard input to
pass to each invocation. This is similar to what you can achieve by running
`GNU parallel` with the `--pipe` and `-N` arguments, except all the
invocations take place on compute nodes, as scheduled by SLURM.

`sbatch.py` prints a JSON summary of SLURM job ids to standard output
(unless `--noJobIds` is used). See below for output format details.

Output from each invocation of the command will appear in a file ending in
`.out` in the directory specified by `--dir`. These files are numbered
with leading zeroes so you can e.g., `cat out/*.out` and the order of the
collected output will correspond to the order of lines on standard
output. Use `--digits` to adjust the number of digits if the default
(currently 5) is not enough.

Error output from running the command will be placed in files ending in
`.err` in the `--dir` directory. These will normally be removed if the
command exits with status zero and the `.err` file is empty.  Use
`--keepErrorFiles` to unconditionally keep them.

An input file (or files) ending in `.in.bz2` will also be placed in the
`--dir` directory. These will also be removed once the command completes
without error. Use `--keepInputs` to unconditionally keep them. Use
`--uncompressed` to generate input files that are not compressed.  See also
the `--inline` option, below, to avoid making input files (though with a
caveat).

Any output from SLURM that is not a result of running your command will
appear in files ending in `.slurm`, which are also removed if no error
occurs and the file is empty. Use `--keepSlurmFiles` to unconditionally
keep them.

If `--dir` is not specified, a directory will be created (via
`tempfile.mkdtemp`) and its path printed.

By default, jobs are submitted to SLURM using a
[Job Array](https://slurm.schedmd.com/job_array.html) for efficient
scehduling of a potentially large number of jobs. This can be disabled with
the `--noArray` option (though see below).

Use `--dryRun` (or `-n`) to have `sbatch.py` write out the files it would
submit to SLURM via `sbatch` (these will be put into the directory
specified by `--dir`, each with a `.sbatch` suffix). If you like what you
see, you can then submit the job to SLURM, via `sbatch dir/initial.sbatch`
(where `dir` is the value you gave to the `--dir` option, or the temporary
directory `sbatch.py` makes for you if you don't specify one).

You can optionally specify commands that should be scheduled to run after
all of standard input is processed, using the `--then` and (for error
handling) `--else` options, or `--finally` for commands that should be run
at the end, irrespective of the exit status of the initial commands.  This
is intended to make it easy to do the rough equivalent of a shell command
line, but the processing starts by (optionally) splitting standard input
and the downstream commands are scheduled by SLURM instead of running on
the same host with their I/O tied together via local UNIX kernel
pipelines. Your downstream commands can make use of the earlier processing
because the output files are predictably named and sorted. You can use
`--prefix` to give output files a unique prefix if necessary.

If standard input starts with a (single) header line (e.g., is a CSV or TSV
file), use `--header` to tell `sbatch.py` to put an identical header at the
start of each input file in the case that multiple jobs are scheduled.

The helper script `remove-repeated-headers.py` can be used to remove
repeated headers from output files if these each contain a header. This
allows you to `cat` all output files into `remove-repeated-headers.py` to
produce a single output file with a single header line (this may of course
differ from the header in standard input, if any).

Unless invoked with `--noJobIds`, `sbatch.py` prints a JSON summary of
SLURM jobs ids, as in the following example:

    {
      "initial": [
        4555549,
        4555550,
        4555551,
        4555552
      ],
      "then": [
        4555553,
        4555554
      ],
      "else": [
        4555555
      ],
      "finally": [
        4555556
      ],
      "all": [
        4555549,
        4555550,
        4555551,
        4555552,
        4555553,
        4555554,
        4555555,
        4555556
      ]
    }

It may be useful to save this output to a file for later use with commands
such as `sacct`, `squeue`, and `scancel`. This can be very conveniently
done if you install [jq](https://stedolan.github.io/jq/). For example, if
you had stored the above into a file called `jobids.json` (and you have a
POSIX shell, such as bash), you could run one of the following:

```sh
$ sacct  --jobs $(jq '.all | join(",")' jobids.json | tr -d \")
$ squeue --jobs $(jq '.all | join(",")' jobids.json | tr -d \")
$ scancel       $(jq '.all | join(",")' jobids.json | tr -d \")
```

Or, to launch a second command via `sbatch.py`, starting only afer the last
of the `then` jobs (`4555554` in the above example) completes successfully:

```sh
$ sbatch.py --afterOk $(jq '.then[-1]' jobids.json) ...
```

See `sbatch.py --help` for additional usage options (e.g., to specify
memory, CPUs, job names, time, SLURM partition, etc).

This script has the limitation that the SLURM resources requested for all
the initial commands will also be requested for any `--then`, `--else`, or
`--finally` commands.

### Example sbatch.py usage

#### Dummy input data

To create some dummy input data, use `seq` to print numbers

```sh
$ seq 5
1
2
3
4
5

$ seq 1000000 | wc -l
1000000
```

#### Dummy work

The commands below send numbers on standard input to `gzip` but throw the
`gzip` output away. E.g.

```sh
$ seq 10000 | gzip > /dev/null
```

#### Dummy output processing

Some examples will use use `awk` to add up numbers. E.g., add the first
10,000 natural numbers:

```sh
$ seq 10000 | awk '{sum += $1} END {print sum}'
50005000
```

### Using parallel on a compute node

First, here's a command that can simply be run with
[GNU parallel](https://www.gnu.org/software/parallel/) on a single compute
node (nothing to do with SLURM).

```sh
# Get a compute node with 32 cores.
$ srun --pty --cpus-per-task 32 --mem=8G bash -i

# This takes about 30 seconds on the node.
$ seq 10000 | parallel --progress 'seq {} | gzip > /dev/null'
```

### Using sbatch.py

We can use `sbatch.py` to do the above, but splitting the input into chunks
and running each chunk via `parallel` on a separate compute node:

```sh
$ seq 10000 | sbatch.py --dir out --linesPerJob 1000 \
              "parallel 'seq {} | gzip > /dev/null'"
```

Use `--makeDoneFiles` to create empty `.done` files in the `--dir`
directory when jobs finish (successfully).

Use `--dryRun` (or `-n`) to tell `sbatch.py` not to run `sbatch` but just
to write out the various files that could later be given to `sbatch`:

```sh
$ seq 10000 | sbatch.py --dir out --linesPerJob 1000 --dryRun \
              "parallel 'seq {} | gzip > /dev/null'"
```

To see the input files that were used, use `--keepInputs`, then you'll find
`.in.bz2` files in the `--dir` directory (with no `.bz2` suffix if you use
`--uncompressed`).

Use `--noArray` to create separate `.sbatch` command scripts for each job,
and `--inline` to use "here" documents in the scripts, to save on making
input files. **Note** that using `--noArray` will mean more calls to
`sbatch` to submit jobs. This can be a bad idea, so `--noArray` should be
used with care, preferably after running with `--dryRun` to see how many
`sbatch` scripts and input files are created.

#### Post-processing with --then

You can use `--then` to schedule a command to be run after everything
completes (successfully).

So we change the original processing to also echo the number (see `echo {}`
below), and when everything is done, `cat` all the result files, add the
numbers, and put the sum into a file called `RESULT.`

```sh
$ seq 10000 | sbatch.py --dir out --linesPerJob 1000 \
              "parallel 'seq {} | gzip > /dev/null; echo {}'" \
              --then 'cat out/initial*.out | awk "{sum += \$1} END {print sum}" > RESULT'
$ cat RESULT
50005000
```

Or add the numbers, send the result into Slack, and then do some clean-up:

```sh
seq 10000 | sbatch.py --dir out --linesPerJob 1000 \
              "parallel 'seq {} | gzip > /dev/null; echo {}'" \
              --then 'cat out/initial*.out | awk "{sum += \$1} END {print sum}" > RESULT' \
              --then "tell-slack.py '$USER, your job has finished (total = $(cat RESULT)).'" \
              --then 'rm -r out' \
              --else "tell-slack.py '$USER, your job failed. Have a look in $(pwd)/out'"
```

#### Error post-processing with --else

Use `--else` for error handling (may be repeated):

```sh
seq 10000 | sbatch.py --dir out --linesPerJob 1000 \
              "parallel 'seq {} | gzip > /dev/null; echo {}'" \
              --then 'cat out/initial*.out | awk "{sum += \$1} END {print sum}" > RESULT' \
              --then "tell-slack.py '$USER, your job has finished (total = $(cat RESULT)).'" \
              --else "tell-slack.py '$USER, your job failed. Have a look in $(pwd)/out'"
```

#### Final post-processing with --finally

Add unconditional final commands via `--finally` (may also be repeated):

```sh
$ seq 10000 | sbatch.py --dir out --linesPerJob 1000 \
              "parallel 'seq {} | gzip > /dev/null; echo {}'" \
              --then 'cat out/initial*.out | awk "{sum += \$1} END {print sum}" > RESULT' \
              --finally 'rm -r out' \
              --finally 'echo Run finished at $(date) > DONE'
```


## Development

If you would like to work on the code or just to run the tests after
cloning the repo, you'll probabaly want to install some development
modules. The easiest way is to just

```sh
$ pip install -r requirements-dev.txt
```

though you might want to be more selective (e.g., you don't need to install
Twisted unless you plan to run `make tcheck` to use their `trial` test
runner).

### Running tests

Any/all of the following should work:

```sh
$ tox # To run the tests on multiple Python versions (see tox.ini).
$ make check  # Run tests with pytest.
$ make tcheck # If you "pip install Twisted" first.
$ python -m discover -v  # If you run "pip install discover" first.
```

## TODO

* Make it possible to pass the names (or at least the prefix) of the
  environment variables (currently hard-coded as `SP_ORIGINAL_ARGS` and
  `SP_DEPENDENCY_ARG`, etc.) to the `SlurmPipeline` constructor.
* (Possibly) make it possible to pass a regex for matching task name and
  job id lines in a script's `stdout` to the `SlurmPipeline` constructor
  (instead of using the currently hard-coded `TASK: name
  [jobid1 [jobid2 [...]]]`).

## Contributors

This code was originally written (and is maintained) by
[Terry Jones (@terrycojones)](https://github.com/terrycojones).

Contributions have been received from:

* [akug](https://github.com/akug)
* [bestdevev](https://github.com/bestdevev)
* [Eric Müller (@muffgaga)](https://github.com/muffgaga)
* [healther](https://github.com/healther)
* [ldynia](https://github.com/ldynia)
* [schmitts](https://github.com/schmitts)
* [TaliVeth](https://github.com/TaliVeith)

Pull requests very welcome!
