#!/bin/bash

split -l 2 $1

for task in x??
do
    echo TASK: $task
done
