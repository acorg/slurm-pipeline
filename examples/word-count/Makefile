.PHONY: run run-toml sh clean

run:
	@test -e output || mkdir output
	rm -f output/*
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.json --scriptArgs texts/*.txt > output/status.json

run-toml:
	@test -e output || mkdir output
	rm -f output/*
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.toml --scriptArgs texts/*.txt > output/status.json

sh:
	cat texts/*.txt | tr ' ' '\012' | awk 'length($0) > 5' | sort | uniq -c | sort -nr | head -n 10

clean:
	rm -fr output
