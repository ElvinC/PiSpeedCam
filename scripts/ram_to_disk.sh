#!/bin/bash

cd "$1"

us=`cut -f1 -d, tstamps.csv | sort -n | uniq -c | sort -n | tail -1 | cut -b9-`
l=`ls -l /dev/shm/out.*.raw | wc --lines`
echo "$l frames were captured at $((1000000 / $us))fps" 

#echo "frame delta time[us] distribution"
#cut -f1 -d, tstamps.csv | sort -n | uniq -c

#skips=`grep "^[2-9]" tstamps.csv | wc --lines | cut -f1 -d\ `
#stamps=`wc --lines tstamps.csv | cut -f1 -d\ `
#per=`expr \( 100 \* $skips \) / \( $skips + $stamps \)`
#echo "$per% frame skips"

echo "removing old auxiliary files"
rm -f out.*.raw out.*.ppm out.*.ppm.[dDT] out.*.ppm.d.png

echo "copying /dev/shm/out.????.raw files"
for((f=1; f<=$l; ++f))
do
  # cp /dev/shm/out.$(printf "%04d" $f).raw .
  cat hd0.32k /dev/shm/out.$(printf "%04d" $f).raw >out.$(printf "%04d" $f).raw
  #echo -en "$f     \r"
done
echo
