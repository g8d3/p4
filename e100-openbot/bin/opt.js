return [...document.querySelectorAll("[role=option],[role=listbox] *")].map(e=>e.innerText).filter(t=>t&&/zhipu|zai|GLM-5.3 Flash/i.test(t)).slice(0,10).join(" | ")
