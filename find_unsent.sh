#!/bin/bash

echo "Gistga yuklangan fayllar:"
gh gist list

echo ""
echo "Loyihadagi barcha fayllar:"
find ~/Donishgoh -type f

echo ""
echo "Gistga yuklanmagan fayllar:"
for f in $(find ~/Donishgoh -type f); do
    name=$(basename "$f")
    if ! gh gist list | grep -q "$name"; then
        echo "$name"
    fi
done

