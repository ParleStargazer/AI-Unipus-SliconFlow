import re
import os
import json
import time
from reloading import reloading
from whisper import Whisper
from selenium.webdriver.edge.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from openai import OpenAI

from media_process import download_media
from prompts import single_choice_question_prompt, multiple_choice_question_prompt, blank_question, input_box_question, translate_question, blank_change_question


def submit(driver: WebDriver):
    submit_button = driver.find_element(By.CLASS_NAME, "btn")
    submit_button.click()
    try:
        WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CLASS_NAME, "ant-btn-primary"))).click()
        print("存在二次确认, 已确认")
    except Exception:
        pass



def watch_video(driver: WebDriver):
    video_box = driver.find_element(By.CLASS_NAME, "video-box")
    video = video_box.find_element(By.TAG_NAME, "video")
    driver.execute_script("arguments[0].pause(); arguments[0].play();", video)
    print("视频开始播放")
    video_duration = driver.execute_script("return arguments[0].duration;", video)
    try:
        video_box.find_elements(By.CLASS_NAME, "controlBtn")[0].click()  # 倍速按钮
        time.sleep(0.5)
        video_box.find_elements(By.CLASS_NAME, "textOption")[5].click()  # 选择2倍速
        print("已调整至两倍速")
    except Exception:
        print("调整倍速失败")
    print(f"视频时长为{video_duration}秒, 程序等待{video_duration/2}秒")
    time.sleep(video_duration / 2)
    print("视频播放完毕")



def submit_single_question(driver: WebDriver, question_type, json_data, debug=False):
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
            answer_list = []
            for item in json_data["questions"]:
                answer_list.extend(item["answer"].split("|"))
            containers = driver.find_element(By.CLASS_NAME, "component-htmlview")
            blanks = driver.find_elements(By.CSS_SELECTOR, ".input-wrapper > .comp-abs-input > input")
            for index, blank in enumerate(blanks):
                blank.clear()
                blank.send_keys(answer_list[index])
    if not debug:
        submit(driver=driver)
        print("已提交答案")
        time.sleep(0.5)


