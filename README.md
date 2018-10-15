# slurm-pipeline

A [Python](https://www.python.org) class for scheduling and examining
[SLURM](http://slurm.schedmd.com/)
([wikipedia](https://en.wikipedia.org/wiki/Slurm_Workload_Manager)) jobs.

Runs under Python 2.7, 3.5, 3.6, 3.7-dev, and [pypy](http://pypy.org/)
[Change log](CHANGELOG.md).
[![Build Status](https://travis-ci.org/acorg/slurm-pipeline.svg?branch=master)](https://travis-ci.org/acorg/slurm-pipeline)

Funding for the development of this package comes from:

* the European Union Horizon 2020 research and innovation programme,
  [COMPARE](http://www.compare-europe.eu/) grant (agreement No. 643476),
  and
* U.S. Federal funds from the Department of Health and Human Services;
  Office of the Assistant Secretary for Preparedness and Response;
  Biomedical Advanced Research and Development Authority, under Contract
  No. HHSO100201500033C

## Installation

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

# Install dependencies.
$ pip install -r requirements.txt

# Install.
$ python setup.py install
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
* `slurm-pipeline-version.py` prints the version number.

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
  variable called `SP_SIMULATE`. Normally this will be set to `0` for all
  steps. Sometimes though, you may want to start a pipeline from one of its
  intermediate steps and not re-do the work of earlier steps. If you specify
  `--firstStep step-name`, the steps before `step-name` will be invoked with
  `SP_SIMULATE=1` in their environment. It is up to the scripts to decide how
  to act when `SP_SIMULATE=1`.
* `--lastStep step-name`: Corresponds to `--firstStep`, except it turns
  simulation back on (i.e., sets `SP_SIMULATE=1`) for steps after the named
  step. Note that `--firstStep` and `--lastStep` may specify the same step
  (to just run that step) and that `--firstStep` may be given without also
  giving `--lastStep`.
* `--skip`: Used to tell `slurm-pipeline.py` to tell a step script that it
  should be skipped. In this case the script should act as though it is not
  even in the pipeline. Commonly this will mean just taking its expected
  input file and copying it unchanged to the place where it normally puts
  its output. This allows the next script in the pipeline to run without
  error. This argument may be repeated to skip multiple steps. See also the
  `skip` directive that can be used in a specification file for more
  permanent disabling of a script step.
* `--startAfter`: Specify one or more SLURM job ids that must be allowed to
  complete (in any state - successful or in error) before the initial steps
  of the current specification are allowed to run. If you have saved the
  output of a previous `slurm-pipeline.py` run, you can use
  `slurm-pipeline-status.py` to output the final job ids of that previous
  run and give those job ids to a subsequent invocation of
  `slurm-pipeline.py` (see `slurm-pipeline-status.py` below for an
  example).
* `--scriptArgs`: Specify arguments that should appear on the command line
  when initial step scripts are run. The initial steps are those that do
  not have any dependencies.

Note that all script steps are *always* executed, including when
`--firstStep` or `--skip` are used. See below for the reasoning behind
this.  It is up to the scripts to decide what to do (based on the `SP_*`
environment variables) in those cases.

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
isolaion. In a normal run with no simulated or skipped steps, steps emit
task names that are passed through the pipeline to subsequent steps. If the
earlier steps are not run, `slurm-pipeline.py` cannot know what task
arguments to pass to the scripts for those later steps.

It is also conceptually easier to know that `slurm-pipeline.py` always runs
all pipeline step scripts, whether or not they are simulating or being
skipped (see <a href="#separation">Separation of concerns</a> below).
Simulated steps may want to log the fact that they were run in simulated
mode, etc.

### Simulating versus skipping

Scripts that are simulating will normally want to emit task names, as
usual, but without doing any work *because the work has already been done
in a previous run*. In that case they can emit the task name with no job
id, so the later steps in the pipeline will not need to wait.  In
simulation (as opposed to skipping), the script has already done its work
(its output file(s) are already in place) and simply does nothing.

Skipping refers to when a step is really no longer in the pipeline. A step
that skips will normally just want to pass along its input to its output
unchanged. I.e., the step must act as though it were not in the pipeline.
The step still needs to be run so that it can make sure that subsequent
steps do not fail. It can be more convenient to add `"skip": true` to a
specification file to completely get rid of a step rather than changing the
subsequent step to take its input from the location the stepped script
would use. Using `--skip step-name` on the command line also provides an
easy way to skip a step.

In summary, a simulated step doesn't do anything because its work was
already done on a previous run, but a skipped step pretends it's not in the
pipeline at all (typically by just copying or moving its input to its
output unchanged). The skipped step *never* does any real work, whereas the
simulated step has *already* done its work.

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

The following environment variables are set when a step's script is
executed:

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
* `SP_SIMULATE` will be set to `1` if the step should be simulated, and `0`
  if not. See the description of `--firstStep` and `--lastStep` above for
  how to turn simulation on and off. In simulating a step, a script should
  just emit its task name(s) as usual, but without job ids. The presumption
  is that a pipeline is being re-run and that the work that would normally
  be done by a step that is now being simulated has already been done. A
  script that is called with `SP_SIMULATE=1` might want to check that its
  regular output does in fact already exist, but there's no need to exit if
  not. The entire pipeline might be simulated, in which case there is no
  issue if intermediate results are never computed.
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
  Simulate: False
  Skip: False
  Slurm pipeline environment variables:
    SP_FORCE: 0
    SP_NICE_ARG: --nice
    SP_ORIGINAL_ARGS:
    SP_SIMULATE: 0
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
  Simulate: False
  Skip: False
  Slurm pipeline environment variables:
    SP_DEPENDENCY_ARG: --dependency=afterok:1349824
    SP_FORCE: 0
    SP_NICE_ARG: --nice
    SP_ORIGINAL_ARGS:
    SP_SIMULATE: 0
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
  Simulate: False
  Skip: False
  Slurm pipeline environment variables:
    SP_DEPENDENCY_ARG: --dependency=afternotok:1349825?afternotok:1349826?afternotok:1349827
    SP_FORCE: 0
    SP_NICE_ARG: --nice
    SP_ORIGINAL_ARGS:
    SP_SIMULATE: 0
    SP_SKIP: 0
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
      "simulate": false,
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
      "simulate": false,
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
      "simulate": false,
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

`examples/blast-with-force-and-simulate` simulates the running of
[BLAST](https://blast.ncbi.nlm.nih.gov/Blast.cgi) on a FASTA file, as
above.

In this case the step scripts take the values of `SP_FORCE` and
`SP_SIMULATE` into account.

As in the `examples/blast` example, all the action takes place in the same
directory, but intermediate files are not removed along the way. This
allows the step scripts to avoid doing work when `SP_SIMULATE=1` and to
detect whether their output already exists, etc. A detailed log of the
actions taken is written to `pipeline.log`.

The `Makefile` has some convenient targets: `run`, `rerun`, and `force`.
You can (and should) of course run `slurm-pipeline.py` from the command
line yourself, with and without `--force` and using `--firstStep` and
`--lastStep` to control which steps are simulated (i.e., receive
`SP_SIMULATE=1` in their environment) and which are not.

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
simulated or not.

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

## Development

If you like to work on the code or just to run the tests having cloned the
repo, you'll probabaly want to install some development modules. The
easiest way is to just

```sh
$ pip install -r requirements-dev.txt
```

though you might want to be more selective (e.g., you don't need to install
Twisted unless you plan to run `make tcheck` to use their `trial` test
runner).

### Running tests

Any/all of the following should work for you:

```sh
$ tox # To run the tests on multiple Python versions (see tox.ini).
$ make check
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
