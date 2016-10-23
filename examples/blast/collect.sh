#!/bin/bash

cat x??.blast-out | sort -nr | head -n 100 > BEST-HITS
