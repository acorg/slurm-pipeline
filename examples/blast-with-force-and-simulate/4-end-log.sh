#!/bin/bash

echo >> pipeline.log
echo "In $(basename $0)" >> pipeline.log
echo "SP_FORCE is $SP_FORCE" >> pipeline.log
echo "SP_SIMULATE is $SP_SIMULATE" >> pipeline.log
echo "BLAST pipeline finished at $(date)" >> pipeline.log
echo "Top hit is against $(head -n 1 BEST-HITS | cut -f2 -d' ')" >> pipeline.log
echo "Full output is in BEST-HITS" >> pipeline.log
