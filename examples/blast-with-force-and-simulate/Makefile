.PHONY: run, force, rerun, clean

run:
	../../bin/slurm-pipeline.py -s specification.json --scriptArgs viruses.fasta > status.json

force:
	../../bin/slurm-pipeline.py -s specification.json --force --scriptArgs viruses.fasta > status.json

rerun:
	../../bin/slurm-pipeline.py -s specification.json --force --firstStep collect --scriptArgs viruses.fasta > status.json

clean:
	rm -f x?? x??.blast-out BEST-HITS pipeline.log status.json
