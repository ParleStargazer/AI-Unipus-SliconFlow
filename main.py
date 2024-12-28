import time
import whisper
import threading
from reloading import reloading
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from openai import OpenAI

from secret import username, password, api_key
from tools import complete_single_question

ai_client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

print("正在载入whisper模型")
model = whisper.load_model("base")

print("正在启动浏览器")
options = Options()
options.add_argument("--disable-logging")
options.add_argument("--log-level=OFF")
driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install(), log_path="nul"), options=options)

print("正在自动登录U校园AI板")
driver.get("https://ucloud.unipus.cn/home")
WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "login")))
driver.find_element(By.NAME, "username").send_keys(username)
driver.find_element(By.NAME, "password").send_keys(password)
driver.find_element(By.ID, "login").click()
WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CLASS_NAME, "layui-layer-btn0"))).click()
WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ucm-ant-btn.ucm-ant-btn-round.ucm-ant-btn-primary"))).click()
WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CLASS_NAME, "pop-up_pop-up-modal-cheat-notice-content-botton__iS8oJ"))).click()


def listen_for_interrupt():
    global auto_running
    while True:
        print("输入任意非空字符以中断")
        user_input = input()
        if user_input.strip():
            auto_running = False
            return


@reloading
def auto():
    print("开始全自动答题, 请勿操作浏览器!")
    course_url = driver.current_url
    print("正在获取待做题列表")
    pending_questions = []
    units = driver.find_elements(By.CSS_SELECTOR, "[data-index]")
    for unit in units:
        unit_pending_questions = []
        unit.click()
        time.sleep(0.5)
        active_unit_area = driver.find_element(By.CLASS_NAME, "unipus-tabs_itemActive__x0WVI")
        elements = active_unit_area.find_elements(By.CLASS_NAME, "courses-unit_taskItemContainer__gkVix")
        for index, element in enumerate(elements):  # 遍历记录下标
            text_content = element.text
            if "必修" in text_content and "已完成" not in text_content:  # 筛选未完成的必修题
                unit_pending_questions.append(index)
        pending_questions.append({"data-index": unit.get_attribute("data-index"), "questions": unit_pending_questions})
    for unit in pending_questions:
        questions = unit["questions"]
        for question in questions:  # 根据记录的下标遍历
            if not auto_running:
                print("全自动答题已中断")
                return
            print(f"\n正在进入Unit{unit['data-index']}的第{question}题")
            driver.get(course_url)  # 返回课程目录并重新寻址题目
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-index="{unit["data-index"]}"]'))).click()
            time.sleep(0.5)
            active_unit_area = driver.find_element(By.CLASS_NAME, "unipus-tabs_itemActive__x0WVI")
            elements = active_unit_area.find_elements(By.CLASS_NAME, "courses-unit_taskItemContainer__gkVix")
            elements[question].click()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "abs-direction")))  # 等待题目加载完成
            time.sleep(0.5)
            # 处理弹窗
            iKnow = driver.find_elements(By.CLASS_NAME, "iKnow")
            if iKnow:
                iKnow[0].click()
            confirm = driver.find_elements(By.CSS_SELECTOR, ".ant-btn.ant-btn-primary")
            if confirm:
                confirm[0].click()
            print("开始自动答题")
            complete_single_question(driver=driver, ai_client=ai_client, model=model)


@reloading
def manual():
    while True:
        print("\n当前模式: 半自动; 手动等待下一步操作: [1]抓取当前页面并分析(default) [2]退出当前模式")
        operate = input("Input Operate Mode: ")
        match operate:
            case "":
                complete_single_question(driver=driver, ai_client=ai_client, model=model)
            case "1":
                complete_single_question(driver=driver, ai_client=ai_client, model=model)
            case "2":
                return
            case _:
                print("请输入正确的选项")


def main():
    while True:
        print("\n选择模式: [1]全自动答题(请确保停留在教程目录页面) [2]半自动答题 [3]退出程序(浏览器也会关闭)")
        mode = input("Input Mode: ")
        match mode:
            case "1":
                global auto_running
                auto_running = True
                listener_thread = threading.Thread(target=listen_for_interrupt, daemon=True)
                listener_thread.start()
                auto()
            case "2":
                manual()
            case "3":
                driver.quit()
                return
            case _:
                print("请输入正确的选项")


if __name__ == "__main__":
    main()
