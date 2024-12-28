import re
import os
import json
from reloading import reloading
from whisper import Whisper
from selenium.webdriver.edge.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from openai import OpenAI

from media_process import download_media
from prompts import SingleChoiceQuestionPrompt, MultipleChoiceQuestionPrompt, BlankQuestion, InputBoxQuestion, TranslateQuestion, BlankChangeQuestion


def Submit(driver: WebDriver):
    submit_button = driver.find_element(By.CLASS_NAME, "btn")
    submit_button.click()
    try:
        WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CLASS_NAME, "ant-btn-primary")))
        yes_button = driver.find_element(By.CLASS_NAME, "ant-btn-primary")
        yes_button.click()
    except Exception:
        print("无二次确认")


@reloading
def submit_single_question(driver: WebDriver, question_type, json_data):
    match question_type:
        case "单选题" | "阅读选择题" | "词汇选择题":
            option_wraps = driver.find_elements(By.CLASS_NAME, "option-wrap")
            answer_list = []
            for item in json_data["questions"]:
                answer_list.append(ord(item["answer"]) - ord("A"))
            for index, option_wrap in enumerate(option_wraps):
                options = option_wrap.find_elements(By.CLASS_NAME, "option")
                if index < len(answer_list):
                    options[answer_list[index]].click()
        case "多选题":
            option_wrap = driver.find_element(By.CLASS_NAME, "option-wrap")
            # 重置所有选项的类名
            selected_options = option_wrap.find_elements(By.CSS_SELECTOR, ".option.selected.isNotReview")
            for selected_option in selected_options:
                selected_option.click()
            answer_list = []
            for item in json_data["questions"][0]["answer"]:
                if item != "|":
                    answer_list.append(ord(item) - ord("A"))
            options = option_wrap.find_elements(By.CLASS_NAME, "option")
            for index in range(len(answer_list)):
                options[answer_list[index]].click()
        case "填空题":
            answer_list = []
            for item in json_data["questions"]:
                answer_list.extend(item["answer"].split("|"))
            containers = driver.find_element(By.CSS_SELECTOR, ".question-common-abs-scoop.comp-scoop-reply")
            blanks = containers.find_elements(By.CSS_SELECTOR, "div.comp-abs-input.input-user-answer.input-can-focus > input")
            for index, blank in enumerate(blanks):
                blank.clear()
                blank.send_keys(answer_list[index])
        case "回答题" | "阅读文章回答问题题":
            text_boxs = driver.find_elements(By.CLASS_NAME, "question-inputbox-input")
            # 清空原有内容并输入新的答案
            for index, text_box in enumerate(text_boxs):
                text_box.clear()
                text_box.send_keys(json_data["questions"][index]["answer"])
        case "翻译题":
            text_boxs = driver.find_elements(By.CLASS_NAME, "question-inputbox-input")
            for index, text_box in enumerate(text_boxs):
                text_box.clear()
                text_box.send_keys(json_data["questions"][index]["answer"])
        case "选词填空题(可变)":
            print("1")
            answer_list = []
            for item in json_data["questions"]:
                answer_list.extend(item["answer"].split("|"))
            containers = driver.find_element(By.CLASS_NAME, "component-htmlview")
            blanks = driver.find_elements(By.CSS_SELECTOR, ".input-wrapper > .comp-abs-input > input")
            for index, blank in enumerate(blanks):
                blank.clear()
                blank.send_keys(answer_list[index])
    Submit(driver=driver)


@reloading
def complete_single_question(driver: WebDriver, ai_client: OpenAI, model: Whisper):
    try:
        # 查看有没有音频或者视频
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
            # 无音频或者视频
            print("没有音频或视频文件")
            # TODO:
            # 阅读文章回答问题题
            # 选词填空题(不可变)
            # 选词填空题(可变)
            # *文本音频结合题
            # *跨页题目

            # 通过Direction来区分题目
            direction_text = driver.find_element(By.CLASS_NAME, "abs-direction").text
            if "Translate" in direction_text:
                question_type = "翻译题"
            elif "Choose the best answer to complete each sentence" in direction_text:
                question_type = "词汇选择题"
            elif "Choose the best answer" in direction_text or "choose the best answer" in direction_text:
                question_type = "阅读选择题"
            elif "Answer the following questions according to the text" in direction_text or "Think about the following questions" in direction_text:
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
                case "词汇选择题":
                    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "reply-wrap")))
                    question_data = driver.find_element(By.CLASS_NAME, "reply-wrap")
                    Question = f"以下是题目,本次题目类型为{question_type}:\n{question_data.text}"
                    AIQuestion = f"{SingleChoiceQuestionPrompt}\n{Direction}\n{Question}"
                case "阅读文章回答问题题":
                    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "text-material-wrapper")))
                    question_text_data = driver.find_element(By.CLASS_NAME, "text-material-wrapper")
                    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "reply-wrap")))
                    question_data = driver.find_element(By.CLASS_NAME, "reply-wrap")
                    Question = f"以下是题目,本次题目类型为{question_type}:\n{question_data.text}"
                    AIQuestion = f"{InputBoxQuestion}\n{Direction}\n{question_text_data.text}\n{Question}"
                case "选词填空题(可变)":
                    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-material-banked-cloze-reply.clearfix")))
                    question_data = driver.find_element(By.CSS_SELECTOR, ".question-material-banked-cloze-reply.clearfix")
                    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "question-material-banked-cloze-scoop")))
                    question_text_data = driver.find_element(By.CLASS_NAME, "question-material-banked-cloze-scoop")
                    Question = f"以下是题目,本次题目类型为{question_type},以下是选项:\n{question_data.text}"
                    AIQuestion = f"{BlankChangeQuestion}\n{Direction}\n{question_text_data.text}\n{Question}"
                    pass
                case "选词填空题(不可变)":
                    print("暂未适配")
                    return
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
        json_str = answer_matched.group(0).replace('",', '"')
        json_data = json.loads(json_str)
        print(1)
        print("DeepSeek最终答案是:")
        for Temp in json_data["questions"]:
            print(f"""{Temp["answer"]}""")

        submit_single_question(driver=driver, question_type=question_type, json_data=json_data)

    except Exception as e:
        print(f"Error occurs: {e}")
