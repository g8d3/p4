#!/bin/bash
# Assemble the final video from captured scenes and TTS audio

cd /home/vuos/code/p4/e023-build-in-public/ag-03/output

# Scene timings (in seconds) based on audio duration
SCENE1_DUR=34.5   # 0:00-0:35
SCENE2_DUR=73.5   # 0:35-1:48
SCENE3_DUR=105    # 1:48-3:33
SCENE4_DUR=49     # 3:33-4:22
SCENE5_DUR=45     # 4:22-5:07
SCENE6_DUR=76     # 5:07-6:23

# Create temporary directory for processed scenes
mkdir -p /tmp/video_scenes

# Process each scene: loop image for its duration
ffmpeg -y -loop 1 -i /tmp/scene1.png -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -t $SCENE1_DUR -pix_fmt yuv420p -r 30 /tmp/video_scenes/scene1.mp4

ffmpeg -y -loop 1 -i /tmp/scene2.png -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -t $SCENE2_DUR -pix_fmt yuv420p -r 30 /tmp/video_scenes/scene2.mp4

ffmpeg -y -loop 1 -i /tmp/scene3.png -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -t $SCENE3_DUR -pix_fmt yuv420p -r 30 /tmp/video_scenes/scene3.mp4

ffmpeg -y -loop 1 -i /tmp/scene4.png -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -t $SCENE4_DUR -pix_fmt yuv420p -r 30 /tmp/video_scenes/scene4.mp4

ffmpeg -y -loop 1 -i /tmp/scene5.png -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -t $SCENE5_DUR -pix_fmt yuv420p -r 30 /tmp/video_scenes/scene5.mp4

ffmpeg -y -loop 1 -i /tmp/scene6.png -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -t $SCENE6_DUR -pix_fmt yuv420p -r 30 /tmp/video_scenes/scene6.mp4

# Concatenate all scenes
cat > /tmp/concat.txt << EOF
file '/tmp/video_scenes/scene1.mp4'
file '/tmp/video_scenes/scene2.mp4'
file '/tmp/video_scenes/scene3.mp4'
file '/tmp/video_scenes/scene4.mp4'
file '/tmp/video_scenes/scene5.mp4'
file '/tmp/video_scenes/scene6.mp4'
EOF

ffmpeg -y -f concat -safe 0 -i /tmp/concat.txt -c:v libx264 -preset fast -crf 23 /tmp/video_no_audio.mp4

# Add audio
ffmpeg -y -i /tmp/video_no_audio.mp4 -i tts/narration.mp3 -c:v copy -c:a aac -b:a 192k -shortest /tmp/episode1_no_subs.mp4

# Add simple subtitles (using the script as reference)
# Since we don't have word-level timestamps, we'll add section-based subtitles
ffmpeg -y -i /tmp/episode1_no_subs.mp4 -vf "drawtext=text='Undetectable Browser Benchmark':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=32:x=(w-tw)/2:y=h-80:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:enable='between(t,0,34)'" \
  -vf "drawtext=text='Chrome Authenticated Test':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=32:x=(w-tw)/2:y=h-80:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:enable='between(t,34.5,108)'" \
  -vf "drawtext=text='Fresh Profile Tests':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=32:x=(w-tw)/2:y=h-80:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:enable='between(t,108,213)'" \
  -vf "drawtext=text='Puppeteer Extra Failure':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=32:x=(w-tw)/2:y=h-80:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:enable='between(t,213,262)'" \
  -vf "drawtext=text='Results Compilation':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=32:x=(w-tw)/2:y=h-80:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:enable='between(t,262,307)'" \
  -vf "drawtext=text='Conclusion':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=32:x=(w-tw)/2:y=h-80:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:enable='between(t,307,383)'" \
  -c:v libx264 -preset medium -crf 22 -c:a copy episode.mp4

echo "Video assembled: episode.mp4"