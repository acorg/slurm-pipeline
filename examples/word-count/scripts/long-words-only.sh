#!/bin/bash -e

task=$1
out=output/long-words-$task.out

echo "Args are $@" > $out
echo "SP_* env vars are:" >> $out
set | egrep '^SP_' | sed 's/^/  /' >> $out

awk 'length($0) > 5' < output/$task.words > output/$task.long-words

# Pretend that we started a SLURM job to do more work on this task.
echo "TASK: $task $RANDOM"
