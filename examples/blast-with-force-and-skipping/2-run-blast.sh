#!/bin/bash

echo >> pipeline.log
echo "In $(basename $0)" >> pipeline.log
echo "SP_FORCE is $SP_FORCE" >> pipeline.log
echo "SP_SKIP is $SP_SKIP" >> pipeline.log

./blast.sh -query $1 -outfmt "6 bitscore sseqid qseqid"

echo "TASK: $1"
