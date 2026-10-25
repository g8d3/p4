return [...document.querySelectorAll("textarea")].map(t=>t.value.length+":"+t.value.slice(-60)).join(" | ")
