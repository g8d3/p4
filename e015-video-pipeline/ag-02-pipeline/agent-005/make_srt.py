import math

duration = 96.408

text = """What if your AI assistant could remember everything across sessions, organize all your saved content automatically, and run entirely on your own hardware with zero cloud dependencies? That future is not just coming, it's here right now.
First, Tencent DB Agent Memory provides a fully local four-tier progressive pipeline designed specifically for AI agent memory.
It operates with absolutely zero API dependencies, meaning your agent's memory stays completely private on your own machine.
The pipeline progresses through four distinct tiers from working memory all the way to long-term archival storage, with each tier offering increasing capacity and decreasing access speed.
Second, Karakip is a self-hostable bookmark everything app that has earned over 27,000 stars on GitHub.
It uses AI-powered tagging to automatically organize everything you save, making your content searchable by meaning and context rather than just keywords or folders.
Third, when you combine these with Tinbase, a tool that delivers full Supabase functionality in a single binary, you get a complete stack for building autonomous AI agents.
These agents can remember past conversations, organize vast libraries of information, and take action, all without any dependency on cloud services or external APIs.
Self-hosted AI infrastructure is no longer a distant dream.
With Agent Memory, AI bookmarking, and single-binary databases, your AI can now run entirely on your terms.
Private, powerful, and truly autonomous."""

segments = [s.strip() for s in text.split('\n') if s.strip()]

total_words = sum(len(s.split()) for s in segments)

def fmt_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

start = 0.0
for i, seg in enumerate(segments):
    words = len(seg.split())
    seg_dur = (words / total_words) * duration
    end = start + seg_dur
    print(f"{i+1}")
    print(f"{fmt_time(start)} --> {fmt_time(end)}")
    print(f"{seg}")
    print()
    start = end
