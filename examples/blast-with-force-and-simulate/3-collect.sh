#!/bin/bash

echo >> pipeline.log
echo "In `basename $0`" >> pipeline.log
echo "SP_FORCE is $SP_FORCE" >> pipeline.log
echo "SP_SIMULATE is $SP_SIMULATE" >> pipeline.log

# This script could be improved by checking to see if the input files it
# depends on are actually present. E.g.:
#
#   prexistingCount=`ls x??.blast-out 2>/dev/null | wc -l | awk '{print $1}'`
#   echo "There are $prexistingCount pre-existing BLAST files." >> pipeline.log
#
# And checking $prexistingCount in the code below.

out=BEST-HITS

if [ $SP_SIMULATE = "0" ]
then
    echo "This is not a simulation." >> pipeline.log
    if [ -f $out ]
    then
        if [ $SP_FORCE = "1" ]
        then
            echo "Pre-existing result file ($out) exists, but --force was used. Overwriting." >> pipeline.log
            cat x??.blast-out | sort -nr | head -n 100 > $out
        else
            echo "Will not overwrite pre-existing result file ($out). Use --force to make me." >> pipeline.log
            echo "`basename $0`: Will not overwrite pre-existing result file ($out). Use --force to make me." >&2
        fi
    else
        echo "No pre-existing result file ($out) exists, making it." >> pipeline.log
        cat x??.blast-out | sort -nr | head -n 100 > $out
    fi
else
    echo "This is a simulation." >> pipeline.log
fi
