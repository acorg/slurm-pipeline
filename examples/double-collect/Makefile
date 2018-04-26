.PHONY: run, clean

run:
	../../bin/slurm-pipeline.py -s specification.json > status.json

clean:
	rm -f pipeline.log status.json
	rm -fr output
