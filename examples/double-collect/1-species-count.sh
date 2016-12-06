#!/bin/bash

task=$1
log=output/$task.log

echo >> $log
echo "Running `basename $0` $@" >> $log

# Log to a file just for this species, since all species jobs are running
# in parallel.
echo "  Computing total for species $task" >> $log

# Add up the numbers in data/$task and print the number of data points
# followed by their total.
awk '{sum += $1} END {print NR, sum}' < data/$task > output/$task.result

echo TASK: $task

echo "Finished `basename $0`" >> $log
