#!/bin/bash

# Our $2 is given to us by run-blast.sh (it's one of the x?? FASTA files).
queryId=`head -n 1 $2 | cut -c2-`

# Emit fake BLAST output: bitscore, subject id, query id (taken from the FASTA).
echo "$RANDOM subject-$RANDOM $queryId" > $2.blast-out

echo "TASK: $2"
