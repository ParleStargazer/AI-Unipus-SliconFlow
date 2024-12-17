import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from pydub import AudioSegment
import speech_recognition as sr
from openai import OpenAI

client = OpenAI(
    api_key="",  # 替换为你的API Key
    base_url="https://api.moonshot.cn/v1",
)

WebsiteAddress = input("输入网址:")
print("输入的网址是:%s" % WebsiteAddress)

# 创建一个 Chrome 浏览器的实例
s = Service("/usr/bin/chromedriver")

print("打开浏览器")
driver = webdriver.Chrome(service=s)

print("打开网页")
driver.get(WebsiteAddress)

time.sleep(2)

print("登陆")
driver.find_element(By.NAME, "username").send_keys("")# username
driver.find_element(By.NAME, "password").send_keys("")# password
driver.find_element(By.ID, "agreement").click()
driver.find_element(By.ID, "login").click()

time.sleep(5)

# 获取页面完整的HTML内容
print("获取页面完整的HTML内容")
WebsiteData = driver.page_source
ReplyWrapData = driver.find_element(By.CLASS_NAME, "reply-wrap")

# 获取mp3路径
print("获取mp3路径")
match = re.search(r'src="([^"]+?)(\.mp3)(#|")', WebsiteData)
mp3_url = match.group(1)
mp3_url = mp3_url + ".mp3"

# 下载mp3文件
print("下载mp3文件")
mp3_data = requests.get(mp3_url, stream=True)
with open("Temp.mp3", 'wb') as f:
        # 循环下载文件
        for chunk in mp3_data.iter_content(chunk_size=8192):
            # 过滤掉保持连接的chunk
            if chunk:
                f.write(chunk)

# mp3 to wav
print("获取WAV格式音频")
Audio = AudioSegment.from_file("Temp.mp3", format="mp3")
WavPath = "Temp.wav"
Audio.export(WavPath, format="wav")

# Get Text 
print("正在进行语音识别(可能要1分钟左右)")
AudioFile = sr.AudioFile(WavPath)
r = sr.Recognizer()
with AudioFile as source:
   AudioData = r.record(source)

said = r.recognize_google(AudioData, language='en-US')
print("语音识别成功")

Question = "给出答案并且说明原因\n"
Question += said + ReplyWrapData.text

# 向kimi提问
print("正在等待KIMI回答")
completion = client.chat.completions.create(
    model="moonshot-v1-8k",  # 你可以根据需要选择不同的模型版本
    messages=[
        {"role": "system", "content": "你是Kimi,由Moonshot AI提供的人工智能助手..."},
        {"role": "user", "content": Question}
    ],
    temperature=0.3,
)

print("以下为答案:")
print(completion.choices[0].message.content)

# 关闭浏览器
driver.quit()
