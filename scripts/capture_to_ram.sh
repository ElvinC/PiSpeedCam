#!/bin/bash


echo "removing /dev/shm/out.*.raw"
rm -f /dev/shm/out.*.raw

cd "$1"

echo "capturing frames..."
exec ${2}
