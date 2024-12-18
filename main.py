import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from pydub import AudioSegment
import speech_recognition as sr
from openai import OpenAI
# from zhipuai import ZhipuAI


KimiClient = OpenAI(
    api_key="sk-",  # 替换为你的API Key
    base_url="https://api.moonshot.cn/v1",
)

# GLM4Client = OpenAI(
#     api_key=".",
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
    if IsInRightWebsite != "y" and IsInRightWebsite != "Y" and IsInRightWebsite != "":
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

    prompt = """- Role: 英语文章解析专家和逻辑推理大师
- Background: 用户需要通过阅读英语文章来解答选择题,并要求提供每个选项的解释和最终所有答案的汇总。
- Profile: 你是一位英语文章解析的专家,擅长从文章中提取关键信息,并能够逻辑推理出正确答案。你具备深厚的英语语言知识和批判性思维能力。
- Skills: 你拥有阅读理解、信息提取、逻辑推理和批判性思维的能力,能够准确分析文章内容,并提供每个选项的解释。
- Goals: 阅读并理解英语文章,准确解答选择题,并提供每个选项的解释,最后汇总所有答案。
- Constrains: 确保每个问题的答案有且仅有一个正确答案,并且在最后以特定格式给出所有答案。
- OutputFormat: 提供选择题的答案和每个选项的解释,最后以“[答案,答案,答案,答案,...]”的格式汇总所有答案。
- Workflow:
  1. 仔细阅读并理解英语文章的内容。
  2. 针对每个选择题,分析选项与文章内容的关系。
  3. 根据文章内容和逻辑推理,确定每个问题的正确答案,并解释每个选项。
  4. 在解释完所有问题后,以“[答案,答案,答案,答案,...]”的格式汇总所有答案。
- Examples:
  - 1:文章讨论了全球变暖的影响。
    问题:全球变暖的主要原因是什么？
    选项A:太阳辐射增强
    选项B:工业排放增加
    选项C:人口增长
    选项D:自然气候变化
    解释:根据文章内容,全球变暖的主要原因是工业排放增加,因此正确答案是选项B。选项A、C和D虽然也对气候有一定影响,但不是主要原因。
    2:文章分析了不同国家的教育体系。
    问题:哪个国家的教育体系最注重实践教学？
    选项A:美国
    选项B:英国
    选项C:德国
    选项D:中国
    解释:文章中提到德国的教育体系最注重实践教学,因此正确答案是选项C。其他选项虽然也有实践教学,但不如德国重视。
    答案:[B,C]\n"""

    Question = prompt
    Question += said + ReplyWrapData.text

    # 向kimi提问
    print("正在等待KIMI回答")
    KIMIResponse = KimiClient.chat.completions.create(
        model="moonshot-v1-8k",  # 你可以根据需要选择不同的模型版本
        messages=[
            {"role": "system", "content": "欢迎来到英语文章解析与逻辑推理的世界。请提供一篇英语文章和一个或多个选择题,我将为你解答并解释每个选项。最后,我会以“[答案,答案,答案,答案,...]”的格式给出所有答案。"},
            {"role": "user", "content": Question}
        ],
        temperature = 0.3,
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
    Anspattern = r'\[([A-D](?:,?[A-D]){1,})\]'
    KIMIFinalAns = re.search(Anspattern, KIMIResponse.choices[0].message.content.replace(" ", ""))
    # GLM4FinalAns = re.search(Anspattern, GLM4Response.choices[0].message.content)

    # 打印结果
    print("KIMI最终答案shi :")
    print(KIMIFinalAns.group(1).replace(" ", ""))
    # print("GLM4最终答案:")
    # print(GLM4FinalAns.group(1))
    
    #自动输入
    # TempStr = KIMIFinalAns.group(1)
    # TempStr = TempStr.strip("[]")
    # TempStr = TempStr.strip(",")
    # print(TempStr)
    
# 关闭浏览器
# driver.quit()

# time.sleep(20)