def complete_single_question(driver: WebDriver, ai_client: OpenAI, model: Whisper, debug=False):
    try:
        if driver.find_elements(By.CLASS_NAME, "layout-reply-container"):
            reply_area = driver.find_element(By.CLASS_NAME, "layout-reply-container")
        else:
            print("本题没有回答区域")
            if driver.find_elements(By.CLASS_NAME, "video-box"):
                print("视频题, 即将开始播放视频")
                watch_video(driver)
            return

        if reply_area.find_elements(By.TAG_NAME, "img"):
            print("本题回答区域有图片, 无法识别处理")
            if not debug:
                return
            match input("是否强行解析? [Y/n]: ").upper():
                case "Y" | "":
                    question_type = "(!未知题型!请试图理解并处理!)"
                case _:
                    return

        # 查看有没有音频或者视频
        match = re.search(r'src="([^"]+\.(mp3|mp4))(#|")', driver.page_source)
        if match:
            if debug:
                print("有音视频文件")
            if driver.find_elements(By.CLASS_NAME, "question-common-abs-choice"):
                if driver.find_elements(By.CLASS_NAME, "multipleChoice"):
                    question_type = "多选题"
                else:
                    question_type = "单选题"
            else:
                if driver.find_elements(By.CLASS_NAME, "question-common-abs-scoop"):
                    question_type = "填空题"
                    if driver.find_elements(By.CLASS_NAME, "comp-scoop-reply-dropdown-selection-overflow"):
                        if not debug:
                            print("伪填空选择题, 不支持, 请于手动模式中处理")
                            return
                elif driver.find_elements(By.CLASS_NAME, "question-inputbox"):
                    question_type = "回答题"
                else:
                    print("不支持的题型!")
                    if not debug:
                        return
                    match input("是否强行解析? [Y/n]: ").upper():
                        case "Y" | "":
                            question_type = "(!未知题型!请试图理解并处理!)"
                        case _:
                            return
            print(question_type)

            question = f"以下是题目,本次题目类型为{question_type}:\n{reply_area.text}"

            # 获取mp3路径并下载
            match = re.search(r'src="([^"]+\.(mp3|mp4))(#|")', driver.page_source)
            aduio_url = match.group(1)
            if not os.path.exists("./.cache/"):
                print("创建缓存文件夹")
                os.makedirs(".cache")
            file_path, file_extension = download_media(aduio_url)
            print("正在进行语音识别")
            listening_data = "以下内容是视频或者音频转成的文章内容:\n" + model.transcribe(file_path)["text"]
            print("语音识别完成")

            direction = "以下是题目的说明, 注意说明中可能包含了答题要求的关键信息, 请优先遵循题目说明中的要求, 所有的视频和音频已经转化成英文文章:\n" + driver.find_element(By.CLASS_NAME, "abs-direction").text
            match question_type:
                case "单选题":
                    ai_question = f"{single_choice_question_prompt}\n{direction}\n{listening_data}\n{question}"
                case "多选题":
                    ai_question = f"{multiple_choice_question_prompt}\n{direction}\n{listening_data}\n{question}"
                case "填空题":
                    ai_question = f"{blank_question}\n{direction}\n{listening_data}\n{question}"
                case "回答题":
                    ai_question = f"{input_box_question}\n{direction}\n{listening_data}\n{question}"
                case "(!未知题型!请试图理解并处理!)":
                    ai_question = f"{input_box_question}\n{direction}\n{listening_data}\n{question}"
                case _:
                    print("Fuck U")
                    return
        else:
            # 无音频或者视频
            if debug:
                print("无音视频文件")
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

            direction = "以下是题目的说明, 注意说明中可能包含了答题要求的关键信息, 请优先遵循题目说明中的要求\n" + direction_text
            match question_type:
                case "翻译题":
                    question_data = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".layout-reply-container.full")))
                    question = f"以下是题目,本次题目类型为{question_type}:\n{question_data.text}"
                    ai_question = f"{translate_question}\n{direction}\n{question}"
                case "阅读选择题":
                    question_text_data = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "text-material-wrapper")))
                    question_data = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "reply-wrap")))
                    question = f"以下是题目,本次题目类型为{question_type}:\n{question_data.text}"
                    ai_question = f"{single_choice_question_prompt}\n{direction}\n{question_text_data.text}\n{question}"
                case "词汇选择题":
                    question_data = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "reply-wrap")))
                    question = f"以下是题目,本次题目类型为{question_type}:\n{question_data.text}"
                    ai_question = f"{single_choice_question_prompt}\n{direction}\n{question}"
                case "阅读文章回答问题题":
                    question_text_data = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "text-material-wrapper")))
                    question_data = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "reply-wrap")))
                    question = f"以下是题目,本次题目类型为{question_type}:\n{question_data.text}"
                    ai_question = f"{input_box_question}\n{direction}\n{question_text_data.text}\n{question}"
                case "选词填空题(可变)":
                    question_data = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-material-banked-cloze-reply.clearfix")))
                    question_text_data = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "question-material-banked-cloze-scoop")))
                    question = f"以下是题目,本次题目类型为{question_type},以下是选项:\n{question_data.text}"
                    ai_question = f"{blank_change_question}\n{direction}\n{question_text_data.text}\n{question}"
                    pass
                case "选词填空题(不可变)":
                    print("暂未适配")
                    return
                case _:
                    print("Fuck U")
                    return

        print("正在等待Qwen/QwQ-32B回答")
        ai_response = ai_client.chat.completions.create(
            model="Qwen/QwQ-32B",
            messages=[
                {
                    "role": "system",
                    "content": """欢迎来到英语文章解析与逻辑推理的世界。请提供一篇英语文章和一些题目""",
                },
                {"role": "user", "content": ai_question},
            ],
            temperature=0.2,
        )
        answer = ai_response.choices[0].message.content
        if debug:
            print(f"--------------------------------\n以下为Qwen/QwQ-32B回答:\n{answer}\n--------------------------------")
        answer_matched = re.search(r"\{[\s\S]*\}", answer)
        json_str = answer_matched.group(0).replace('",', '"')
        json_data = json.loads(json_str)
        print("Qwen/QwQ-32B的答案是:")
        for i in json_data["questions"]:
            print(f"""{i["answer"]}""")

        submit_single_question(driver=driver, question_type=question_type, json_data=json_data, debug=debug)
        return [question_type, json_data]

    except Exception as e:
        print(f"Error occurs: {e}")


if __name__ == "__main__":
    print("It seems you're not running main.py, but it's okay, we're calling main() now.")
    from main import main

    main()