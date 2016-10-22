#!/bin/bash

out=output/long-words-$SP_TASK_NAME.out

echo "Args are $@" > $out
echo "SP_* env vars are:" >> $out
set | egrep '^SP_' | sed 's/^/  /' >> $out

# The file we need to operate on can be constructed from SP_TASK_NAME

awk 'length($0) > 5' < output/$SP_TASK_NAME.words > output/$SP_TASK_NAME.long-words

# Pretend that we started a SLURM job.
echo "TASK: $SP_TASK_NAME $RANDOM"
