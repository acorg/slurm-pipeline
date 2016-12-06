#!/bin/bash

echo >> pipeline.log
echo "Running `basename $0` $@" >> pipeline.log

for category in `cut -f1 -d' ' categories`
do
    echo "Category $category:"
    cat output/$category.result
    echo
done > output/SUMMARY

echo "Finished `basename $0`" >> pipeline.log
