# Script — "Your first Diffusion Studio composition"

Topic: writing and rendering a first composition with Diffusion Studio's JSX API.
Angle: hands-on code tutorial (ag-01 already did the broad overview + benchmark).
Aspect ratio: 16:9 (1920×1080). Duration results from transcription.

Narration is split into 3 parts for KIE Gemini TTS (~106 s max per call).

## Part 1 — intro, scene root, text

Diffusion Studio turns a video into code. This is the editor your coding agents
can drive — and in this video we will write our very first composition from
scratch. A composition is a TypeScript JSX module. Every scene is a tree of
elements: text, video, image, audio, timing, and animation, all declared as code
instead of dragged on a timeline.

Every composition starts with a scene. In JSX that is a single rect element with
a scene attribute and an id. Here it is one thousand nine hundred and twenty by
one thousand and eighty pixels — a sixteen by nine canvas. Everything you mount
lives inside this rectangle. Re-mounting a composition with the same scene id
rebuilds that scene in place, so editing is just editing the file and mounting
again.

Text is a first-class element. You give it position, size, font, color, and
alignment — the same props a designer would set in a panel. Here a one hundred
and twenty pixel title sits centered on screen, with a fade-in animation.
Because it is code, you can map over an array and render a whole list of
captions from one loop.

## Part 2 — media, timing, mount, inspect

Media works the same way. A video element takes a source, a start, and an end.
An image takes a source and an object fit. An audio element drops narration or
music onto the timeline. Everything is relative to the scene, so the same
composition works at any resolution you render.

Timing is explicit. start and end are time values in seconds, not frames.
Animations are attached to elements with a type and a duration. That removes the
guesswork around frame rates — the engine keeps it consistent whether you render
at twenty five or thirty frames per second.

To see it, mount it. One command — dapi mount — compiles the TypeScript and
loads it into the editor over a local socket. The command line is agent-native:
JSON on standard output, errors on standard error, exit code one on failure.
Pipe it, grep it, drive it from a script.

Then inspect before you commit pixels. dapi node tree prints the scene graph as
a tree. dapi node capture renders any frame to a contact sheet image, offline,
no credits. You can check layout at any timestamp before you spend an encode.

## Part 3 — render, payoff, conclusion

Render with dapi node render. One caveat measured on this machine: the default
AAC audio is refused by the browser encoder, so pass opus. The render is
software H.264 — around one hundred frames per second at ten eighty p — real
enough to author with, but not the GPU encoder p4 uses for final delivery.

The real payoff is the loop. Change a line, re-mount, capture a frame, render.
Everything stays editable because the source of truth is the file, not a baked
timeline. For an agent, that is the difference between writing video and
building it.

That is your first composition. Ten elements, one mount, one render. Diffusion
Studio is not a replacement for ffmpeg — it is a better way to describe the
video. Write it here, then let the GPU encode it. The source is the deliverable.
