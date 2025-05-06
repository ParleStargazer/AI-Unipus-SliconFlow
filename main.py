import time
import whisper
import getpass
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from openai import OpenAI

from tools import complete_single_question, submit_single_question

api_key=getpass.getpass("请输入硅基流动的API密钥:")
username=input("请输入手机号:")
password=getpass.getpass("请输入密码:")
ai_client = OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1/")



print("正在载入whisper模型")
model = whisper.load_model("base")



print("正在启动浏览器")
options = Options()
options.add_argument("--headless")#无头模式
options.add_argument("--disable-logging")#禁用日志
options.add_argument("--log-level=3")#禁用日志
options.add_experimental_option("excludeSwitches", ["enable-logging"])#禁用日志
driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install(), log_path="nul"), options=options)



print("正在自动登录U校园AI板")
driver.get("https://ucloud.unipus.cn/home")




#执行登录操作
WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "login")))
driver.find_element(By.NAME, "username").send_keys(username)#输入账号
time.sleep(0.05)
driver.find_element(By.NAME, "password").send_keys(password)#输入密码
time.sleep(0.05)
checkbox = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#agreement input[type='checkbox']")))#同意协议
checkbox.click()#点击同意协议
time.sleep(0.05)
driver.find_element(By.ID, "login").click()#点击登录按钮




#登录后直接进入课程目录网址
WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ucm-ant-btn.ucm-ant-btn-round.ucm-ant-btn-primary"))).click()#等待弹窗出现并点击，然后直接进入课程目录




def listen_for_interrupt():
    global auto_running
    while True:
        print("输入任意非空字符以中断")
        user_input = input()
        if user_input.strip():
            auto_running = False
            return



def auto(main_trys):
    f_main_trys = main_trys
    #获取课程目录
    course_url = driver.current_url

    print("正在获取待做题列表")
    pending_questions = []
    units = driver.find_elements(By.CSS_SELECTOR, "[data-index]")
    for unit in units:
        unit_pending_questions = []
        unit.click()#点击单元
        time.sleep(0.75)
        active_unit_area = driver.find_element(By.CLASS_NAME, "unipus-tabs_itemActive__x0WVI")
        elements = active_unit_area.find_elements(By.CLASS_NAME, "courses-unit_taskItemContainer__gkVix")
        for index, element in enumerate(elements):  # 遍历记录下标
            text_content = element.text #记录每个下标标题
            if "必修" in text_content and "已完成" not in text_content and "Discussion" not in text_content and "Vocabulary" not in text_content:  # 筛选未完成的必修题
                unit_pending_questions.append({"index": index, "text": element.find_element(By.CLASS_NAME, "courses-unit_taskTypeName__99BXj").text})
        pending_questions.append({"data-index": unit.get_attribute("data-index"), "questions": unit_pending_questions})



    print("待做题列表如下:")
    for unit in pending_questions:
        print(f"Unit {unit['data-index']}:")
        if unit["questions"]:
            for question in unit["questions"]:
                print(f"  [{question['index']}] {question['text']}")
        else:
            print("  None")


    for unit in pending_questions:
        questions = unit["questions"]
        for question in questions:  # 根据记录的下标遍历


            attempts = 1
            while attempts < 100:
                print(f"\n正在尝试进入Unit{unit['data-index']}的第{question['index']}题 {question['text']}，尝试次数：{attempts}")


                try:
                    driver.get(course_url)  # 返回课程目录并重新寻址题目
                    waiting_time = 4+attempts
                    WebDriverWait(driver, waiting_time).until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-index="{unit["data-index"]}"]'))).click()
                    #如果可以点击，跳出循环
                    time.sleep(0.5)
                    active_unit_area = driver.find_element(By.CLASS_NAME, "unipus-tabs_itemActive__x0WVI")
                    time.sleep(0.5)
                    elements = active_unit_area.find_elements(By.CLASS_NAME, "courses-unit_taskItemContainer__gkVix")
                    time.sleep(0.5)
                    elements[question["index"]].click()
                    time.sleep(0.5)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "abs-direction")))  # 等待题目加载完成
                    # 处理弹窗
                    iKnow = driver.find_elements(By.CLASS_NAME, "iKnow")
                    if iKnow:
                        iKnow[0].click()
                        time.sleep(0.5)
                    confirm = driver.find_elements(By.CSS_SELECTOR, ".ant-btn.ant-btn-primary")
                    if confirm:
                        confirm[0].click()
                        time.sleep(0.5)
                    print("开始自动答题")
                    break
                except Exception as e:
                    print(f"无法进入Unit{unit['data-index']}的第{question['index']}题 {question['text']}")
                    attempts += 1
                    continue



            try:#尝试答题
                complete_single_question(driver=driver, ai_client=ai_client, model=model)
            except Exception as e:
                print("无法答题，从最初开始重试")
                main(f_main_trys + 1)




def main(main_trys):
    f_main_trys = main_trys
    if f_main_trys >= 10:
        print("尝试次数过多，结束程序")
        return
    
    #请注释掉下面的代码，适配你的课程!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    driver.get("https://ucloud.unipus.cn/app/cmgt/course-management")
    course_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//span[@title='大学英语A2B2']")))
    # 找到该课程元素附近的 img 元素
    # 定位到最终的 ant-card 元素并点击
    course_card = driver.find_element(By.XPATH, "//span[@title='大学英语A2B2']/ancestor::div[contains(@class, 'item')]//ancestor::div[contains(@class, 'info')]//ancestor::div[contains(@class, 'top-info')]//following-sibling::div[contains(@class, 'content-con')]//descendant::div[contains(@class, 'ant-carousel')]//descendant::div[contains(@class, 'slick-slider')]//descendant::div[contains(@class, 'slick-list')]//descendant::div[contains(@class, 'slick-track')]//descendant::div[contains(@class, 'slick-slide slick-active slick-current')]//descendant::div[contains(@class, 'course-card-stu active')]//descendant::div[contains(@class, 'ant-card ant-card-bordered ant-card-hoverable')]")
    # 点击该元素
    course_card.click()
    print("已进入视听说教程2")


    #点击两次左侧按钮，退回到课程目录
    while True:
        try:
            left_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'unipus-tabs_tabInnerContainerLeft__pOHZU')]")))
            print("退回到课程目录：1")
            left_button.click()
            time.sleep(0.5)
            print("退回到课程目录：2")
            left_button.click()
            time.sleep(0.5)
            break
        except Exception as e:
            print("左侧按钮未加载完成，刷新网页重试")
            driver.refresh()
            continue


    #点击第一个单元
    first_unit = driver.find_element(By.XPATH, "//div[@title='Course preview']")
    first_unit.click()
    print("已点击第一个单元")
    time.sleep(0.25)

    #开始答题

    #请注释掉上面的代码，适配你的课程!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    auto(f_main_trys)#


if __name__ == "__main__":
    main(0)