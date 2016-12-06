#!/bin/bash

# Just emit a new task name for each category.

for category in `cut -f1 -d' ' categories`
do
    # Log to a file just for this category, since all category jobs will
    # run in parallel.
    echo "Emitting category $category task" >> output/$category.log

    echo TASK: $category
done
