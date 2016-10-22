.PHONY: run clean

run:
	@test -e output || mkdir output
	../../bin/slurm-pipeline.py -s specification.json texts/*.txt

clean:
	rm -fr output
