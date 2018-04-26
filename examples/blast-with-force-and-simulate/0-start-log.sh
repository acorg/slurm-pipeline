#!/bin/bash

echo "Running (fake) BLAST pipeline at $(date)" > pipeline.log
echo "Input FASTA is $@" >> pipeline.log
echo "SP_FORCE is $SP_FORCE" >> pipeline.log
echo "SP_SIMULATE is $SP_SIMULATE" >> pipeline.log
