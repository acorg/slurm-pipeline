.PHONY: run clean

run:
	../../bin/slurm-pipeline.py -s specification.json viruses.fasta

clean:
	rm -f x?? x??.blast-out BEST-HITS pipeline.log
