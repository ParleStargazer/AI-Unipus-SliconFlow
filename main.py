import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from pydub import AudioSegment
import speech_recognition as sr
from openai import OpenAI


KimiClient = OpenAI(
    api_key="",  # 替换为你的API Key
    base_url="https://api.moonshot.cn/v1",
)

# GLM4Client = OpenAI(
#     api_key="",
#     base_url="https://open.bigmodel.cn/api/paas/v4/"
# ) 

# 创建一个 Chrome 浏览器的实例
s = Service("/usr/bin/chromedriver")

print("打开浏览器")
driver = webdriver.Chrome(service=s)

print("打开网页")
driver.get("https://ucloud.unipus.cn/home")

time.sleep(2)

print("登陆")
driver.find_element(By.NAME, "username").send_keys("")
driver.find_element(By.NAME, "password").send_keys("")
driver.find_element(By.ID, "login").click()
time.sleep(0.5)
driver.find_element(By.CLASS_NAME, "layui-layer-btn0").click()

while 1:
    IsInRightWebsite = input("是否进入正确页面(Y/n):")
    if IsInRightWebsite != "y" and IsInRightWebsite != "Y" and IsInRightWebsite != None:
        continue
    
    WebsiteAddress2 = driver.current_url
    print("网址是:%s" % WebsiteAddress2)
    driver.get(WebsiteAddress2)
    
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
    print("正在进行语音识别(可能要1分钟)")
    AudioFile = sr.AudioFile(WavPath)
    r = sr.Recognizer()
    with AudioFile as source:
        AudioData = r.record(source)

    said = r.recognize_google(AudioData, language='en-US')
    print("语音识别成功")

    Question = "给出答案并且说明原因,注意每题有且仅有一个正确答案.注意在最后,你必须一定要以[答案,答案,答案,答案,....]的格式,在一个[]内给出所有答案,例如[A,B], [A,B,C] [A,B,C,D]\n"
    Question += said + ReplyWrapData.text

    # 向kimi提问
    print("正在等待KIMI回答")
    KIMIResponse = KimiClient.chat.completions.create(
        model="moonshot-v1-8k",  # 你可以根据需要选择不同的模型版本
        messages=[
            {"role": "system", "content": "你是一个聪明且仔细的英语老师,擅长做英语题目,在题目的最后你会以[答案,答案,答案,答案,....]的格式,在一个[]内给出所有答案"},
            {"role": "user", "content": Question}
        ],
        temperature = 0.2,
    )
    
    # # 向GLM4提问
    # print("正在等待GLM4回答")
    # GLM4Response = GLM4Client.chat.completions.create(
    # model="glm-4-airx",  # 请填写您要调用的模型名称
    #     messages=[    
    #             {"role": "system", "content": "你是一个聪明且仔细的英语老师,擅长做英语题目,在题目的最后你会以[答案,答案,答案,答案,....]的格式,在一个[]内给出所有答案"},
    #             {"role": "user", "content": Question} 
    #         ],
    #     top_p=0.7,
    #     temperature=0.9
    # )
    
    print("以下为KIMI答案:")
    print(KIMIResponse.choices[0].message.content)
    # print("以下为GLM4答案:")
    # print(GLM4Response.choices[0].message.content)
    print("---------------------------")

    # Anspattern = r'\[([A-Z]+(?:,\s*[A-Z]+)*)\]'
    Anspattern = r'\[([A-Z]+(?:,\s*[A-Z]+)*)\]'
    KIMIFinalAns = re.search(Anspattern, KIMIResponse.choices[0].message.content)
    # GLM4FinalAns = re.search(Anspattern, GLM4Response.choices[0].message.content)

    # 打印结果
    print("KIMI最终答案:")
    print(KIMIFinalAns.group(1).replace(" ", ""))
    # print("GLM4最终答案:")
    # print(GLM4FinalAns.group(1))
    
    #自动输入
    TempStr = KIMIFinalAns.group(1)
    TempStr = TempStr.strip("[]")
    TempStr = TempStr.strip(",")
    for t in TempStr:
        print(t)
    
# 关闭浏览器
# driver.quit()

# time.sleep(20)
