#!/bin/bash

if [ "$1" = "" ]; then echo "format: `basename $0` ms"; exit; fi

echo "removing /dev/shm/out.*.raw"
rm -f /dev/shm/out.*.raw

cd "$2"

fps=1007
echo "capturing frames for ${1}ms with ${fps}fps requested"
raspiraw -md 7 -g 200 -t $1 -ts tstamps.csv -hd0 hd0.32k -h 75 --voinc 01 --fps $fps -sr 1 -o /dev/shm/out.%04d.raw 2>/dev/null >/dev/null -y 10
exit 1
us=`cut -f1 -d, tstamps.csv | sort -n | uniq -c | sort -n | tail -1 | cut -b9-`
l=`ls -l /dev/shm/out.*.raw | wc --lines`
echo "$l frames were captured at $((1000000 / $us))fps" 

echo "frame delta time[us] distribution"
cut -f1 -d, tstamps.csv | sort -n | uniq -c

# echo "press CTRL-C to stop, or ENTER to show frame skip indices ..."
# read
#echo "after skip frame indices (middle column)"
#grep "^[2-9]" tstamps.csv

skips=`grep "^[2-9]" tstamps.csv | wc --lines | cut -f1 -d\ `
stamps=`wc --lines tstamps.csv | cut -f1 -d\ `
per=`expr \( 100 \* $skips \) / \( $skips + $stamps \)`
echo "$per% frame skips"

echo "removing old auxiliary files"
rm -f out.*.raw out.*.ppm out.*.ppm.[dDT] out.*.ppm.d.png

echo "copying /dev/shm/out.????.raw files"
for((f=1; f<=$l; ++f))
do
  # cp /dev/shm/out.$(printf "%04d" $f).raw .
  cat hd0.32k /dev/shm/out.$(printf "%04d" $f).raw >out.$(printf "%04d" $f).raw
  echo -en "$f     \r"
done
echo

echo "Preparing preview..."

#if [ "$2" = "" ]; then
#    /home/pi/dcraw/dcraw -K /home/pi/Documents/cam/darkframe.pgm out.0001.raw
#else
#    /home/pi/dcraw/dcraw -W out.0001.raw
#fi

/home/pi/dcraw/dcraw -W out.0001.raw



#pnmtopng out.0005.ppm > preview.png
pnmtojpeg -quality 50 out.0001.ppm > preview.png
rm out.0001.ppm
#display preview.png

convertraw
