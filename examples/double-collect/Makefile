.PHONY: run, clean

run:
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.json > status.json

clean:
	rm -f pipeline.log status.json
	rm -fr output
