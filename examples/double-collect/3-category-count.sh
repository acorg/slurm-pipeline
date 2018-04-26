#!/bin/bash

task=$1

# Log to a file just for this category, since all category jobs are running
# in parallel.
log=output/$task.log

echo >> $log
echo "Running $(basename $0): Computing total for category $task" >> $log

# Add up the number of observations and totals in the species result files
# for this category, and write a summary to the category output file.
for species in $(egrep "^$task " categories | cut -f2- -d' ')
do
    echo "  Collecting data for species $species" >> $log
    cat output/$species.result
done | awk '{
    n += $1
    sum += $2
}

END {
    printf("%d observations, total %d, mean %.2f\n", n, sum, sum / n)
}' > output/$task.result

echo "Finished $(basename $0) for category $task" >> $log
