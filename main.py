import time
import re
import os
import json
import requests
import whisper
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from pydub import AudioSegment
from openai import OpenAI
from reloading import reloading

from secret import username, password, api_key
from prompts import SingleChoiceQuestionPrompt, MultipleChoiceQuestionPrompt, BlankQuestion, InputBoxQuestion


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


def Submit():
    SubmitButton = driver.find_element(By.CLASS_NAME, "btn")
    SubmitButton.click()
    try:
        WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CLASS_NAME, "ant-btn-primary")))
        YesButton = driver.find_element(By.CLASS_NAME, "ant-btn-primary")
        YesButton.click()
    except Exception:
        print("无二次确认")


DeepSeekClient = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

print("正在载入whisper模型")
model = whisper.load_model("base")

print("正在启动浏览器并自动登录U校园AI板")
driver = webdriver.Edge(
    service=Service(EdgeChromiumDriverManager().install(), log_path="nul"),
    options=Options().add_argument("--disable-logging"),  # 禁用浏览器日志
)

driver.get("https://ucloud.unipus.cn/home")
WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.NAME, "username")))
driver.find_element(By.NAME, "username").send_keys(username)
WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.NAME, "password")))
driver.find_element(By.NAME, "password").send_keys(password)
WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, "login")))
driver.find_element(By.ID, "login").click()
WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CLASS_NAME, "layui-layer-btn0")))
driver.find_element(By.CLASS_NAME, "layui-layer-btn0").click()
WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ucm-ant-btn.ucm-ant-btn-round.ucm-ant-btn-primary")))
driver.find_element(By.CSS_SELECTOR, ".ucm-ant-btn.ucm-ant-btn-round.ucm-ant-btn-primary").click()
WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CLASS_NAME, "pop-up_pop-up-modal-cheat-notice-content-botton__iS8oJ")))
driver.find_element(By.CLASS_NAME, "pop-up_pop-up-modal-cheat-notice-content-botton__iS8oJ").click()


@reloading
def CompleteSingleQuestion():
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

        Direction = "以下是题目的说明, 注意说明中可能包含了答题要求的关键信息, 请优先遵循题目说明中的要求, 所有的视频和音频已经转化成英文文章:\n" + driver.find_element(By.CLASS_NAME, "abs-direction").text
        # print(Direction)

        print(f"{Direction}\n{ListeningData}\n{Question}")

        # AIQuestion = f"{prompt}\n{Direction}\n{ListeningData}\n{Question}"
        if QuestionType == "单选题":
            AIQuestion = f"{SingleChoiceQuestionPrompt}\n{Direction}\n{ListeningData}\n{Question}"
        elif QuestionType == "多选题":
            AIQuestion = f"{MultipleChoiceQuestionPrompt}\n{Direction}\n{ListeningData}\n{Question}"
        elif QuestionType == "填空题":
            AIQuestion = f"{BlankQuestion}\n{Direction}\n{ListeningData}\n{Question}"
        elif QuestionType == "回答题":
            AIQuestion = f"{InputBoxQuestion}\n{Direction}\n{ListeningData}\n{Question}"
            pass

        # print(AIQuestion)

        print("正在等待DeepSeek回答")
        DeepSeekResponse = DeepSeekClient.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": """欢迎来到英语文章解析与逻辑推理的世界。请提供一篇英语文章和一些题目""",
                },
                {"role": "user", "content": AIQuestion},
            ],
            temperature=0.2,
        )

        Answer = DeepSeekResponse.choices[0].message.content
        print(f"以下为DeepSeek答案:\n{Answer}\n---------------------------")
        AnswerMatched = re.search(r"\{[\s\S]*\}", Answer)
        JsonStr = AnswerMatched.group(0)
        JsonData = json.loads(JsonStr)
        # 打印结果
        print("DeepSeek最终答案是:")
        for Temp in JsonData["questions"]:
            print(f"""{Temp["answer"]}""")

        # 自动输入

        match QuestionType:
            case "单选题":
                OptionWraps = driver.find_elements(By.CLASS_NAME, "option-wrap")
                # 把AI回答变成格式化答案
                AnswerList = []
                for Item in JsonData["questions"]:
                    AnswerList.append(ord(Item["answer"]) - ord("A"))
                # 选中指定答案
                for index, OptionWrap in enumerate(OptionWraps):
                    Options = OptionWrap.find_elements(By.CLASS_NAME, "option")
                    if index < len(AnswerList):
                        Options[AnswerList[index]].click()

            case "多选题":
                OptionWrap = driver.find_element(By.CLASS_NAME, "option-wrap")
                # 重置所有选项的类名
                SelectedOptions = OptionWrap.find_elements(By.CSS_SELECTOR, ".option.selected.isNotReview")
                for SelectedOption in SelectedOptions:
                    SelectedOption.click()
                # 把AI回答变成格式化答案
                AnswerList = []
                for Item in JsonData["questions"][0]["answer"]:
                    if Item != "|":
                        AnswerList.append(ord(Item) - ord("A"))
                # 选中指定答案
                Options = OptionWrap.find_elements(By.CLASS_NAME, "option")
                for index in range(len(AnswerList)):
                    Options[AnswerList[index]].click()

            case "填空题":
                # 把AI回答变成格式化答案
                AnswerList = []
                for Item in JsonData["questions"]:
                    AnswerList.extend(Item["answer"].split("|"))
                # 填答案
                Containers = driver.find_element(By.CSS_SELECTOR, ".question-common-abs-scoop.comp-scoop-reply")
                Blanks = Containers.find_elements(By.CSS_SELECTOR, "div.comp-abs-input.input-user-answer.input-can-focus > input")
                for Index, Blank in enumerate(Blanks):
                    Blank.clear()
                    Blank.send_keys(AnswerList[Index])

            case "回答题":
                print(JsonData)
                TextBoxs = driver.find_elements(By.CLASS_NAME, "question-inputbox-input")
                # 清空原有内容并输入新的答案
                for Index, TextBox in enumerate(TextBoxs):
                    TextBox.clear()
                    TextBox.send_keys(JsonData["questions"][Index]["answer"])

        Submit()

    except Exception as e:
        print(f"Error occurs: {e}")


@reloading
def Auto():
    print("开始全自动答题, 请勿操作浏览器!")
    print("正在获取单元列表")
    Units = driver.find_elements(By.CSS_SELECTOR, '[data-index]')
    for i in Units:
        i.click ()
        time.sleep(1)

@reloading
def Manual():
    while True:
        print("\n当前模式: 半自动; 手动等待下一步操作: [1]抓取当前页面并分析(default) [2]退出当前模式")
        Operate = input("Input Operate: ")
        match Operate:
            case "":
                CompleteSingleQuestion()
            case "1":
                CompleteSingleQuestion()
            case "2":
                return
            case _:
                print("请输入正确的选项")


if __name__ == "__main__":
    while True:
        print("\n选择模式: [1]全自动答题(请确保停留在教程目录页面) [2]半自动答题")
        Mode = input("Input Mode: ")
        match Mode:
            case "1":
                Auto()
            case "2":
                Manual()
            case _:
                print("请输入正确的选项")
