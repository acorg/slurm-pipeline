#!/bin/bash

./blast.sh -query $1 -outfmt "6 bitscore sseqid qseqid"

# Clean up (remove the split FASTA file made by 1-split-fasta.sh).
rm $1

echo "TASK: $1"
