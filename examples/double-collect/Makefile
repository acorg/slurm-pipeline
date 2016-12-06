.PHONY: run, clean

run:
	../../bin/slurm-pipeline.py -s specification.json > specification-post-run.json

clean:
	rm -f pipeline.log specification-post-run.json
	rm -fr output
