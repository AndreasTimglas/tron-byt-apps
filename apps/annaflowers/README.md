# Anna Flowers

A 64×32 greeting with the exact text:

> Anna, Anna, vad gör man en söndagmorgon

The sentence scrolls in white `tb-8` text, preserving the Swedish ö, inside
a pink, purple, and peach flower border. The original pixel flowers have
rounded upright blossoms and paired side petals with an intentionally cheeky,
suggestive silhouette. The border occupies all four sides; the text has its
own 46-pixel-wide central strip.

No settings, network calls, API keys, or external images are needed.

```sh
pixlet check apps/annaflowers/annaflowers.star
pixlet render apps/annaflowers/annaflowers.star
pixlet serve apps/annaflowers/annaflowers.star
```

Set the app's display duration to at least **14 seconds** in Tronbyt Manager
to read the complete sentence. The scroll uses a 60 ms frame delay and fits
within the standard 15-second render limit. Daily rendering is recommended
in the manifest because the content is static; this is separate from how long
the app stays on screen.

Validated with Pixlet v0.54.0: compatibility check, rendered border/text layout,
and complete animation duration.
