#!/usr/bin/env python

from setuptools import setup

setup(name='slurm-pipeline',
      version='1.1.4',
      packages=['slurm_pipeline'],
      include_package_data=True,
      url='https://github.com/acorg/slurm-pipeline',
      download_url='https://github.com/acorg/slurm-pipeline',
      author='Terry Jones',
      author_email='tcj25@cam.ac.uk',
      keywords=['slurm'],
      scripts=['bin/slurm-pipeline.py', 'bin/slurm-pipeline-status.py'],
      classifiers=[
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      license='MIT',
      description='A Python class for scheduling SLURM jobs')
