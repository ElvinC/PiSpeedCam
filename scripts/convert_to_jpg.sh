#!/bin/bash

cd "$1"


echo "dcraw each .raw file (to .ppm)"
for f in out.*.raw
do
  NUM=$(echo {$f} | cut -c6-9)
  /home/pi/Documents/code/PiSpeedCam/dependencies/dcraw/dcraw -W -r 1.2 1 1.3 1 -c $f | pnmtopng > out.$NUM.ppm.png
  echo -en "$f     \r"
done
echo

#echo ".ppm -> .ppm.d"
#for f in out.*.ppm
#do
#  if [ "$5" = "" ]; then
#    ln -s $f $f.d 
#  else
#    if [ "$5" = "d" ]; then
#      double $f > $f.d
#    else
#      double $f > $f.D
#      double $f.D > $f.d
#    fi
#  fi
#  echo -en "$f     \r"
#done
echo
exit 1

echo ".ppm.d -> .ppm.d.png"
for f in out.*.ppm
do
  pnmtopng $f > $f.png
  echo -en "$f     \r"
done
echo

#ffmpeg -i "out.%04d.ppm.png" -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" -pix_fmt yuv420p -crf 11 video.mp4
