.PHONY: run run-toml force force-toml rerun rerun-toml clean

run:
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.json --scriptArgs viruses.fasta > status.json

run-toml:
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.toml --scriptArgs viruses.fasta > status.json

force:
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.json --force --scriptArgs viruses.fasta > status.json

force-toml:
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.toml --force --scriptArgs viruses.fasta > status.json

rerun:
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.json --force --firstStep collect --scriptArgs viruses.fasta > status.json

rerun-toml:
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.toml --force --firstStep collect --scriptArgs viruses.fasta > status.json

clean:
	rm -f x?? x??.blast-out BEST-HITS pipeline.log status.json
