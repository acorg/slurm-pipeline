# Version 4.1.2 - October 28, 2024

Swapped two colours in the status plot, to make `RUNNING` status more distinct.

# Version 4.1.1 - October 9, 2024

Added type hints.

# Version 4.1.0 - September 21, 2024

Added support for TOML specification files.

# Version 4.0.20 - September 18, 2024

Fixed failing test.

# Version 4.0.19 - September 18, 2024

Removed `kaleido` from the requirements in `setup.py`. No idea how that got there.

# Version 4.0.18 - Aug 13, 2024

Reversed order of status categories displayed in `bin/slurm-pipeline-status-plot.py` plots.

# Version 4.0.17 - Aug 11, 2024

Added "pandas" to test requirements in `setup.py`.

# Version 4.0.16 - Aug 11, 2024

Small tweaks to improve the appearance of `bin/slurm-pipeline-status-plot.py` plots.

# Version 4.0.15 - Aug 11, 2024

Added `bin/slurm-pipeline-status-plot.py`.

# Version 4.0.14 - Dec 11, 2023

Make loading the JSON specification file give a better error message,
including the specification filename.

# Version 4.0.13 - May 22, 2022

Added missing `<` in command line providing input from `*.bz2` files to the
command being executed by `sbatch.py`.

# Version 4.0.12 - April 1, 2022

Added `--verbose` option to `sbatch.py`.

# Version 4.0.11 - April 1, 2022

Added `--compressLevel` and `--randomSleep` options to `sbatch.py`.

# Version 4.0.10 - March 31, 2022

Added compression of input files to `sbatch.py` and an `--uncompress`
option to turn this off. Thanks to
[@holtgrewe](https://github.com/holtgrewe) for this suggestion.

# Version 4.0.9 - November 2, 2021

Updated `.travis.yml` and build status image URL on `README.md`.

# Version 4.0.8 - November 2, 2021

Added conda install instructions to `README.md`.

# Version 4.0.7 - November 2, 2021

Improved `README.md` description of `sbatch.py`.

# Version 4.0.6 - November 2, 2021

Added JSON output of all SLURM job numbers and added to `README.md` to
describe how to easily use the output with
[jq](https://stedolan.github.io/jq/) to pass job ids to `sacct`, `squeue`,
`scancel` or `sbatch.py --afterOk`. Fixed silly bug causing `--then`,
`--else`, and `--finally` commands not to be wrapped in a script for
submission to `sbatch`.

# Version 4.0.5 - October 26, 2021

Improved `README.md`.

# Version 4.0.4 - October 26, 2021

Moved `test` directory back to top level.

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

Updated funding acknowledgements in `README.md`.

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
