.PHONY: run run-toml clean

run:
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.json > status.json

run-toml:
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.toml > status.json

clean:
	rm -f pipeline.log status.json
	rm -fr output
