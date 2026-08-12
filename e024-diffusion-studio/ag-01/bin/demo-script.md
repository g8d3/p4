# Demo video script v3 — "Diffusion Studio: the video editor your coding agents can drive"

Topic: Diffusion Studio — what it is, the dapi CLI workflow, compositions as
TSX, real measured data from this agent's session with the editor, and an
honest comparison with p4's ffmpeg/VAAPI pipeline. 16:9 (1920×1080).
Duration results from transcription.

## Narration (KIE Gemini TTS, single take)

Intro:
Diffusion Studio is a video editor built for coding agents. Instead of a
timeline you can't touch, a scene is a TypeScript JSX module — text, media,
timing, and animation all declared as code. This video is itself a Diffusion
Studio composition, written and rendered entirely by an agent.

What I did with it:
I spent a session with the editor to find out what it actually takes to
drive it. The results were mixed — and the numbers tell the story. Setup
alone needed three workarounds: npm twelve blocks git dependencies, blocks
install scripts, and Electron's binary never downloaded. Each one took a
manual fix.

The workflow:
Once running, the workflow is fast. Mount a composition with one command,
inspect the scene graph as a tree, capture any frame to check the layout,
then render the scene to disk. The command surface is agent-native: JSON on
stdout, errors on stderr, exit code one.

The data:
Here is the measured reality. The render engine encodes with software H.264,
called OpenH264, at roughly ninety to one hundred frames per second at
1080p. That means a forty eight second video renders in about fourteen
seconds of wall time. Our GPU encoder, h264_vaapi, runs at two hundred and
thirty five frames per second for the same resolution — two and a half
times faster. The editor also refuses our default AAC audio profile; every
render had to be told to use opus instead. File sizes are honest: a fourteen
second clip with video, audio, and text came out under one megabyte at
around five hundred kilobits per second.

What it means:
So the honest verdict. For authoring — layered text, picture-in-picture,
timing, iteration — compositions as code are dramatically better than
escaping drawtext filters in a shell. For encoding, the software encoder
cannot match our GPU. The practical split: adopt the editor for authoring,
keep the GPU encode rule for delivery. Write the composition here, render
it, then let h264_vaapi produce the final file.

Ideas for the future:
This opens real next steps. Captions and generated assets need the hosted
backend, so wiring the local Parakeet transcription into compositions would
unlock fully offline pipeline. A hardware encoder path inside the editor
would close the speed gap. And the grid pattern — one generation request
for a whole storyboard, decoded by a vision model, cropped into scenes — is
exactly the kind of asset pipeline that belongs in a video tool built for
agents.

Conclusion:
Diffusion Studio is not a replacement for ffmpeg. It is a better way to
describe the video, and ffmpeg stays the best way to encode it. For an
agent, that division of labor is exactly right. This video — script, assets,
renders — was produced end to end by one agent using the tool itself.
