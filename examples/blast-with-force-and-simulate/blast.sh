#!/bin/bash

echo >> pipeline.log
echo "In $(basename $0) $@" >> pipeline.log
echo "SP_FORCE is $SP_FORCE" >> pipeline.log
echo "SP_SIMULATE is $SP_SIMULATE" >> pipeline.log

# $1 = "--query" (to simulate running BLAST), which we just ignore.
# $3 = "--outfmt" (ditto).

# $2 is given to us by run-blast.sh (it's one of the x?? FASTA files). Pull
# out the query id so we can make fake BLAST output for it.
task=$2
queryId=$(head -n 1 $task | cut -c2-)

out=$task.blast-out

if [ $SP_SIMULATE = "0" ]
then
    echo "This is not a simulation." >> pipeline.log

    if [ -f $out ]
    then
        if [ $SP_FORCE = "1" ]
        then
            echo "Pre-existing BLAST file ($out) exists, but --force was used. Overwriting." >> pipeline.log
            echo "$RANDOM subject-$RANDOM $queryId" > $out
        else
            echo "Will not overwrite pre-existing BLAST file ($out). Use --force to make me." >> pipeline.log
            exit 0
        fi
    else
        echo "No pre-existing BLAST file ($out) exists. Running BLAST." >> pipeline.log
        # Emit fake BLAST output: bitscore, subject id, query id (taken from the FASTA).
        echo "$RANDOM subject-$RANDOM $queryId" > $out
    fi
else
    echo "This is a simulation. Will re-emit task name ($task)." >> pipeline.log
fi

echo "TASK: $task"
