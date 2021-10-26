# Version 4.0.3 - October 26, 2021

Moved `test` directory under `slurm_pipeline`.

# Version 4.0.2 - October 26, 2021

Use `getpass.getuser()` instead of `pwd.getpwuid(os.getuid()).pw_name` to
get the user's name (since the `import pwd` fails on windows).

# Version 4.0.1 - October 26, 2021

Added `LICENSE.txt` for conda forge distribution.

# Version 4.0.0 - October 23, 2021

Removed support for Python 2.7. Added conda building.

# Version 3.2.2 - October 23, 2021

Added `sbatch.py` utility script (and `remove-repeated-headers.py` helper).

# Version 3.2.1 - June 7, 2021

Added `--printOutput` option to tell `slurm-pipeline.py` to print the
output of running each step.

# Version 3.2.0 - June 5, 2021

The distinction between simulated and skipped steps has been removed as it
was too subtle and complicated. Only step skipping remains now, and step
scripts need to decide what to do based on the value of `SP_SKIP`. For
backwards compatibility, the `SP_SIMULATE` variable is still set in the
environment, but its value is always identical to `SP_SKIP`.

Removed use of now-outdated ugly mocking code for `open`. This might break
Python 2 compatibility, but at this point I don't care.

# Version 3.1.1 - August 29, 2019

The `--nice` argument put into the `SP_NICE_ARG` environment variable
changed to be e.g., `--nice=50` (used to be `--nice 50` which causes
`sbatch` to complain "sbatch: error: Unable to open file 50").

## Version 3.1.0 - April 4, 2019

Removed unused `specification` argument to `SAcct` class.

## Version 3.0.2 - October 16, 2018

Added missing `--scriptArgs` to `README.md`. Thanks
[@avatar-lavventura](https://github.com/avatar-lavventura)!

## Version 3.0.1 - June 4, 2018

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
