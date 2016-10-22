#!/bin/bash

out=output/one-word-per-line.out

echo "Args are $@" > $out
echo "SP_* env vars are:" >> $out
set | egrep '^SP_' | sed 's/^/  /' >> $out

for file in "$@"
do
    base=`basename $file | cut -f1 -d.`
    tr ' ' '\012' < $file > output/$base.words

    # Pretend to have started a SLURM job.
    echo "TASK: $base $RANDOM"
done
