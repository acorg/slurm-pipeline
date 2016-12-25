# slurm-pipeline

A Python class for scheduling and examining
[SLURM](http://slurm.schedmd.com/)
([wikipedia](https://en.wikipedia.org/wiki/Slurm_Workload_Manager)) jobs.

Runs under Python 2.7, 3.5, and [pypy](http://pypy.org/).

## Scripts

The `bin` directory of this repo contains two Python scripts:

* `slurm-pipeline.py` schedules programs to be run in an organized pipeline
  fashion on a Linux cluster that uses SLURM as a workload manager. Here
  "pipeline" means with an understanding of possibly complex inter-program
  dependencies. `slurm-pipeline.py` must be given a JSON job specification
  (see below). It prints a corresponding JSON status that contains the
  original specification plus information about the scheduling (times, job
  ids, etc).
* `slurm-pipeline-status.py` must be given a specification status (as
  produced by `slurm-pipeline.py`) and prints a summary of the status
  including job status (obtained from `squeue`). It can also be used to
  print a list of unfinished jobs (useful for cancelling the jobs of a
  running specification) or a list of the final jobs of a specification
  (useful for making sure that jobs scheduled in a subsequent run of
  `slurm-pipeline.py` do not begin until the given specification has
  finished). See below for more information.

## Specification

A pipeline run is schedule according to a specification file in JSON format
which is given to `slurm-pipeline.py`. Several examples of these can be
found under [`examples`](examples). Here's the one from
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

The specification above contains almost everything you need to know to set
up your own pipeline, though you of course still have to write the scripts.

## Steps

A pipeline run is organized into a series of conceptual *steps*. These are
scheduled in the order they appear in the specification file. The actual
running of the programs involved will occur later, in an order that will
depend on how long earlier programs take to complete and on dependencies.

Each step must contain a `name` key. Names must be unique.

Each step must also contain a `script` step. This gives the file name of a
program to be run. The file must exist at the time of scheduling and must
be executable.

Optionally, a step may have a `dependencies` key which gives a list of step
names upon which the step depends. Any dependency named must have already
been defined in the specification.

Optionally, a script may specify `collect` with a `true` value. This will
cause the script to be run when all the *tasks* (see below) started by
earlier dependent steps have completed.

The full list of specification directives can be found below.

## Tasks

A step script may emit one or more *task*s. It does this by writing lines
such as `TASK: xxx 39749 39750` to its standard output. This indicates that
a task named `xxx` has been scheduled and that two SLURM jobs (with ids
`39749` and `39750`) will be run to complete whatever work is needed for
the task.

A task name may be emitted multiple times by the same script.

Any other output from a step script is ignored (it is however stored in the
specification - see TODO, below).

When a step depends on an earlier step (or steps), its `script` will be
called with a single argument: the name of each task emitted by the earlier
script (or scripts). If a step depends on multiple earlier steps that each
emit the same task name, the script will only be called once, with that
task name as an argument, after all the jobs from all the dependent steps
have finished.

So, for example, a step that starts the processing of 10 FASTA files could
emit the file names (as task names), which will cause ten subsequent
invocations of any dependent step's script.

If a script emits `TASK: xxx` with no job id(s), the named task will be
passed along the pipeline but dependent steps will not need to wait for any
SLURM job to complete before being invoked. This is useful when a script
does its work synchronously (i.e., without scheduling via SLURM).

If a step specification uses `"collect": true`, its script will only be
called once. The script's arguments will be the names of all tasks emitted
by the steps it depends on.

Steps that have no dependencies are called with whatever command-line
arguments are given to `slurm-pipeline.py` (apart from the specification
file, of course).

So for example, given the specification above,

```sh
$ cd examples/word-count
$ slurm-pipeline.py -s specification.json texts/*.txt > status.json
```

will cause `one-word-per-line.sh` from the first specification step to be
called with the files matching `texts/*.txt`. The script of the second
script (`long-words-only.sh`) will be invoked multiple times (once for each
`.txt` file). The script will be invoked with the task names emitted by
`one-word-per-line.sh` (the names can be anything desired, and in this case
they are the file names without the `.txt` suffix). The (`collect`) script
of the third step (`summarize.sh`) will be called with the names of *all*
the tasks emitted by its dependency (the second script).

The standard input of invoked scripts is closed.

The file `status.json` produced by the above will contain the original
specification, updated to contain information about the tasks that have
been scheduled, their SLURM job ids, script output, timestamps, etc. See
the `word-count` example below for sample output.

## slurm-pipeline.py options

`slurm-pipeline.py` accepts the following options:

* `--specification filename`: as described above.
* `--force`: Will cause `SP_FORCE` to be set in the environment of step
  scripts with a value of `1`. It is up to the individual scripts to notice
  this and act accordingly. If `--force` is not used, `SP_FORCE` will be
  set to `0`.
* `--firstStep step-name`: Step scripts are always run with an environment
  variable called `SP_SIMULATE`. Normally this will be set to `0` for all
  steps. Sometimes though, you may want to start a pipeline from one of its
  intermediate steps and not re-do the work of earlier steps. Using
  `--firstStep step-name` Will cause `step-name` to be run with
  `SP_SIMULATE=0` in its environment. Earlier steps in the pipeline will be
  run with `SP_SIMULATE=1`. It is up to the scripts to decide how to act
  when `SP_SIMULATE=1`.
* `--lastStep step-name`: Corresponds to `--firstStep`, except it turns
  simulation back on (i.e., sets `SP_SIMULATE=1`) after the named step.
  Note that `--firstStep` and `--lastStep` may specify the same step (to
  just run that step) and that `--firstStep` may be given without also
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

Note that all script steps are *always* executed, including when
`--firstStep` or `--skip` are used. It is up to the scripts to decide what
to do.

### Simulating versus skipping

Scripts that are simulating will normally want to emit task names, as
usual, but without doing any work *because the work has already been done
in a previous run*. In that case they can emit the task name with no job
id, so the later steps in the pipeline will not need to wait.  In
simulation (as opposed to skipping), the script has already done its work
(its output file(s) are already in place) and simply does nothing.

Skipping refers to when a step is really no longer in the pipeline. A step
that skips will normally just want to pass along its input to its output
unchanged. The step still needs to be run so that it can make sure that its
subsequent step(s) do not fail. It can be more convenient to add `"skip":
true` to a specification file to completely get rid of a step rather than
changing the subsequent step to take its input from the location the
stepped script would use. Being able to use `--skip step-name` on the
command line provides an easy way to skip a step.

In summary, a simulated step doesn't do anything because its work was
already done on a previous run, but a skipped step pretends it's not there
at all (normally by copying its input to its output unchanged). The skipped
step *never* does anything, the simulated step has *already* done its work.

### Why are all scripts always executed?

It is cleaner to implement partial pipeline operation as above because it
would otherwise be unclear how to invoke intermediate step scripts if the
earlier scripts had not emitted any task names.  Simulated steps may still
want to log the fact that they were run in simulated mode, etc. And it's
conceptually easier to know that `slurm-pipeline.py` always runs all
pipeline step scripts (see the Separation of concerns section below).

## Specification file directives

You've already seen most of the specification file directives above. Here's
the full list:

* `name`: the name of the step (required).
* `script`: the script to run (required).
* `cwd`: the directory to run the script in. If no directory is given, the
   script will be run in the directory where you invoke
   `slurm-pipeline.py`.
* `collect`: for scripts that should run only when all tasks from all their
  prerequisites have completed.
* `dependencies`: a list of previous steps that a step depends on.
* `error step`: if `true` the step script will only be run if one of its
  dependencies fails.
* `skip`: if `true`, the step script will be run with `SP_SKIP=1` in its
  environment. Otherwise, `SP_SKIP` will always be set and will be `0`.

## Step script environment variables

The following environment variables are set when a step's script is
exectued:

* `SP_ORIGINAL_ARGS` contains the (space-separated) list of arguments
  originally passed to `slurm-pipeline.py`. Most scripts will not need to
  know this information, but it might be useful. Scripts that have no
  dependencies will be run with these arguments on the command line too.
  Note that if an original command-line argument contained a space, and you
  split `SP_ORIGINAL_ARGS` on spaces, you'll have two strings instead of
  one.
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
  invokes [`sbatch`](https://slurm.schedmd.com/sbatch.html) to guarantee
  that the execution of the script does not begin until after the tasks
  from all dependent steps have finished successfully.

    The canonical way to use `SP_DEPENDENCY_ARG` in a step script is as
    follows:

    ```sh
    jobid=`sbatch -n 1 $SP_DEPENDENCY_ARG submit.sh $task | cut -f4 -d' '`
    echo "TASK: $task $jobid"
    ```

    This calls `sbatch` with the dependency argument (if any) and
    simultaneously gets the job id from the `sbatch` output (`sbatch` prints a
    line like `Submitted batch job 3779695`) and the `cut` in the above pulls
    out just the job id. The task name is then emitted, along with the job id.

## Separation of concerns

`slurm-pipeline.py` doesn't interact with SLURM at all. Actually, the
*only* thing it knows about SLURM is how to construct a dependency argument
for `sbatch` (so it could in theory be generalized to support other
workload managers).

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

* `--specification filename`: must contain the status specification printed
    by `slurm-pipeline.py`.
* `--squeueArgs'`: A list of arguments to pass to squeue (this must include
    the squeue command itself). If not specified, the user's login name will be
    appended to `squeue -u`.
* `--printUnfinished`: If specified, just print a list of job ids that have not
    yet finished. This can be used to cancel a job, via e.g.,
    
    ```sh
    $ slurm-pipeline-status.py --specification spec.json --printUnfinished  | xargs -r scancel
    ```
* `--printFinal`: If specified, just print a list of job ids issued by the
    final steps of a specification. This can be used with the
    `--startAfter` option to `slurm-pipeline.py` to make it schedule a
    different specification to run only after the given specification
    finishes. E.g.,
    
    ```sh
    # Start a first specification and save its status:
    $ slurm-pipeline.py --specification spec1.json > spec1-status.json

    # Start a second specification once the first has finished (this assumes you shell is bash):
    $ slurm-pipeline.py --specification spec2.json --startAfter $(slurm-pipeline-status.py --specification spec1-status.json --printFinal) > spec2-status.json
    ```

If neither `--printUnfinished` nor `--printFinal` is given,
`slurm-pipeline-status.py` prints a detailed summary of the status of the
specification it is given. Example output might resemble the following:

```sh
$ slurm-pipeline.py --specification spec1.json > status.json
$ slurm-pipeline-status.py --specification status.json
Scheduled at: 2016-12-10 14:20:58
Scheduling arguments:
  First step: panel
  Force: False
  Last step: None
  Script arguments: <None>
  Skip: <None>
  Start after: <None>
5 jobs emitted in total, of which 4 (80.00%) are finished
Step summary:
  start: no jobs emitted
  split: no jobs emitted
  blastn: 3 jobs emitted, 3 (100.00%) finished
  panel: 1 job emitted, 1 (100.00%) finished
  stop: 1 job emitted, 0 (0.00%) finished
Step 1: start
  No dependencies.
  No tasks emitted by this step
  Working directory: 00-start
  Scheduled at: 2016-12-10 14:20:59
  Script: 00-start/start.sh
  Simulate: True
  Skip: False
Step 2: split
  1 step dependency: start
    Dependent on 0 tasks emitted by the dependent step
  3 tasks emitted by this step
    0 jobs started by these tasks
    Tasks:
      chunk-aaaaa
      chunk-aaaab
      chunk-aaaac
  Working directory: 01-split
  Scheduled at: 2016-12-10 14:21:04
  Script: 01-split/sbatch.sh
  Simulate: True
  Skip: False
Step 3: blastn
  1 step dependency: split
    Dependent on 3 tasks emitted by the dependent step
    0 jobs started by the dependent tasks
    Dependent tasks:
      chunk-aaaaa
      chunk-aaaab
      chunk-aaaac
  3 tasks emitted by this step
    3 jobs started by this task, of which 3 (100.00%) are finished
    Tasks:
      chunk-aaaaa
        Job 4416231: Finished
      chunk-aaaab
        Job 4416232: Finished
      chunk-aaaac
        Job 4416233: Finished
  Working directory: 02-blastn
  Scheduled at: 2016-12-10 14:22:02
  Script: 02-blastn/sbatch.sh
  Simulate: True
  Skip: False
Step 4: panel
  1 step dependency: blastn
    Dependent on 3 tasks emitted by the dependent step
    3 jobs started by the dependent task, of which 3 (100.00%) are finished
    Dependent tasks:
      chunk-aaaaa
        Job 4416231: Finished
      chunk-aaaab
        Job 4416232: Finished
      chunk-aaaac
        Job 4416233: Finished
  1 task emitted by this step
    1 job started by this task, of which 1 (100.00%) are finished
    Tasks:
      panel
        Job 4417615: Finished
  Working directory: 03-panel
  Scheduled at: 2016-12-10 14:22:02
  Script: 03-panel/sbatch.sh
  Simulate: False
  Skip: False
Step 5: stop
  1 step dependency: panel
    Dependent on 1 task emitted by the dependent step
    1 job started by the dependent task, of which 1 (100.00%) are finished
    Dependent tasks:
      panel
        Job 4417615: Finished
  1 task emitted by this step
    1 job started by this task, of which 0 (0.00%) are finished
    Tasks:
      stop
        Job 4417616: Status=R Time=4:27 Nodelist=cpu-3
  Working directory: 04-stop
  Scheduled at: 2016-12-10 14:22:02
  Script: 04-stop/sbatch.sh
  Simulate: False
  Skip: False
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
../../bin/slurm-pipeline.py -s specification.json texts/*.txt > status.json
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
  "scheduledAt": 1477302666.246372,
  "steps": [
    {
      "name": "one-per-line",
      "scheduledAt": 1477302666.271217,
      "script": "scripts/one-word-per-line.sh",
      "stdout": "TASK: 1-karamazov 20132\nTASK: 2-trial 3894\nTASK: 3-ulysses 13586\n",
      "taskDependencies": {},
      "tasks": {
        "1-karamazov": [
          20132
        ],
        "2-trial": [
          3894
        ],
        "3-ulysses": [
          13586
        ]
      }
    },
    {
      "dependencies": [
        "one-per-line"
      ],
      "name": "long-words",
      "scheduledAt": 1477302666.300458,
      "script": "scripts/long-words-only.sh",
      "stdout": "TASK: 3-ulysses 31944\n",
      "taskDependencies": {
        "1-karamazov": [
          20132
        ],
        "2-trial": [
          3894
        ],
        "3-ulysses": [
          13586
        ]
      },
      "tasks": {
        "1-karamazov": [
          27401
        ],
        "2-trial": [
          13288
        ],
        "3-ulysses": [
          31944
        ]
      }
    },
    {
      "collect": true,
      "dependencies": [
        "long-words"
      ],
      "name": "summarize",
      "scheduledAt": 1477302666.319238,
      "script": "scripts/summarize.sh",
      "stdout": "",
      "taskDependencies": {
        "1-karamazov": [
          27401
        ],
        "2-trial": [
          13288
        ],
        "3-ulysses": [
          31944
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
freqeunt (short) English words such as `the`, `and`, etc.

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

### A more realistic example

Another example can be seen in another of my repos,
[eske-pipeline-spec](https://github.com/acorg/eske-pipeline-spec). You wont
be able to run that example unless you have various bioinformatics tools
installed. But it may be instructive to look at the specification file and
the scripts. The scripts use `sbatch`, unlike those (described above) in
the `examples` directory.

## Limitations

SLURM allows users to submit scripts for later execution. Thus there are
two distinct phases of operation: the time of scheduling and the later
time(s) of script excecution. When using `slurm-pipeline.py` it is
important to understand this distinction.

The reason is that `slurm-pipeline.py` only examines the output of
scheduling scripts for task names and job ids. If a scheduling script calls
`sbatch` to execute a later script, the output of that later script cannot
be checked for `TASK: xxx 97322` style output because `slurm-pipeline.py`
is completely unaware of the existence of that script. Thus all tasks and
job dependencies must be established at the time of scheduling.

Normally this is not an issue, as many pipelines fall nicely into the model
used by `slurm-pipeline.py`. But sometimes it is necessary to write a step
script that performs a slow synchronous operation in order to emit
tasks. For example, you might have a very large input file that you want to
process in smaller pieces. You can use `split` to break the file into
pieces and emit task names such as `xaa`, `xab` etc, but you must do this
synchronously (i.e., in the step script, not in a script submitted to
`sbatch` by the step script to be executed some time later).

In such cases, it may be advisable to allocate a compute node (using
[`salloc`](https://slurm.schedmd.com/salloc.html)) to run
`slurm-pipeline.py` on (instead of tying up a SLURM login node), or at
least to run `slurm-pipeline.py` using `nice`.

## TODO

* Make it possible to pass the names (or at least the prefix) of the two
  environment variables (currently hard-coded as `SP_ORIGINAL_ARGS` and
  `SP_DEPENDENCY_ARG`) to the `SlurmPipeline` constructor.
* (Possibly) make it possible to pass a regex for matching task name and
  job id lines in a script's stdout to the `SlurmPipeline` constructor
  (instead of using the currently hard-coded `TASK: name
  [jobid1 [jobid2 [...]]]`).
