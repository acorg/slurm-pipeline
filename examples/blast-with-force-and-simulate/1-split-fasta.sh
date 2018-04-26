#!/bin/bash

echo >> pipeline.log
echo "In $(basename $0)" >> pipeline.log
echo "SP_FORCE is $SP_FORCE" >> pipeline.log
echo "SP_SIMULATE is $SP_SIMULATE" >> pipeline.log

prexistingCount=$(ls x?? 2>/dev/null | wc -l | awk '{print $1}')
echo "There are $prexistingCount pre-existing split files." >> pipeline.log

if [ $SP_SIMULATE = "0" ]
then
    echo "This is not a simulation." >> pipeline.log
    if [ $prexistingCount -ne 0 ]
    then
        if [ $SP_FORCE = "1" ]
        then
            echo "Pre-existing split files exist, but --force was used. Overwriting." >> pipeline.log
            split -l 2 $1
        else
            echo "Will not overwrite pre-existing split files. Use --force to make me." >> pipeline.log
            echo "$(basename $0): Will not overwrite pre-existing split files. Use --force to make me." >&2
        fi
    else
        echo "No pre-existing split files exist, splitting." >> pipeline.log
        split -l 2 $1
    fi
else
    echo "This is a simulation. Will re-emit task names (the already existing split file names)." >> pipeline.log
fi

for task in x??
do
    echo TASK: $task
done
