#!/bin/bash

task=$1
out=output/long-words-$task.out

echo "Args are $@" > $out
echo "SP_* env vars are:" >> $out
set | egrep '^SP_' | sed 's/^/  /' >> $out

if [ $SP_SKIP = '1' ]
then
    # Act as though we don't exist. We could also make a symbolic link
    # instead of doing the actual copying.
    cp output/$task.words output/$task.long-words
else
    awk 'length($0) > 5' < output/$task.words > output/$task.long-words
fi

# Pretend that we started a SLURM job to do more work on this task.
echo "TASK: $task $RANDOM"
