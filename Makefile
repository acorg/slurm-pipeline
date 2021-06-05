# To make the targets below, you should first run pip install requirements-dev.txt

.PHONY: check, tcheck, examples-test, pycodestyle, pyflakes, lint, wc, clean, clobber, upload

check:
	env PYTHONPATH=. pytest

tcheck:
	env PYTHONPATH=. trial --rterrors test

examples-test:
	make -C examples/word-count run clean
	make -C examples/word-count-with-skipping run clean
	make -C examples/blast run clean
	make -C examples/blast-with-force-and-simulate run clean

pycodestyle:
	find . -path './.tox' -prune -o -path './build' -prune -o -path './dist' -prune -o -name '*.py' -print0 | xargs -0 pycodestyle

pyflakes:
	find .  -path './.tox' -prune -path './build' -prune -o -path './dist' -prune -o -name '*.py' -print0 | xargs -0 pyflakes

flake8:
	find .  -path './.tox' -prune -path './build' -prune -o -path './dist' -prune -o -name '*.py' -print0 | xargs -0 flake8

lint: pycodestyle pyflakes

wc:
	find . -path './.tox' -prune -o -path './build' -prune -o -path './dist' -prune -o \( -name '*.py' -o -name '*.sh' \) -print0 | xargs -0 wc -l

clean:
	find . \( -name '*.pyc' -o -name '*~' \) -print0 | xargs -0 rm
	find . -name __pycache__ -type d -print0 | xargs -0 rmdir
	find . -name _trial_temp -type d -print0 | xargs -0 rm -r
	find . -name .pytest_cache -type d -print0 | xargs -0 rm -r
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
