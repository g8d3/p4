#!/usr/bin/env python3
"""Generate AI news HyperFrames video — v2 with content-based visuals."""
import json, os

MANIFEST = '/home/vuos/code/p4/e018-hyprframes-browser-video/ag-02/output/ai-news-manifest.json'
OUTPUT_HTML = '/home/vuos/code/p4/e018-hyprframes-browser-video/ag-02/ai-news/index.html'

with open(MANIFEST) as f:
    segments = json.load(f)

total_dur = segments[-1]['end'] + 0.5

# Visual concepts per segment (index-based)
visuals = [
    # 1: globe network — video background
    ("intro", "linear-gradient(135deg,#050510 0%,#0a1030 50%,#050510 100%)",
     '''<video id="s1-vid" muted playsinline data-volume="0" style="position:absolute;top:0;left:0;width:1080px;height:1920px;object-fit:cover;opacity:0.7">
  <source src="assets/globe_clip.mp4" type="video/mp4">
</video>''',
     '''tl.fromTo("#s1-vid",{opacity:0},{opacity:0.7,duration:0.8},{0.3});'''),

    # 2: neural network mesh
    ("nn", "linear-gradient(135deg,#0a0510 0%,#1a0520 50%,#0a0510 100%)",
     '''<div id="s2-n1" class="dot" style="width:12px;height:12px;left:300px;top:700px;background:#aa44ff"></div>
<div id="s2-n2" class="dot" style="width:10px;height:10px;left:700px;top:800px;background:#cc66ff"></div>
<div id="s2-n3" class="dot" style="width:8px;height:8px;left:540px;top:1100px;background:#8822ff"></div>
<div id="s2-n4" class="dot" style="width:6px;height:6px;left:200px;top:1000px;background:#aa44ff"></div>
<div id="s2-n5" class="dot" style="width:10px;height:10px;left:800px;top:500px;background:#cc66ff"></div>
<div id="s2-n6" class="dot" style="width:7px;height:7px;left:400px;top:1200px;background:#8822ff"></div>
<div id="s2-c1" class="line" style="width:2px;height:250px;left:300px;top:700px;background:linear-gradient(to bottom,rgba(170,68,255,0.3),transparent);transform:rotate(30deg);transform-origin:top center"></div>
<div id="s2-c2" class="line" style="width:2px;height:350px;left:700px;top:800px;background:linear-gradient(to bottom,rgba(204,102,255,0.3),transparent);transform:rotate(-20deg);transform-origin:top center"></div>
<div id="s2-c3" class="line" style="width:2px;height:200px;left:540px;top:1100px;background:linear-gradient(to top,rgba(136,34,255,0.2),transparent);transform:rotate(-15deg);transform-origin:bottom center"></div>''',
     '''tl.fromTo("#s2-n1",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"},{2.7});
tl.fromTo("#s2-n2",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"},{3});
tl.fromTo("#s2-n3",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"},{3.3});
tl.fromTo("#s2-n4",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"},{3.6});
tl.fromTo("#s2-n5",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"},{3.9});
tl.fromTo("#s2-n6",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"},{4.2});
tl.fromTo("#s2-c1",{scaleY:0,opacity:0,transformOrigin:"top center"},{scaleY:1,opacity:1,duration:0.6},{3.5});
tl.fromTo("#s2-c2",{scaleY:0,opacity:0,transformOrigin:"top center"},{scaleY:1,opacity:1,duration:0.6},{4});
tl.fromTo("#s2-c3",{scaleY:0,opacity:0,transformOrigin:"bottom center"},{scaleY:1,opacity:1,duration:0.6},{4.5});
tl.to(["#s2-n1","#s2-n2","#s2-n3","#s2-n4","#s2-n5","#s2-n6"],{opacity:0.4,duration:0.8,repeat:-1,yoyo:true},{5});'''),

    # 3: shield with crack
    ("shield", "linear-gradient(135deg,#100505 0%,#200510 50%,#100505 100%)",
     '''<div id="s3-shield" class="rect" style="width:200px;height:240px;left:440px;top:840px;border:4px solid rgba(255,50,50,0.4);border-radius:30px"></div>
<div id="s3-crack" class="line" style="width:180px;height:3px;left:450px;top:980px;background:rgba(255,50,50,0.6);transform:rotate(-35deg);transform-origin:left center"></div>
<div id="s3-crack2" class="line" style="width:120px;height:2px;left:490px;top:960px;background:rgba(255,50,50,0.5);transform:rotate(25deg);transform-origin:left center"></div>
<div id="s3-glow" class="shape" style="width:400px;height:400px;left:340px;top:760px;background:radial-gradient(circle,rgba(255,50,50,0.06) 0%,transparent 70%)"></div>''',
     '''tl.fromTo("#s3-shield",{scale:0.5,opacity:0},{scale:1,opacity:1,duration:0.6,ease:"back.out(2)"},{7.3});
tl.fromTo("#s3-glow",{scale:0,opacity:0},{scale:1.5,opacity:1,duration:0.8},{7.2});
tl.fromTo("#s3-crack",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.5},{8.5});
tl.fromTo("#s3-crack2",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.4},{9});'''),

    # 4: guardrails breaking
    ("rails", "linear-gradient(135deg,#0a0510 0%,#1a0510 50%,#0a0510 100%)",
     '''<div id="s4-rail1" class="rect" style="width:400px;height:6px;left:340px;top:760px;background:rgba(255,100,50,0.6);border-radius:3px"></div>
<div id="s4-rail2" class="rect" style="width:400px;height:6px;left:340px;top:840px;background:rgba(255,100,50,0.5);border-radius:3px"></div>
<div id="s4-rail3" class="rect" style="width:400px;height:6px;left:340px;top:920px;background:rgba(255,100,50,0.4);border-radius:3px"></div>
<div id="s4-rail4" class="rect" style="width:400px;height:6px;left:340px;top:1000px;background:rgba(255,100,50,0.3);border-radius:3px"></div>
<div id="s4-post1" class="rect" style="width:10px;height:300px;left:340px;top:760px;background:rgba(255,100,50,0.3);border-radius:2px"></div>
<div id="s4-post2" class="rect" style="width:10px;height:300px;left:730px;top:760px;background:rgba(255,100,50,0.3);border-radius:2px"></div>''',
     '''tl.fromTo("#s4-rail1",{scaleX:1,opacity:1},{scaleX:0.3,opacity:0.5,duration:1,transformOrigin:"center center"},{11.6});
tl.fromTo("#s4-rail2",{scaleX:1,opacity:1},{scaleX:0.3,opacity:0.5,duration:1,transformOrigin:"center center"},{12.2});
tl.fromTo("#s4-rail3",{scaleX:1,opacity:1},{scaleX:0.3,opacity:0.5,duration:1,transformOrigin:"center center"},{12.8});
tl.fromTo("#s4-rail4",{scaleX:1,opacity:1},{scaleX:0.3,opacity:0.5,duration:1,transformOrigin:"center center"},{13.4});
tl.fromTo("#s4-post1",{scaleY:1},{scaleY:0.5,duration:0.8,transformOrigin:"bottom center"},{13});
tl.fromTo("#s4-post2",{scaleY:1},{scaleY:0.5,duration:0.8,transformOrigin:"bottom center"},{13});'''),

    # 5: capsule/box with light escaping
    ("escape", "linear-gradient(135deg,#0a0a10 0%,#1a0a15 50%,#0a0a10 100%)",
     '''<div id="s5-box" class="rect" style="width:240px;height:280px;left:420px;top:820px;border:2px solid rgba(200,100,200,0.3);border-radius:20px"></div>
<div id="s5-door" class="rect" style="width:100px;height:200px;left:490px;top:860px;border:1px solid rgba(200,100,200,0.2);border-radius:10px"></div>
<div id="s5-beam" class="line" style="width:300px;height:4px;left:540px;top:960px;background:linear-gradient(90deg,rgba(200,100,255,0.6),transparent)"></div>
<div id="s5-particle1" class="dot" style="width:6px;height:6px;left:550px;top:940px;background:#c864ff"></div>
<div id="s5-particle2" class="dot" style="width:5px;height:5px;left:600px;top:900px;background:#c864ff"></div>
<div id="s5-particle3" class="dot" style="width:4px;height:4px;left:650px;top:960px;background:#c864ff"></div>''',
     '''tl.fromTo("#s5-box",{scale:0.5,opacity:0},{scale:1,opacity:1,duration:0.5,ease:"back.out(2)"},{17.5});
tl.fromTo("#s5-door",{scaleX:0,opacity:0,transformOrigin:"right center"},{scaleX:1,opacity:1,duration:0.4},{18.2});
tl.fromTo("#s5-beam",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.5},{18.5});
tl.fromTo("#s5-particle1",{x:0,y:0,opacity:0},{x:80,y:-20,opacity:1,duration:0.8},{19});
tl.fromTo("#s5-particle2",{x:0,y:0,opacity:0},{x:120,y:10,opacity:1,duration:0.8},{19.3});
tl.fromTo("#s5-particle3",{x:0,y:0,opacity:0},{x:100,y:30,opacity:1,duration:0.8},{19.6});'''),

    # 6: spiderweb connections
    ("web", "linear-gradient(135deg,#051010 0%,#051020 50%,#051010 100%)",
     '''<div id="s6-center" class="dot" style="width:20px;height:20px;left:530px;top:950px;background:#00aaff"></div>
<div id="s6-web1" class="line" style="width:2px;height:300px;left:530px;top:800px;background:rgba(0,170,255,0.2)"></div>
<div id="s6-web2" class="line" style="width:2px;height:300px;left:530px;top:950px;background:rgba(0,170,255,0.2)"></div>
<div id="s6-web3" class="line" style="width:300px;height:2px;left:300px;top:950px;background:rgba(0,170,255,0.2)"></div>
<div id="s6-web4" class="line" style="width:300px;height:2px;left:480px;top:950px;background:rgba(0,170,255,0.2)"></div>
<div id="s6-ring1" class="ring" style="width:100px;height:100px;left:490px;top:900px;border-color:rgba(0,170,255,0.15);border-width:1px"></div>
<div id="s6-ring2" class="ring" style="width:200px;height:200px;left:440px;top:850px;border-color:rgba(0,170,255,0.1);border-width:1px"></div>
<div id="s6-ring3" class="ring" style="width:300px;height:300px;left:390px;top:800px;border-color:rgba(0,170,255,0.07);border-width:1px"></div>''',
     '''tl.fromTo("#s6-center",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.5,ease:"back.out(2)"},{24});
tl.fromTo("#s6-ring1",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4},{24.3});
tl.fromTo("#s6-ring2",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4},{24.6});
tl.fromTo("#s6-ring3",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4},{24.9});
tl.fromTo("#s6-web1",{scaleY:0,opacity:0,transformOrigin:"center top"},{scaleY:1,opacity:1,duration:0.5},{25.3});
tl.fromTo("#s6-web2",{scaleY:0,opacity:0,transformOrigin:"center bottom"},{scaleY:1,opacity:1,duration:0.5},{25.6});
tl.fromTo("#s6-web3",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.5},{25.9});
tl.fromTo("#s6-web4",{scaleX:0,opacity:0,transformOrigin:"right center"},{scaleX:1,opacity:1,duration:0.5},{26.2});
tl.to(["#s6-ring1","#s6-ring2","#s6-ring3"],{opacity:0.5,duration:1.5,repeat:-1,yoyo:true},{27});'''),

    # 7: circle closing in (containment)
    ("contain", "linear-gradient(135deg,#051005 0%,#051005 50%,#050510 100%)",
     '''<div id="s7-c1" class="ring" style="width:400px;height:400px;left:340px;top:760px;border-color:rgba(0,255,100,0.3);border-width:3px"></div>
<div id="s7-c2" class="ring" style="width:500px;height:500px;left:290px;top:710px;border-color:rgba(0,255,100,0.15);border-width:2px"></div>
<div id="s7-c3" class="ring" style="width:600px;height:600px;left:240px;top:660px;border-color:rgba(0,255,100,0.08);border-width:1px"></div>
<div id="s7-dot" class="dot" style="width:10px;height:10px;left:535px;top:955px;background:#00ff64"></div>''',
     '''tl.fromTo("#s7-c1",{scale:1.5,opacity:0},{scale:1,opacity:1,duration:1,ease:"power2.out"},{31.6});
tl.fromTo("#s7-c2",{scale:1.5,opacity:0},{scale:1,opacity:1,duration:1,ease:"power2.out"},{31.8});
tl.fromTo("#s7-c3",{scale:1.5,opacity:0},{scale:1,opacity:1,duration:1,ease:"power2.out"},{32});
tl.fromTo("#s7-dot",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"},{32.5});'''),

    # 8: opposing forces
    ("oppose", "linear-gradient(135deg,#0a0a10 0%,#1a0510 50%,#0a0a10 100%)",
     '''<div id="s8-left" class="rect" style="width:80px;height:80px;left:340px;top:920px;border:3px solid rgba(255,50,50,0.5);border-radius:10px"></div>
<div id="s8-right" class="rect" style="width:80px;height:80px;left:660px;top:920px;border:3px solid rgba(50,100,255,0.5);border-radius:10px"></div>
<div id="s8-line" class="line" style="width:240px;height:3px;left:420px;top:960px;background:linear-gradient(90deg,rgba(255,50,50,0.4),rgba(50,100,255,0.4))"></div>''',
     '''tl.fromTo("#s8-left",{x:-40,opacity:0},{x:0,opacity:1,duration:0.5,ease:"back.out(2)"},{34.5});
tl.fromTo("#s8-right",{x:40,opacity:0},{x:0,opacity:1,duration:0.5,ease:"back.out(2)"},{34.5});
tl.fromTo("#s8-line",{scaleX:0,opacity:0,transformOrigin:"center center"},{scaleX:1,opacity:1,duration:0.5},{35});
tl.to("#s8-left",{x:-15,duration:2,repeat:-1,yoyo:true,ease:"sine.inOut"},{36});
tl.to("#s8-right",{x:15,duration:2,repeat:-1,yoyo:true,ease:"sine.inOut"},{36});'''),

    # 9: spotlights (conference)
    ("spotlights", "linear-gradient(135deg,#100510 0%,#201020 50%,#100510 100%)",
     '''<div id="s9-s1" class="line" style="width:500px;height:4px;left:290px;top:960px;background:linear-gradient(90deg,transparent,rgba(255,200,100,0.5),transparent)"></div>
<div id="s9-s2" class="line" style="width:400px;height:3px;left:340px;top:920px;background:linear-gradient(90deg,transparent,rgba(255,200,100,0.3),transparent)"></div>
<div id="s9-s3" class="line" style="width:300px;height:2px;left:390px;top:1000px;background:linear-gradient(90deg,transparent,rgba(255,200,100,0.2),transparent)"></div>
<div id="s9-glow" class="shape" style="width:300px;height:300px;left:390px;top:810px;background:radial-gradient(circle,rgba(255,200,100,0.06) 0%,transparent 70%)"></div>''',
     '''tl.fromTo("#s9-glow",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.8},{39.7});
tl.fromTo("#s9-s1",{scaleX:0,opacity:0,transformOrigin:"center center"},{scaleX:1,opacity:1,duration:0.6},{40});
tl.fromTo("#s9-s2",{scaleX:0,opacity:0,transformOrigin:"center center"},{scaleX:1,opacity:1,duration:0.5},{40.5});
tl.fromTo("#s9-s3",{scaleX:0,opacity:0,transformOrigin:"center center"},{scaleX:1,opacity:1,duration:0.4},{41});
tl.to("#s9-s1",{width:600,duration:2,repeat:-1,yoyo:true,ease:"sine.inOut"},{41.5});'''),

    # 10: question mark
    ("question", "linear-gradient(135deg,#0a0a10 0%,#101020 50%,#0a0a10 100%)",
     '''<div id="s10-q" class="shape" style="width:100px;height:100px;left:490px;top:910px;border:3px solid rgba(255,200,100,0.5);border-radius:50%"></div>
<div id="s10-qdot" class="dot" style="width:14px;height:14px;left:540px;top:1030px;background:rgba(255,200,100,0.5)"></div>''',
     '''tl.fromTo("#s10-q",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"},{44.4});
tl.fromTo("#s10-qdot",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.3},{44.8});
tl.to("#s10-q",{scale:1.1,duration:0.8,repeat:-1,yoyo:true,ease:"sine.inOut"},{45.2});'''),

    # 11: portal opening
    ("portal", "linear-gradient(135deg,#051010 0%,#051020 50%,#051010 100%)",
     '''<div id="s11-portal" class="rect" style="width:200px;height:340px;left:440px;top:790px;border:2px solid rgba(0,200,255,0.4);border-radius:100px 100px 0 0"></div>
<div id="s11-glow" class="shape" style="width:300px;height:300px;left:390px;top:810px;background:radial-gradient(circle,rgba(0,200,255,0.08) 0%,transparent 70%)"></div>''',
     '''tl.fromTo("#s11-portal",{scaleY:0,opacity:0,transformOrigin:"bottom center"},{scaleY:1,opacity:1,duration:0.6,ease:"back.out(2)"},{46.1});
tl.fromTo("#s11-glow",{scale:0,opacity:0},{scale:2,opacity:1,duration:1},{46});
tl.to("#s11-portal",{borderColor:"rgba(0,200,255,0.8)",duration:0.8,repeat:-1,yoyo:true},{47});'''),

    # 12: phone with radar pulses
    ("phone", "linear-gradient(135deg,#051020 0%,#051005 50%,#051020 100%)",
     '''<div id="s12-phone" class="rect" style="width:100px;height:180px;left:490px;top:870px;border:2px solid rgba(0,150,255,0.5);border-radius:12px"></div>
<div id="s12-scr" class="rect" style="width:80px;height:140px;left:500px;top:885px;border:1px solid rgba(0,150,255,0.2);border-radius:6px"></div>
<div id="s12-pulse1" class="ring" style="width:200px;height:200px;left:440px;top:860px;border-color:rgba(0,150,255,0.2);border-width:2px"></div>
<div id="s12-pulse2" class="ring" style="width:300px;height:300px;left:390px;top:810px;border-color:rgba(0,150,255,0.1);border-width:1px"></div>
<div id="s12-pulse3" class="ring" style="width:400px;height:400px;left:340px;top:760px;border-color:rgba(0,150,255,0.06);border-width:1px"></div>''',
     '''tl.fromTo("#s12-phone",{scale:0.5,opacity:0,rotation:-15},{scale:1,opacity:1,rotation:0,duration:0.5,ease:"back.out(2)"},{50});
tl.fromTo("#s12-scr",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.3},{50.5});
tl.fromTo("#s12-pulse1",{scale:0.3,opacity:0},{scale:1,opacity:0.8,duration:0.6},{51});
tl.to("#s12-pulse1",{scale:1.8,opacity:0,duration:2,repeat:-1},{51.5});
tl.fromTo("#s12-pulse2",{scale:0.3,opacity:0},{scale:1,opacity:0.6,duration:0.8},{52});
tl.to("#s12-pulse2",{scale:1.5,opacity:0,duration:2.5,repeat:-1},{52.5});
tl.fromTo("#s12-pulse3",{scale:0.3,opacity:0},{scale:1,opacity:0.4,duration:1},{53});
tl.to("#s12-pulse3",{scale:1.3,opacity:0,duration:3,repeat:-1},{53.5});'''),

    # 13: brain + robotic arm
    ("bci", "linear-gradient(135deg,#0a0510 0%,#051005 50%,#0a0510 100%)",
     '''<div id="s13-brain" class="shape" style="width:140px;height:140px;left:400px;top:880px;border:2px solid rgba(200,0,255,0.3);border-radius:50%"></div>
<div id="s13-arm-base" class="rect" style="width:120px;height:20px;left:620px;top:930px;background:rgba(200,100,255,0.2);border-radius:6px"></div>
<div id="s13-arm-grip" class="rect" style="width:60px;height:30px;left:650px;top:940px;background:rgba(200,100,255,0.3);border-radius:4px"></div>
<div id="s13-signal1" class="line" style="width:120px;height:2px;left:540px;top:930px;background:rgba(200,0,255,0.2)"></div>
<div id="s13-signal2" class="line" style="width:80px;height:2px;left:560px;top:950px;background:rgba(200,0,255,0.15)"></div>
<div id="s13-signal3" class="line" style="width:100px;height:2px;left:550px;top:970px;background:rgba(200,0,255,0.1)"></div>''',
     '''tl.fromTo("#s13-brain",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.5,ease:"back.out(2)"},{60.2});
tl.fromTo("#s13-signal1",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.4},{60.8});
tl.fromTo("#s13-signal2",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.4},{61.2});
tl.fromTo("#s13-signal3",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.4},{61.6});
tl.fromTo("#s13-arm-base",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.5},{62});
tl.fromTo("#s13-arm-grip",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.4},{62.5});'''),

    # 14: bar chart (Gartner forecast)
    ("barchart", "linear-gradient(135deg,#051005 0%,#0a1005 50%,#051005 100%)",
     '''<div id="s14-b1" class="bar" style="width:50px;height:60px;left:330px;top:1000px;background:rgba(0,200,120,0.5);border-radius:4px"></div>
<div id="s14-b2" class="bar" style="width:50px;height:100px;left:400px;top:960px;background:rgba(0,200,120,0.6);border-radius:4px"></div>
<div id="s14-b3" class="bar" style="width:50px;height:180px;left:470px;top:880px;background:rgba(0,200,120,0.8);border-radius:4px"></div>
<div id="s14-b4" class="bar" style="width:50px;height:140px;left:540px;top:920px;background:rgba(0,200,120,0.6);border-radius:4px"></div>
<div id="s14-b5" class="bar" style="width:50px;height:80px;left:610px;top:980px;background:rgba(0,200,120,0.5);border-radius:4px"></div>
<div id="s14-base" class="line" style="width:380px;height:3px;left:310px;top:1060px;background:rgba(0,200,120,0.3)"></div>''',
     '''tl.fromTo("#s14-base",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.4},{66.1});
tl.fromTo("#s14-b1",{scaleY:0,opacity:0,transformOrigin:"bottom center"},{scaleY:1,opacity:1,duration:0.3},{66.3});
tl.fromTo("#s14-b2",{scaleY:0,opacity:0,transformOrigin:"bottom center"},{scaleY:1,opacity:1,duration:0.3},{66.6});
tl.fromTo("#s14-b3",{scaleY:0,opacity:0,transformOrigin:"bottom center"},{scaleY:1,opacity:1,duration:0.3},{66.9});
tl.fromTo("#s14-b4",{scaleY:0,opacity:0,transformOrigin:"bottom center"},{scaleY:1,opacity:1,duration:0.3},{67.2});
tl.fromTo("#s14-b5",{scaleY:0,opacity:0,transformOrigin:"bottom center"},{scaleY:1,opacity:1,duration:0.3},{67.5});'''),

    # 15: number counter (64 billion)
    ("counter", "linear-gradient(135deg,#050510 0%,#051020 50%,#050510 100%)",
     '''<div id="s15-box" class="rect" style="width:400px;height:200px;left:340px;top:860px;border:2px solid rgba(0,200,255,0.2);border-radius:20px"></div>
<div id="s15-bar" class="bar" style="width:360px;height:50px;left:360px;top:960px;background:rgba(0,200,255,0.3);border-radius:8px"></div>
<div id="s15-bar2" class="bar" style="width:240px;height:50px;left:360px;top:960px;background:rgba(0,255,200,0.5);border-radius:8px"></div>''',
     '''tl.fromTo("#s15-box",{scale:0.5,opacity:0},{scale:1,opacity:1,duration:0.5,ease:"back.out(2)"},{70.5});
tl.fromTo("#s15-bar",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.8,ease:"power2.out"},{71});
tl.fromTo("#s15-bar2",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:0.67,opacity:1,duration:1.5,ease:"power2.out"},{72});
tl.to("#s15-box",{borderColor:"rgba(0,255,200,0.5)",duration:0.6},{74});'''),

    # 16: blocks connecting with chains
    ("blocks", "linear-gradient(135deg,#0a0a10 0%,#101005 50%,#0a0a10 100%)",
     '''<div id="s16-b1" class="rect" style="width:90px;height:90px;left:340px;top:870px;border:2px solid rgba(255,150,0,0.4);border-radius:8px"></div>
<div id="s16-b2" class="rect" style="width:90px;height:90px;left:450px;top:870px;border:2px solid rgba(255,150,0,0.3);border-radius:8px"></div>
<div id="s16-b3" class="rect" style="width:90px;height:90px;left:560px;top:870px;border:2px solid rgba(255,150,0,0.2);border-radius:8px"></div>
<div id="s16-ch1" class="line" style="width:20px;height:3px;left:430px;top:915px;background:rgba(255,150,0,0.4)"></div>
<div id="s16-ch2" class="line" style="width:20px;height:3px;left:540px;top:915px;background:rgba(255,150,0,0.3)"></div>
<div id="s16-fence" class="rect" style="width:400px;height:10px;left:340px;top:1020px;background:rgba(255,150,0,0.15);border-radius:5px"></div>''',
     '''tl.fromTo("#s16-b1",{scale:0,opacity:0,rotation:-20},{scale:1,opacity:1,rotation:0,duration:0.4,ease:"back.out(2)"},{80.6});
tl.fromTo("#s16-b2",{scale:0,opacity:0,rotation:20},{scale:1,opacity:1,rotation:0,duration:0.4,ease:"back.out(2)"},{81});
tl.fromTo("#s16-b3",{scale:0,opacity:0,rotation:-15},{scale:1,opacity:1,rotation:0,duration:0.4,ease:"back.out(2)"},{81.4});
tl.fromTo("#s16-ch1",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.3},{81.8});
tl.fromTo("#s16-ch2",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.3},{82.2});
tl.fromTo("#s16-fence",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.5},{83});'''),

    # 17: magnifying glass
    ("magnify", "linear-gradient(135deg,#100510 0%,#100510 50%,#100510 100%)",
     '''<div id="s17-glass" class="shape" style="width:130px;height:130px;left:475px;top:895px;border:3px solid rgba(255,80,200,0.4);border-radius:50%"></div>
<div id="s17-handle" class="line" style="width:60px;height:4px;left:575px;top:1010px;background:rgba(255,80,200,0.3);transform:rotate(-45deg);border-radius:2px"></div>
<div id="s17-ripple" class="ring" style="width:200px;height:200px;left:440px;top:860px;border-color:rgba(255,80,200,0.1);border-width:1px"></div>''',
     '''tl.fromTo("#s17-glass",{scale:0.5,opacity:0},{scale:1,opacity:1,duration:0.5,ease:"back.out(2)"},{89.1});
tl.fromTo("#s17-handle",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.4},{89.6});
tl.fromTo("#s17-ripple",{scale:0.3,opacity:0},{scale:1,opacity:0.5,duration:0.6},{90});
tl.to("#s17-ripple",{scale:1.5,opacity:0,duration:2,repeat:-1},{90.5});
tl.to("#s17-glass",{x:15,y:-15,duration:3,repeat:-1,yoyo:true,ease:"sine.inOut"},{91});'''),

    # 18: scan line (forensic)
    ("scan", "linear-gradient(135deg,#050510 0%,#051010 50%,#050510 100%)",
     '''<div id="s18-scanner" class="rect" style="width:500px;height:220px;left:290px;top:850px;border:1px solid rgba(0,255,200,0.2);border-radius:10px"></div>
<div id="s18-scanline" class="line" style="width:480px;height:3px;left:300px;top:870px;background:rgba(0,255,200,0.6);border-radius:2px"></div>''',
     '''tl.fromTo("#s18-scanner",{scaleX:0,opacity:0,transformOrigin:"left center"},{scaleX:1,opacity:1,duration:0.5},{92.2});
tl.fromTo("#s18-scanline",{y:0,opacity:0},{y:180,opacity:1,duration:3},{92.5});
tl.to("#s18-scanline",{y:0,duration:3,repeat:-1,ease:"power1.inOut"},{95.5});'''),

    # 19: data stream / matrix-like
    ("datastream", "linear-gradient(135deg,#051005 0%,#050510 50%,#051005 100%)",
     '''<div id="s19-d1" class="line" style="width:2px;height:300px;left:320px;top:800px;background:linear-gradient(to bottom,rgba(0,255,100,0.3),transparent)"></div>
<div id="s19-d2" class="line" style="width:2px;height:250px;left:440px;top:800px;background:linear-gradient(to bottom,rgba(0,255,100,0.2),transparent)"></div>
<div id="s19-d3" class="line" style="width:2px;height:280px;left:560px;top:800px;background:linear-gradient(to bottom,rgba(0,255,100,0.25),transparent)"></div>
<div id="s19-d4" class="line" style="width:2px;height:220px;left:680px;top:800px;background:linear-gradient(to bottom,rgba(0,255,100,0.15),transparent)"></div>''',
     '''tl.fromTo("#s19-d1",{scaleY:0,opacity:0,transformOrigin:"top center"},{scaleY:1,opacity:1,duration:0.4},{98.7});
tl.fromTo("#s19-d2",{scaleY:0,opacity:0,transformOrigin:"top center"},{scaleY:1,opacity:1,duration:0.4},{99.2});
tl.fromTo("#s19-d3",{scaleY:0,opacity:0,transformOrigin:"top center"},{scaleY:1,opacity:1,duration:0.4},{99.7});
tl.fromTo("#s19-d4",{scaleY:0,opacity:0,transformOrigin:"top center"},{scaleY:1,opacity:1,duration:0.4},{100.2});
tl.to("#s19-d1",{scaleY:0.5,duration:1,repeat:-1,yoyo:true,ease:"sine.inOut"},{101});
tl.to("#s19-d2",{scaleY:1.3,duration:1.2,repeat:-1,yoyo:true,ease:"sine.inOut"},{101});
tl.to("#s19-d3",{scaleY:0.6,duration:0.8,repeat:-1,yoyo:true,ease:"sine.inOut"},{101});
tl.to("#s19-d4",{scaleY:1.2,duration:1.1,repeat:-1,yoyo:true,ease:"sine.inOut"},{101});'''),

    # 20: fast rotating squares
    ("fast", "linear-gradient(135deg,#0a0a0a 0%,#1a1005 50%,#0a0a0a 100%)",
     '''<div id="s20-r1" class="rect" style="width:70px;height:70px;left:390px;top:880px;border:2px solid rgba(255,180,50,0.5);border-radius:6px"></div>
<div id="s20-r2" class="rect" style="width:60px;height:60px;left:530px;top:890px;border:2px solid rgba(255,100,50,0.4);border-radius:6px"></div>
<div id="s20-r3" class="rect" style="width:50px;height:50px;left:470px;top:830px;border:2px solid rgba(255,220,50,0.3);border-radius:6px"></div>''',
     '''tl.fromTo("#s20-r1",{scale:0,opacity:0,rotation:-90},{scale:1,opacity:1,rotation:0,duration:0.3,ease:"back.out(2)"},{107});
tl.fromTo("#s20-r2",{scale:0,opacity:0,rotation:90},{scale:1,opacity:1,rotation:0,duration:0.3,ease:"back.out(2)"},{107.3});
tl.fromTo("#s20-r3",{scale:0,opacity:0,rotation:-60},{scale:1,opacity:1,rotation:0,duration:0.3,ease:"back.out(2)"},{107.6});
tl.to("#s20-r1",{rotation:360,duration:2,repeat:-1,ease:"linear"},{108});
tl.to("#s20-r2",{rotation:-360,duration:1.8,repeat:-1,ease:"linear"},{108});
tl.to("#s20-r3",{rotation:180,duration:1.5,repeat:-1,yoyo:true,ease:"sine.inOut"},{108});'''),

    # 21: generative color explosion
    ("colors", "linear-gradient(135deg,#0a000a 0%,#100520 50%,#0a000a 100%)",
     '''<div id="s21-c1" class="shape" style="width:200px;height:200px;left:340px;top:760px;background:radial-gradient(circle,rgba(255,50,150,0.2) 0%,transparent 70%)"></div>
<div id="s21-c2" class="shape" style="width:160px;height:160px;left:550px;top:800px;background:radial-gradient(circle,rgba(50,255,150,0.15) 0%,transparent 70%)"></div>
<div id="s21-c3" class="shape" style="width:140px;height:140px;left:400px;top:1020px;background:radial-gradient(circle,rgba(50,150,255,0.15) 0%,transparent 70%)"></div>''',
     '''tl.fromTo("#s21-c1",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.6},{111});
tl.fromTo("#s21-c2",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.6},{111.3});
tl.fromTo("#s21-c3",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.6},{111.6});
tl.to("#s21-c1",{x:40,y:-30,duration:3,repeat:-1,yoyo:true,ease:"sine.inOut"},{112});
tl.to("#s21-c2",{x:-40,y:30,duration:3.5,repeat:-1,yoyo:true,ease:"sine.inOut"},{112});
tl.to("#s21-c3",{x:30,y:40,duration:2.5,repeat:-1,yoyo:true,ease:"sine.inOut"},{112});'''),

    # 22: flash burst (Gemini)
    ("flash", "linear-gradient(135deg,#0a0a20 0%,#101030 50%,#0a0a20 100%)",
     '''<div id="s22-flash" class="shape" style="width:350px;height:350px;left:365px;top:785px;background:radial-gradient(circle,rgba(255,255,220,0.12) 0%,transparent 70%)"></div>
<div id="s22-core" class="shape" style="width:80px;height:80px;left:500px;top:920px;background:radial-gradient(circle,rgba(255,255,220,0.25) 0%,transparent 70%)"></div>
<div id="s22-ray" class="line" style="width:500px;height:2px;left:290px;top:960px;background:linear-gradient(90deg,transparent,rgba(220,220,255,0.5),transparent)"></div>''',
     '''tl.fromTo("#s22-flash",{scale:0,opacity:0},{scale:2,opacity:1,duration:0.4},{121.5});
tl.fromTo("#s22-core",{scale:0,opacity:0},{scale:2,opacity:1,duration:0.3,ease:"back.out(2)"},{121.5});
tl.fromTo("#s22-ray",{scaleX:0,opacity:0,transformOrigin:"center center"},{scaleX:1,opacity:1,duration:0.3},{121.8});
tl.to("#s22-flash",{opacity:0,duration:0.3},{122.5});
tl.to("#s22-core",{scale:3,opacity:0,duration:0.3},{122.5});'''),

    # 23: two entities merging
    ("merge", "linear-gradient(135deg,#051010 0%,#101005 50%,#051010 100%)",
     '''<div id="s23-a" class="circle" style="width:100px;height:100px;left:340px;top:900px;border:3px solid rgba(0,150,255,0.5);border-radius:50%"></div>
<div id="s23-b" class="circle" style="width:100px;height:100px;left:640px;top:900px;border:3px solid rgba(255,150,0,0.5);border-radius:50%"></div>
<div id="s23-merge-line" class="line" style="width:200px;height:2px;left:440px;top:950px;background:linear-gradient(90deg,rgba(0,150,255,0.4),rgba(255,150,0,0.4))"></div>
<div id="s23-glow" class="shape" style="width:120px;height:120px;left:480px;top:900px;background:radial-gradient(circle,rgba(255,200,100,0.06) 0%,transparent 70%)"></div>''',
     '''tl.fromTo("#s23-a",{x:-30,opacity:0},{x:0,opacity:1,duration:0.5,ease:"back.out(2)"},{125.5});
tl.fromTo("#s23-b",{x:30,opacity:0},{x:0,opacity:1,duration:0.5,ease:"back.out(2)"},{125.5});
tl.fromTo("#s23-merge-line",{scaleX:0,opacity:0,transformOrigin:"center center"},{scaleX:1,opacity:1,duration:0.5},{126});
tl.fromTo("#s23-glow",{scale:0,opacity:0},{scale:2,opacity:1,duration:1},{127});
tl.to(["#s23-a","#s23-b"],{x:60,duration:3,repeat:-1,yoyo:true,ease:"sine.inOut"},{128});'''),

    # 24: converging lines (wrap up)
    ("converge", "linear-gradient(135deg,#0a0a0a 0%,#0a0510 50%,#0a0a0a 100%)",
     '''<div id="s24-c1" class="line" style="width:450px;height:3px;left:100px;top:960px;background:linear-gradient(90deg,rgba(200,180,100,0.2),transparent)"></div>
<div id="s24-c2" class="line" style="width:350px;height:2px;left:200px;top:980px;background:linear-gradient(90deg,rgba(200,180,100,0.15),transparent)"></div>
<div id="s24-c3" class="line" style="width:250px;height:2px;left:300px;top:1000px;background:linear-gradient(90deg,rgba(200,180,100,0.1),transparent)"></div>''',
     '''tl.fromTo("#s24-c1",{scaleX:0,opacity:0,transformOrigin:"right center"},{scaleX:1,opacity:1,duration:0.5},{133});
tl.fromTo("#s24-c2",{scaleX:0,opacity:0,transformOrigin:"right center"},{scaleX:1,opacity:1,duration:0.4},{133.3});
tl.fromTo("#s24-c3",{scaleX:0,opacity:0,transformOrigin:"right center"},{scaleX:1,opacity:1,duration:0.3},{133.6});'''),

    # 25: expanding rings (goodbye)
    ("rings", "linear-gradient(135deg,#050505 0%,#050510 50%,#050505 100%)",
     '''<div id="s25-r1" class="ring" style="width:450px;height:450px;left:315px;top:735px;border-color:rgba(180,180,255,0.1);border-width:1px"></div>
<div id="s25-r2" class="ring" style="width:300px;height:300px;left:390px;top:810px;border-color:rgba(180,180,255,0.07);border-width:1px"></div>
<div id="s25-r3" class="ring" style="width:150px;height:150px;left:465px;top:885px;border-color:rgba(180,180,255,0.04);border-width:1px"></div>''',
     '''tl.fromTo("#s25-r1",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.6},{135.6});
tl.fromTo("#s25-r2",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.6},{135.8});
tl.fromTo("#s25-r3",{scale:0,opacity:0},{scale:1,opacity:1,duration:0.6},{136});
tl.to("#s25-r1",{scale:1.3,opacity:0.3,duration:3,repeat:-1,yoyo:true,ease:"sine.inOut"},{136.5});
tl.to("#s25-r2",{scale:1.2,opacity:0.2,duration:3.5,repeat:-1,yoyo:true,ease:"sine.inOut"},{136.5});'''),
]

