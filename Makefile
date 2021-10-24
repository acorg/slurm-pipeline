# To make the targets below, you should first run pip install requirements-dev.txt

.PHONY: check, examples-test, pycodestyle, flake8, wc, clean, upload

check:
	pytest

examples-test:
	make -C examples/word-count run clean
	make -C examples/word-count-with-skipping run clean
	make -C examples/blast run clean
	make -C examples/blast-with-force-and-skipping run clean

pycodestyle:
	find . -path './.tox' -prune -o -path './build' -prune -o -path './dist' -prune -o -name '*.py' -print0 | xargs -0 pycodestyle

flake8:
	find .  -path './.tox' -prune -path './build' -prune -o -path './dist' -prune -o -name '*.py' -print0 | xargs -0 flake8

wc:
	find . -path './.tox' -prune -o -path './build' -prune -o -path './dist' -prune -o \( -name '*.py' -o -name '*.sh' \) -print0 | xargs -0 wc -l

clean:
	find . \( -name '*.pyc' -o -name '*~' \) -print0 | xargs -0 rm
	find . -name __pycache__ -type d -print0 | xargs -0 rmdir
	find . -name _trial_temp -type d -print0 | xargs -0 rm -r
	find . -name .pytest_cache -type d -print0 | xargs -0 rm -r
	python setup.py $@
	rm -fr slurm_pipeline.egg-info dist
	make -C examples/word-count $@
	make -C examples/word-count-with-skipping $@
	make -C examples/blast $@
	make -C examples/blast-with-force-and-skipping $@

# The upload target requires that you have access rights to PYPI.
upload:
	python setup.py sdist
	export PYTHONPATH=`pwd`; twine upload dist/slurm-pipeline-$$(bin/slurm-pipeline-version.py).tar.gz
