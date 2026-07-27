#!/usr/bin/env python3
"""Enhance SRT: fix numbers, add word highlighting, generate ASS."""
import re, json

# Number words → digits
NUM_MAP = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
    'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
    'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
    'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
    'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
    'eighty': '80', 'ninety': '90', 'hundred': '100', 'thousand': '1000',
    'million': '1000000', 'billion': '1000000000',
}

FRAC_MAP = {'half': '.5', 'quarter': '.25', 'third': '.333'}

def replace_numbers(text):
    """Convert 'five point six' → '5.6', 'sixty four billion' → '64 billion'."""
    # Match patterns like "five point six" or "sixty four billion"
    # First, handle decimal numbers: "five point six"
    text = re.sub(
        r'(' + '|'.join(NUM_MAP.keys()) + r') point (' + '|'.join(NUM_MAP.keys()) + r')',
        lambda m: NUM_MAP[m.group(1)] + '.' + NUM_MAP[m.group(2)], text
    )
    # Handle compound numbers: "sixty four" → "64"
    for i in range(0, 10):
        for j in range(0, 10):
            tens = list(NUM_MAP.keys())[10 + i] if i < 9 else ''
            ones = list(NUM_MAP.keys())[j]
            if tens and ones:
                text = re.sub(r'\b' + tens + r' ' + ones + r'\b',
                              lambda m, a=tens, b=ones: str(int(NUM_MAP[a]) + int(NUM_MAP[b])), text)
    # Handle single number words
    for word, digit in list(NUM_MAP.items())[:10]:
        text = re.sub(r'\b' + word + r'\b', digit, text)
    return text

def generate_ass(srt_segments, output_path):
    """Generate ASS subtitle file with highlighted key words."""
    def fmt_ass(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = sec % 60
        cs = int((s - int(s)) * 100)
        return f'{h:01d}:{m:02d}:{int(s):02d}.{cs:02d}'

    # Key words to highlight (companies, products, people)
    KEYWORDS = [
        'openai', 'gpt', 'hugging face', 'waic', 'shanghai',
        'nubia', 'navix', 'gartner', 'google', 'deepmind',
        'youtube', 'flux', 'gemini', 'microsoft', 'mistral',
        'uc riverside', 'black forest'
    ]

    lines = [
        '[Script Info]',
        'Title: AI News Subtitles',
        'ScriptType: v4.00+',
        'WrapStyle: 0',
        'ScaledBorderAndShadow: yes',
        '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        'Style: Default,Inter,16,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,60,60,50,1',
        'Style: Highlight,Inter,16,&H00FFCC00,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,0,2,60,60,50,1',
        '',
        '[Events]',
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
    ]

    for i, seg in enumerate(srt_segments):
        text = seg['text']
        words = text.split()
        highlighted = []
        for w in words:
            clean = w.lower().strip('.,!?;:')
            if clean in KEYWORDS:
                highlighted.append(r'{\rHighlight}' + w + r'{\rDefault}')
            else:
                highlighted.append(w)
        styled_text = ' '.join(highlighted)

        lines.append(
            f"Dialogue: 0,{fmt_ass(seg['start'])},{fmt_ass(seg['end'])},"
            f"Default,,0,0,0,,{styled_text}"
        )

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f'ASS: {output_path} ({len(srt_segments)} segments with highlighting)')

if __name__ == '__main__':
    # Test
    tests = [
        ('five point six', '5.6'),
        ('sixty four billion', '64 billion'),
        ('ninety nine percent', '99 percent'),
    ]
    for inp, expected in tests:
        result = replace_numbers(inp)
        print(f'  {inp} → {result} (expected: {expected})')
