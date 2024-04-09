# MetalSeries

**RUN `python main.py` WITH ADMINISTRATOR**

If it says that a package wasn't found, run `python -m pip install -r requirements.txt`.

The patches are read from `patches.json`. I've provided a few default ones which you can toggle on and off, but you can add your own if you'd like.

Yes, you could just directly edit the source code (the stuff in `decomp`) but this is more accessible for people who want to use others' patches and don't know how to code.

Sometimes, after the beautifying stage of the decompilation it breaks and puts a newline for every line.
To fix this you can just run `Decompiler().beautify()` until it's fixed. (For me sometimes I have to run it twice, just keep retrying. It doesn't take too long.)

*P.S. SteelSeries Devs, please make cvgamesense open source. 😁*
