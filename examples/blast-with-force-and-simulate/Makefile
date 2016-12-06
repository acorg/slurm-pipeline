.PHONY: run, force, rerun, clean

run:
	../../bin/slurm-pipeline.py -s specification.json viruses.fasta > specification-post-run.json

force:
	../../bin/slurm-pipeline.py -s specification.json --force viruses.fasta > specification-post-run.json

rerun:
	../../bin/slurm-pipeline.py -s specification.json --force --firstStep collect viruses.fasta > specification-post-run.json

clean:
	rm -f x?? x??.blast-out BEST-HITS pipeline.log specification-post-run.json
