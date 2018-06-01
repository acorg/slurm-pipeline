.PHONY: run, sh, clean

run:
	@test -e output || mkdir output
	rm -f output/*
	env PYTHONPATH=../.. ../../bin/slurm-pipeline.py -s specification.json --skip long-words --scriptArgs texts/*.txt > output/status.json

sh:
	cat texts/*.txt | tr ' ' '\012' | sort | uniq -c | sort -nr | head -n 10

clean:
	rm -fr output
