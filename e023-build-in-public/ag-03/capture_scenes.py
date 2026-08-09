import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# Setup Chrome headless
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--user-data-dir=/tmp/chrome-video-render')
driver = webdriver.Chrome(options=chrome_options)

scenes = []
for i in range(1, 7):
    # Navigate to the HTML with that scene active
    driver.get(f'file:///home/vuos/code/p4/e023-build-in-public/ag-03/output/video.html?scene={i}')
    time.sleep(1)

    # Execute script to show only that scene
    driver.execute_script(f'''
        document.querySelectorAll('.scene').forEach(s => s.classList.remove('active'));
        document.getElementById('scene{i}').classList.add('active');
    ''')
    time.sleep(0.5)

    # Capture screenshot
    driver.save_screenshot(f'/tmp/scene{i}.png')
    scenes.append(f'/tmp/scene{i}.png')
    print(f"Captured scene {i}")

driver.quit()
print(f"Captured {len(scenes)} scenes: {scenes}")