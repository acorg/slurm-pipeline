.PHONY: run, clean

run:
	../../bin/slurm-pipeline.py -s specification.json viruses.fasta > specification-post-run.json

clean:
	rm -f x?? x??.blast-out BEST-HITS pipeline.log specification-post-run.json
