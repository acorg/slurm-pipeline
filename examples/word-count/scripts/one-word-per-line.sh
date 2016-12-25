#!/bin/bash -e

[ -d output ] || mkdir output

out=output/one-word-per-line.out

echo "Args are $@" > $out
echo "SP_* env vars are:" >> $out
set | egrep '^SP_' | sed 's/^/  /' >> $out

# This is the first script to be run. On its command line it gets the
# (non-specification) arguments that were given to
# ../../bin/slurm-pipeline.py by the Makefile (i.e., texts/*.txt).

for file in "$@"
do
    task=`basename $file | cut -f1 -d.`
    tr ' ' '\012' < $file > output/$task.words

    # Pretend that we started a SLURM job to do more work on this task.
    echo "TASK: $task $RANDOM"
done
