# Demo video script — "Diffusion Studio: the video editor your coding agents can drive"

Topic: Diffusion Studio — what it is, the dapi CLI workflow, compositions as TSX,
and an honest comparison with p4's ffmpeg/VAAPI pipeline.
Aspect ratio: 16:9 (1920×1080). Duration: results from transcription.

## Narration (KIE Gemini TTS, single take)

Diffusion Studio is a video editor built for coding agents. Instead of a
timeline you can't touch, a scene is a TypeScript JSX module — text, media,
timing, and animation all declared as code.

The dapi CLI is the agent's interface to that editor. You write a composition,
mount it with a single command, and every element stays editable. dapi speaks
the agent's language: JSON on stdout, errors on stderr, exit code one.

A typical workflow takes seconds. Mount the composition, inspect the scene graph
as a tree, capture any frame to check the layout, then render the scene to an
H.264 MP4 with audio — right from the command line, no screen capture, no
ffmpeg filter graphs.

The whole thing runs as a live document. Re-mount rebuilds the scene in place.
Assets resolve from a path, a URL, or an asset id, and the editor's own
generation models can fill in the rest.

Now the honest part. Compared to p4's ffmpeg and VAAPI pipeline, what does this
buy you? For authoring — layered text, picture-in-picture, timing, iteration —
compositions as code are dramatically better than escaping drawtext filters. But
the render engine encodes with software H.264 at around a hundred frames per
second, while our GPU encoder runs at over two hundred. And it refuses our
default AAC audio profile.

So the practical answer is: adopt the editor for authoring, keep the GPU encode
rule for delivery. Write the composition here, render it, and let the p4 VAAPI
encoder produce the final file.

Diffusion Studio is not a replacement for ffmpeg. It's a better way to describe
the video, and ffmpeg stays the best way to encode it. For an agent, that
division of labor is exactly right.
