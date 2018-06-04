## Version 3.0.1 - Juna 4, 2018

Added `env PYTHONPATH=../..` to all example Makefiles.

## Version 3.0.0

* Added `--scriptArgs` to `slurm-pipeline.py` to formalize giving arguments
  on the command line that should be passed to initial step scripts (i.e.,
  those that have no dependencies).  This prevents the possibility of
  putting unrecognized arguments (like `--startStep`) on the command line
  which are then passed to the script steps.

## Version 2.0.11 - April 16, 2018

Added Travis CI build messaging to IRC.

## Version 2.0.10 - April 16, 2018

Updated funding acknowledgements in README.md

## Version 2.0.9 - April 16, 2018

Added "error step" setting to per-step information printed by
`slurm-pipeline-status.py`.

## Version 2.0.8 - April 15, 2018

Added JobName to list of default job status fields printed by
`slurm-pipeline-status.py`.

## Version 2.0.7 - April 15, 2018

Added printing of SP_* environment variables to per-step output of
`slurm-pipeline-status.py`.

## Version 2.0.6 - April 15, 2018

Added "Collect step:" to per-step output of `slurm-pipeline-status.py`.

## Version 2.0.5 - April 15, 2018

### sacct now used instead of squeue

This change is not backward-compatible with earlier versions, hence the
major version number change.

* SLURM job status reporting was changed to use `sacct` rather than
  `squeue` as a result of a pull request submitted by
  [healther](https://github.com/healther).  This has the advantage of being
  able to show status information for jobs that have completed.
* The `squeueArgs` command line option to `slurm-pipeline.py` was removed.
* A `fieldNames` argument was added to `slurm-pipeline-status.py`. This can
  be used to specify what job fields you want to see in the summary
  output. The default is `State`, `Elapsed`, and `Nodelist`. You can set
  `SP_STATUS_FIELD_NAMES` to a comma-separated list of job fields to set
  your own default preference.  See `man sacct` for the full list of field
  names.

Other changes

* It is now possible to specify `error step: true` for a step that has no
  dependencies. This used to be flagged as an error, but it makes sense to
  allow it as the user might use `--startAfter` on the command line, and
  the jobs which the no-dependency step is suppose to start after may fail.
* The `Makefile` now uses `pycodestyle` instead of `pep8` to check Python
  style (this is just a new name for the `pep8` tool).
* An `--output` option was added to `slurm-pipeline.py` to allow the
  specification of an output file for the JSON status. The default is to
  print it to standard output.
* `SP_DEPENDENCY_ARG` is now set for all steps that don't have dependencies
  if `--startAfter` is used when invoking `slurm-pipeline.py`.
* The all-step summary section of the `slurm-pipeline-status.py` output is
  slightly improved, to list an overall count of jobs started and finished.
