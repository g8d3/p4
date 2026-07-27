#!/usr/bin/env python3
"""Download images for specific segments and apply Ken Burns effect."""
import subprocess, json, os, re, time, shutil
from pathlib import Path

TMPDIR = Path('/tmp/ai-news-build')
MANIFEST = Path('/home/vuos/code/p4/e018-hyprframes-browser-video/ag-02/output/ai-news-manifest.json')
OUTPUT = Path('/home/vuos/code/p4/e018-hyprframes-browser-video/ag-02/output')
CACHE = TMPDIR / 'kenburns'

# Segments that need Ken Burns images (index, search term)
KENBURN_SEGMENTS = {
    2: 'openai logo',     # "We start with a major security incident at OpenAI"
    4: 'gpt logo',        # "an unreleased model GPT-5.6 Sol"
    5: 'hugging face logo',  # "The AI connected to internet... Hugging Face"
    8: 'shangai conference center',  # "Moving on to Shanghai... WAIC"
    11: 'nubia smartphone',  # "smartphones like Nubia's NaviX Ultra"
    13: 'gartner logo',   # "Gartner released a massive forecast"
    17: 'google deepmind logo',  # "working with Google DeepMind and YouTube"
    18: 'youtube logo',
    20: 'black forest labs logo',  # "Black Forest Labs rolled out FLUX 3"
    21: 'gemini logo',    # "Google DeepMind expanded... Gemini 3.6 Flash"
    22: 'microsoft mistral logo',  # "Microsoft and Mistral deepened..."
}

def search_download_image(term, output_path):
    """Search Pixabay images for term, download first result."""
    import urllib.parse
    search_url = f"https://pixabay.com/images/search/{urllib.parse.quote(term)}/"
    subprocess.run(['agent-browser', '--auto-connect', 'open', search_url],
                  capture_output=True, timeout=30)
    time.sleep(2)
    snap = subprocess.run(['agent-browser', '--auto-connect', 'snapshot', '-i'],
                         capture_output=True, text=True, timeout=20)
    # Find download ref
    download_ref = None
    for line in snap.stdout.split('\n'):
        if 'Download' in line and 'ref=' in line:
            m = re.search(r'ref=([a-z0-9]+)', line)
            if m:
                download_ref = m.group(1)
                break
    if not download_ref:
        print(f"    No download for '{term}'")
        return False
    subprocess.run(['agent-browser', '--auto-connect', 'click', f'@{download_ref}'],
                  capture_output=True, timeout=30)
    time.sleep(2)
    dl_dir = Path.home() / 'Downloads'
    imgs = sorted(dl_dir.glob('*.jpg'), key=os.path.getmtime, reverse=True)
    if imgs:
        shutil.move(str(imgs[0]), str(output_path))
        return True
    imgs = sorted(dl_dir.glob('*.png'), key=os.path.getmtime, reverse=True)
    if imgs:
        shutil.move(str(imgs[0]), str(output_path))
        return True
    return False

def create_kenburns(image_path, duration, output_path):
    """Apply Ken Burns zoom-in effect to a still image."""
    fps = 30
    frames = int(duration * fps)
    # zoom from 1.0 to 1.3 over the duration
    subprocess.run([
        'ffmpeg', '-y', '-i', str(image_path),
        '-vf', f"zoompan=z='min(zoom+0.01,1.3)':d={frames}:fps={fps}:s=1080x1920",
        '-t', str(duration), '-c:v', 'libvpx', '-b:v', '2M',
        str(output_path)
    ], capture_output=True, timeout=60)
    return output_path.exists()

if __name__ == '__main__':
    with open(MANIFEST) as f:
        segments = json.load(f)
    
    CACHE.mkdir(parents=True, exist_ok=True)
    results = []
    
    for seg_idx, search_term in KENBURN_SEGMENTS.items():
        img_file = CACHE / f'seg{seg_idx}.jpg'
        webm_file = CACHE / f'seg{seg_idx}.webm'
        
        if not img_file.exists():
            print(f"[{seg_idx}] Searching: {search_term}")
            ok = search_download_image(search_term, img_file)
            if not ok:
                print(f"  FAILED: {search_term}")
                continue
            print(f"  Image saved: {img_file.name}")
        
        dur = round(segments[seg_idx]['end'] - segments[seg_idx]['start'] + 0.2, 2)
        
        if not webm_file.exists():
            print(f"  Ken Burns: {dur}s")
            create_kenburns(img_file, dur, webm_file)
        
        results.append({'index': seg_idx, 'webm': webm_file, 'duration': dur,
                        'term': search_term})
    
    # Print copy-paste instructions for build script
    print(f"\nDone. {len(results)}/{len(KENBURN_SEGMENTS)} segments processed.")
    print("\nTo use: replace these files in concat:")
    for r in results:
        print(f"  seg_{r['index']}.webm → {r['webm']}")
