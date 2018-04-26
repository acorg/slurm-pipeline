.PHONY: run, clean

run:
	../../bin/slurm-pipeline.py -s specification.json --scriptArgs viruses.fasta > status.json

clean:
	rm -f x?? x??.blast-out BEST-HITS pipeline.log status.json
