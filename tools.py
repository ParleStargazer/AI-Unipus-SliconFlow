import re
import os
import json
from whisper import Whisper
from selenium.webdriver.edge.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from openai import OpenAI

from media_process import download_media
from prompts import SingleChoiceQuestionPrompt, MultipleChoiceQuestionPrompt, BlankQuestion, InputBoxQuestion, TranslateQuestion

from reloading import reloading

def Submit(driver: WebDriver):
    SubmitButton = driver.find_element(By.CLASS_NAME, "btn")
    SubmitButton.click()
    try:
        WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CLASS_NAME, "ant-btn-primary")))
        YesButton = driver.find_element(By.CLASS_NAME, "ant-btn-primary")
        YesButton.click()
    except Exception:
        print("无二次确认")

@reloading
def complete_submit_question(driver: WebDriver, QuestionType, JsonData):
    match QuestionType:
        case "单选题" | "阅读选择题" | "词汇选择题":
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
            TextBoxs = driver.find_elements(By.CLASS_NAME, "question-inputbox-input")
            # 清空原有内容并输入新的答案
            for Index, TextBox in enumerate(TextBoxs):
                TextBox.clear()
                TextBox.send_keys(JsonData["questions"][Index]["answer"])
        case "翻译题":
            TextBoxs = driver.find_elements(By.CLASS_NAME, "question-inputbox-input")
            for Index, TextBox in enumerate(TextBoxs):
                TextBox.clear()
                TextBox.send_keys(JsonData["questions"][Index]["answer"])
    Submit(driver=driver)

@reloading
def complete_single_question(driver: WebDriver, ai_client: OpenAI, model: Whisper):
    try:
        #查看有没有音频或者视频
        match = re.search(r'src="([^"]+\.(mp3|mp4))(#|")', driver.page_source)
        if match:
            print("有音频或者视频文件")
            if driver.find_elements(By.CLASS_NAME, "question-common-abs-choice"):
                if driver.find_elements(By.CLASS_NAME, "multipleChoice"):
                    question_type = "多选题"
                else:
                    question_type = "单选题"
            else:
                if driver.find_elements(By.CLASS_NAME, "question-common-abs-scoop"):
                    question_type = "填空题"
                elif driver.find_elements(By.CLASS_NAME, "question-inputbox"):
                    question_type = "回答题"
                else:
                    print("不支持的题型!")
                    return
            print(question_type)

            question_data = driver.find_element(By.CLASS_NAME, "layout-reply-container")
            Question = f"以下是题目,本次题目类型为{question_type}:\n{question_data.text}"

            # 获取mp3路径并下载
            match = re.search(r'src="([^"]+\.(mp3|mp4))(#|")', driver.page_source)
            aduio_url = match.group(1)
            if not os.path.exists("./.cache/"):
                print("创建缓存文件夹")
                os.makedirs(".cache")
            file_path, file_extension = download_media(aduio_url)
            print("正在进行语音识别")
            ListeningData = "以下内容是视频或者音频转成的文章内容:\n" + model.transcribe(file_path)["text"]
            print("语音识别完成")

            Direction = "以下是题目的说明, 注意说明中可能包含了答题要求的关键信息, 请优先遵循题目说明中的要求, 所有的视频和音频已经转化成英文文章:\n" + driver.find_element(By.CLASS_NAME, "abs-direction").text
            match question_type:
                case "单选题":
                    AIQuestion = f"{SingleChoiceQuestionPrompt}\n{Direction}\n{ListeningData}\n{Question}"
                case "多选题":
                    AIQuestion = f"{MultipleChoiceQuestionPrompt}\n{Direction}\n{ListeningData}\n{Question}"
                case "填空题":
                    AIQuestion = f"{BlankQuestion}\n{Direction}\n{ListeningData}\n{Question}"
                case "回答题":
                    AIQuestion = f"{InputBoxQuestion}\n{Direction}\n{ListeningData}\n{Question}"
        else:
            #无音频或者视频
            print("没有音频或视频文件")
            #TODO: 
            # 阅读选择题
            # 阅读文章回答问题题
            # 选词填空题(不可变)
            # 选词填空题(可变)
            # *文本音频结合题
            # *跨页题目
            
            #通过Direction来区分题目
            direction_text = driver.find_element(By.CLASS_NAME, "abs-direction").text
            if "Translate" in direction_text:
                question_type = "翻译题"
            elif "Choose the best answer to complete each sentence" in direction_text:
                question_type = "词汇选择题"
            elif "Choose the best answer" in direction_text or "choose the best answer" in direction_text:
                question_type = "阅读选择题"
            elif "Answer the following questions according to the text" in direction_text:
                question_type = "阅读文章回答问题题"
            elif "Fill in the blanks" in direction_text and "Change the form" in direction_text:
                question_type = "选词填空题(可变)"
            elif "Fill in the blanks" in direction_text:
                question_type = "选词填空题(不可变)"
            else:
                print("不支持的题型!")
                return
            
            print(question_type)
            
            Direction = "以下是题目的说明, 注意说明中可能包含了答题要求的关键信息, 请优先遵循题目说明中的要求\n" + direction_text
            match question_type:
                case "翻译题":
                    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".layout-reply-container.full")))
                    question_data = driver.find_element(By.CSS_SELECTOR, ".layout-reply-container.full")
                    Question = f"以下是题目,本次题目类型为{question_type}:\n{question_data.text}"
                    AIQuestion = f"{TranslateQuestion}\n{Direction}\n{Question}"
                case "阅读选择题":
                    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "text-material-wrapper")))
                    question_text_data = driver.find_element(By.CLASS_NAME, "text-material-wrapper")
                    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "reply-wrap")))
                    question_data = driver.find_element(By.CLASS_NAME, "reply-wrap")
                    Question = f"以下是题目,本次题目类型为{question_type}:\n{question_data.text}"
                    AIQuestion = f"{SingleChoiceQuestionPrompt}\n{Direction}\n{question_text_data.text}\n{Question}"
                    pass
                case "词汇选择题":
                    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "reply-wrap")))
                    question_data = driver.find_element(By.CLASS_NAME, "reply-wrap")
                    Question = f"以下是题目,本次题目类型为{question_type}:\n{question_data.text}"
                    AIQuestion = f"{SingleChoiceQuestionPrompt}\n{Direction}\n{Question}"
                case "阅读文章回答问题题":
                    pass
                case "选词填空题(可变)":
                    pass
                case "选词填空题(不可变)":
                    pass
                case _:
                    pass
                
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
        answer_matched = re.search(r"\{[\s\S]*\}", Answer)
        json_str = answer_matched.group(0)
        json_data = json.loads(json_str)
        print("DeepSeek最终答案是:")
        for Temp in json_data["questions"]:
            print(f"""{Temp["answer"]}""")
                
        complete_submit_question(driver=driver, QuestionType=question_type, JsonData=json_data)
        
    except Exception as e:
        print(f"Error occurs: {e}")
        # 自动输入


    except Exception as e:
        print(f"Error occurs: {e}")
