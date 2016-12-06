#!/bin/bash

echo "Running double collect pipeline at `date`" > pipeline.log

echo >> pipeline.log
echo "Running `basename $0` $@" >> pipeline.log

[ -d output ] || mkdir output

for file in data/*
do
    task=`basename $file`
    echo "  Emitting task $task" >> pipeline.log
    echo TASK: $task
done

echo "Finished `basename $0`" >> pipeline.log
