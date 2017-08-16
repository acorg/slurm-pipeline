.PHONY: check, tcheck, examples-test, pep8, pyflakes, lint, wc, clean, clobber, upload

check:
	python -m discover -v

tcheck:
	trial --rterrors test

examples-test:
	make -C examples/word-count run clean
	make -C examples/word-count-with-skipping run clean
	make -C examples/blast run clean
	make -C examples/blast-with-force-and-simulate run clean

pep8:
	find . -path './.tox' -prune -o -path './build' -prune -o -path './dist' -prune -o -name '*.py' -print0 | xargs -0 pep8

pyflakes:
	find .  -path './.tox' -prune -path './build' -prune -o -path './dist' -prune -o -name '*.py' -print0 | xargs -0 pyflakes

lint: pep8 pyflakes

wc:
	find . -path './.tox' -prune -o -path './build' -prune -o -path './dist' -prune -o \( -name '*.py' -o -name '*.sh' \) -print0 | xargs -0 wc -l

clean:
	find . \( -name '*.pyc' -o -name '*~' \) -print0 | xargs -0 rm
	find . -name '__pycache__' -type d -print0 | xargs -0 rmdir
	find . -name '_trial_temp' -type d -print0 | xargs -0 rm -r
	python setup.py clean
	rm -fr slurm_pipeline.egg-info dist
	make -C examples/word-count $@
	make -C examples/word-count-with-skipping $@
	make -C examples/blast $@
	make -C examples/blast-with-force-and-simulate $@

# The upload target requires that you have access rights to PYPI.
upload:
	python setup.py sdist
	export PYTHONPATH=`pwd`; twine upload dist/slurm-pipeline-$$(bin/slurm-pipeline-version.py).tar.gz
