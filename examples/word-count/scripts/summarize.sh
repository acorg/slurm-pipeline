#!/bin/bash -e

out=output/summarize.out

echo "Args are $@" > $out
echo "SP_* env vars are:" >> $out
set | egrep '^SP_' | sed 's/^/  /' >> $out

files=

for base in "$@"
do
    files="$files output/$base.long-words"
done

echo "Files we operate on:$files" >> $out

cat $files | sort | uniq -c | sort -nr | head -n 10 > output/MOST-FREQUENT-WORDS
