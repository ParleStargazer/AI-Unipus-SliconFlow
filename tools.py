import re
import os
import json
import whisper
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from openai import OpenAI

from media_process import download_media
from secret import api_key
from prompts import SingleChoiceQuestionPrompt, MultipleChoiceQuestionPrompt, BlankQuestion, InputBoxQuestion

ai_client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

print("正在载入whisper模型")
model = whisper.load_model("base")


def Submit(driver):
    SubmitButton = driver.find_element(By.CLASS_NAME, "btn")
    SubmitButton.click()
    try:
        WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CLASS_NAME, "ant-btn-primary")))
        YesButton = driver.find_element(By.CLASS_NAME, "ant-btn-primary")
        YesButton.click()
    except Exception:
        print("无二次确认")


# @reloading
def complete_single_question(driver):
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

        ReplyContainerData = driver.find_element(By.CLASS_NAME, "layout-reply-container")
        Question = f"以下是题目,本次题目类型为{QuestionType}:\n{ReplyContainerData.text}"

        # 获取mp3路径
        match = re.search(r'src="([^"]+\.(mp3|mp4))(#|")', driver.page_source)
        aduio_url = match.group(1)

        # 下载并转换为WAV
        if not os.path.exists("./.cache/"):
            print("创建缓存文件夹")
            os.makedirs(".cache")
        file_path, file_extension = download_media(aduio_url)

        print("正在进行语音识别")
        ListeningData = "以下内容是视频或者音频转成的文章内容:\n" + model.transcribe(file_path)["text"]
        print("语音识别完成")

        Direction = "以下是题目的说明, 注意说明中可能包含了答题要求的关键信息, 请优先遵循题目说明中的要求, 所有的视频和音频已经转化成英文文章:\n" + driver.find_element(By.CLASS_NAME, "abs-direction").text

        match QuestionType:
            case "单选题":
                AIQuestion = f"{SingleChoiceQuestionPrompt}\n{Direction}\n{ListeningData}\n{Question}"
            case "多选题":
                AIQuestion = f"{MultipleChoiceQuestionPrompt}\n{Direction}\n{ListeningData}\n{Question}"
            case "填空题":
                AIQuestion = f"{BlankQuestion}\n{Direction}\n{ListeningData}\n{Question}"
            case "回答题":
                AIQuestion = f"{InputBoxQuestion}\n{Direction}\n{ListeningData}\n{Question}"
        # print(AIQuestion)

        print("正在等待DeepSeek回答")
        ai_response = ai_client.chat.completions.create(
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

        Answer = ai_response.choices[0].message.content
        print(f"以下为DeepSeek答案:\n{Answer}\n---------------------------")
        AnswerMatched = re.search(r"\{[\s\S]*\}", Answer)
        JsonStr = AnswerMatched.group(0)
        JsonData = json.loads(JsonStr)

        print("DeepSeek最终答案是:")
        for Temp in JsonData["questions"]:
            print(f"""{Temp["answer"]}""")

        # 自动输入
        match QuestionType:
            case "单选题":
                OptionWraps = driver.find_elements(By.CLASS_NAME, "option-wrap")
                AnswerList = []
                for Item in JsonData["questions"]:
                    AnswerList.append(ord(Item["answer"]) - ord("A"))
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
                AnswerList = []
                for Item in JsonData["questions"][0]["answer"]:
                    if Item != "|":
                        AnswerList.append(ord(Item) - ord("A"))
                Options = OptionWrap.find_elements(By.CLASS_NAME, "option")
                for index in range(len(AnswerList)):
                    Options[AnswerList[index]].click()
            case "填空题":
                AnswerList = []
                for Item in JsonData["questions"]:
                    AnswerList.extend(Item["answer"].split("|"))
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