scene_html = ""
tl_entries = ""

for idx, seg in enumerate(segments):
    sid = f"s{idx+1}"
    s = seg['start']
    d = round(seg['end'] - seg['start'] + 0.2, 2)
    name, bg, shapes, anim = visuals[idx]

    scene_html += f'''
    <section id="{sid}" class="clip scene" data-start="{s}" data-duration="{d}" data-track-index="{idx+1}">
        <div class="bg" style="background: {bg}"></div>
        <div class="gfx" style="position:absolute;top:0;left:0;width:1080px;height:1920px;transform:scale(1.6);transform-origin:540px 960px">
        {shapes}
        </div>
    </section>'''

    tl_entries += anim

html = f'''<!doctype html>
<html lang="en" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
.scene {{ width: 1080px; height: 1920px; position: absolute; top: 0; left: 0; overflow:hidden; }}
.bg {{ position: absolute; top: 0; left: 0; width: 1080px; height: 1920px; }}
.shape {{ position: absolute; border-radius: 50%; }}
.rect {{ border-radius: 0; }}
.circle {{ position: absolute; }}
.line {{ position: absolute; }}
.ring {{ position: absolute; border-radius: 50%; border-style: solid; }}
.dot {{ position: absolute; border-radius: 50%; }}
.bar {{ position: absolute; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total_dur}" data-width="1080" data-height="1920">
{scene_html}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{tl_entries}
window.__timelines["main"] = tl;
</script>
</body>
</html>'''

import re
# Fix: unwrap numeric position args wrapped in {} -> tl.fn(... ,{0.5}) -> tl.fn(... ,0.5)
html = re.sub(r',\{(\d+(?:\.\d+)?)\}', r',\1', html)

with open(OUTPUT_HTML, 'w') as f:
    f.write(html)

print(f'HTML: {OUTPUT_HTML} ({len(segments)} scenes)')
