import time
import re
import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from pydub import AudioSegment
from openai import OpenAI
import whisper
from reloading import reloading

from secret import username, password, api_key


def download_media(url):
    file_extension = os.path.splitext(url)[-1].lower()
    file_path = f"./.cache/Temp{file_extension}"
    print(f"下载文件 {file_extension}")
    response = requests.get(url, stream=True)
    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return [file_path, file_extension]


def export_wav(file_path, file_extension):
    print("尝试转换为WAV格式音频")
    if file_extension == ".mp3":
        audio = AudioSegment.from_file(file_path, format="mp3")
    elif file_extension == ".mp4":
        audio = AudioSegment.from_file(file_path, format="mp4")
    else:
        raise ValueError(f"不支持的文件格式: {file_extension}")
    audio.export("./.cache/Temp.wav", format="wav")
    print("成功转换为WAV格式音频")


KimiClient = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")

print("正在载入whisper模型")
model = whisper.load_model("base")

print("正在启动浏览器并自动登录U校园AI板")
driver = webdriver.Edge(
    service=Service(EdgeChromiumDriverManager().install(), log_path="nul"),
    options=Options().add_argument("--disable-logging"),  # 禁用浏览器日志
)
driver.get("https://ucloud.unipus.cn/home")
time.sleep(2)
driver.find_element(By.NAME, "username").send_keys(username)
driver.find_element(By.NAME, "password").send_keys(password)
driver.find_element(By.ID, "login").click()
time.sleep(0.5)
driver.find_element(By.CLASS_NAME, "layui-layer-btn0").click()


@reloading
def main():
    try:
        WebsiteAddress2 = driver.current_url
        print("网址是:%s" % WebsiteAddress2)
        driver.get(WebsiteAddress2)

        if driver.find_elements(By.CLASS_NAME, "question-common-abs-choice"):
            if driver.find_elements(By.CLASS_NAME, "multipleChoice"):
                QuestionType = "多选题"
            else:
                QuestionType = "单选题"
        else:
            if driver.find_elements(By.CLASS_NAME, "question-common-abs-scoop"):
                QuestionType = "填空题"
            elif driver.find_elements(By.CLASS_NAME, "question-inputbox"):
                QuestionType = "回答题"
            else:
                print("不支持的题型!")
                return

        # 获取页面完整的HTML内容
        ReplyContainerData = driver.find_element(By.CLASS_NAME, "layout-reply-container")
        Question = f"以下是题目,本次题目类型为{QuestionType}:\n{ReplyContainerData.text}"
        # print(Question)

        # 获取mp3路径
        match = re.search(r'src="([^"]+\.(mp3|mp4))(#|")', driver.page_source)
        aduio_url = match.group(1)
        # print(aduio_url)

        # 下载并转换为WAV
        if not os.path.exists("./.cache/"):
            print("创建缓存文件夹")
            os.makedirs(".cache")
        file_path, file_extension = download_media(aduio_url)

        print("正在进行语音识别")
        ListeningData = "以下内容是视频或者音频转成的文章内容:\n" + model.transcribe(file_path)["text"]
        print("语音识别完成")

        demand1 = """以形如["","","",""]的格式汇总输出所有答案, 最外围以一对[]包裹整个答案, 内部每题用""围起来, 并以单个','分隔每道题目, 填空题的每一个空视作一道题目, 注意输出格式的准确性, 不要有非法数据与格式, 不要有无效冗余数据, 注意填空题答案不要包含周边的题目"""

        prompt = f"""- Role: 英语文章解析专家和逻辑推理大师
    - Background: 用户需要通过阅读英语文章来解答, 并要求提供正确的答案及其解释和最终所有答案的汇总
    - Profile: 你是一位英语文章解析的专家, 擅长从文章中提取关键信息, 并能够逻辑推理出正确答案
    - Skills: 你拥有阅读理解、信息提取、逻辑推理和批判性思维的能力, 能够准确分析文章内容, 并提供正确的答案及其解释
    - Goals: 阅读并理解英语文章, 准确解答选择题, 并提供正确的答案及其解释, 最后汇总所有答案
    - Constrains: 确保每个问题的答案有且仅有一个正确答案, 并且在最后以特定格式给出所有答案
    - OutputFormat: 不使用markdown语法, 使用一般文字输出; 根据题型返回不同格式的答案及原因, 最后{demand1}
    - AnswerFormat: 单选题: "A", 多选题: "A,B,C,D", 填空题: "now answer", 回答题: "now reply"
    - Workflow:
    1. 仔细阅读并理解题目内容
    2. 针对每个题目, 分析选项与文章内容的关系(如果有选项)
    3. 根据文章内容和逻辑推理, 确定每个问题的正确答案, 并解释为什么
    4. 在解释完所有问题后, {demand1}; 注意每种题型的回答格式: 单选题: "A", 多选题: "A,B,C,D", 填空题: "now answer", 回答题: "now reply"
    5. !!!注意最外围以一对[]包裹整个答案, 多选题的选项是仅以逗号分隔且存放在仅一对引号中的!!!"""

        Direction = "以下是题目的说明, 注意说明中可能包含了答题要求的关键信息, 请优先遵循题目说明中的要求, 所有的视频和音频已经转化成英文文章:\n" + driver.find_element(By.CLASS_NAME, "abs-direction").text
        # print(Direction)

        AIQuestion = f"{prompt}\n{Direction}\n{ListeningData}\n{Question}"
        # print(AIQuestion)

        print("正在等待KIMI回答")
        KIMIResponse = KimiClient.chat.completions.create(
            model="moonshot-v1-8k",  # 你可以根据需要选择不同的模型版本
            messages=[
                {
                    "role": "system",
                    "content": f"""欢迎来到英语文章解析与逻辑推理的世界。请提供一篇英语文章和一些题目, 我将为你解答这些题目并解释; 最后, 我会{demand1}""",
                },
                {"role": "user", "content": AIQuestion},
            ],
            temperature=0.2,
        )

        print(f"以下为KIMI答案:\n{KIMIResponse.choices[0].message.content}\n---------------------------")

        Anspattern = r"\[([^\n]*)\]"
        KIMIFinalAns = re.search(Anspattern, KIMIResponse.choices[0].message.content.replace(" ", ""))
        print(KIMIFinalAns.group(1))
        return

        # 打印结果
        print("KIMI最终答案是:")
        print(KIMIFinalAns.group(1).replace(" ", ""))

        # 自动输入
        # TempStr = KIMIFinalAns.group(1)
        # TempStr = TempStr.strip("""")
        # TempStr = TempStr.strip(",")
        # print(TempStr)
    except Exception as e:
        print(f"Error occurs: {e}")


if __name__ == "__main__":
    while True:
        print ("\n等待下一步操作: [Y]抓取当前页面并分析(default) [Q]关闭浏览器并退出程序")
        Operate = input("Input Operate: ").upper()
        match Operate:
            case "":
                main()
            case "Y":
                main()
            case "Q":
                driver.quit()
                break
            case _:
                print("请输入正确的选项")
