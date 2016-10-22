#!/bin/bash

out=output/summarize.out

echo "Args are $@" > $out
echo "SP_* env vars are:" >> $out
set | egrep '^SP_' | sed 's/^/  /' >> $out

# The files we need to operate on can be constructed from SP_TASK_NAMES

files=

for base in $SP_TASK_NAMES
do
    files="$files output/$base.long-words"
done

echo "Our files: $files" >> $out

cat $files | sort | uniq -c | sort -nr | head -n 10 > output/most-frequent-words
