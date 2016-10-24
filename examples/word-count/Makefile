.PHONY: run clean

run:
	@test -e output || mkdir output
	rm -f output/*
	../../bin/slurm-pipeline.py -s specification.json texts/*.txt > output/specification-post-run.json

sh:
	cat texts/*.txt | tr ' ' '\012' | awk 'length($0) > 5' | sort | uniq -c | sort -nr | head -n 10

clean:
	rm -fr output
