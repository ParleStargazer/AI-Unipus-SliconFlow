single_choice_question_prompt = """请帮我解答以下英语题目, 并将答案以JSON格式输出。每个题目的答案应包含正确答案。JSON格式如下:
{
  "questions": [
    {
      "answer": "正确答案(只需要给出ABCD)"
    },
    ...
  ]
}
"""

multiple_choice_question_prompt = """这是多选题,请帮我解答以下英语题目, 并将答案以JSON格式输出. 一个多选题的答案全在一个"answer"里!!! 答案应包含正确答案,答案里只能有ABCD等选项和|,答案里若是有多个选项要用|隔开!!! JSON格式如下:
{
  "questions": [
    {
      "answer": "正确答案(只要给出选项例如A|C|D|E)"
    },
    ...
  ]
}
"""

blank_question = """请帮我解答以下英语题目, 并将答案以JSON格式输出, 如果一个题目有多个空请把那一题的全部答案放在一个"answer"里, 相互之间要用|隔开!!! 每个题目的答案应包含正确答案。JSON格式如下:
{
  "questions": [
    {
      "answer": "正确答案"
    },
    ...
  ]
}
"""

input_box_question = """请帮我解答以下英语题目, 并将答案以JSON格式输出,题目的答案应包含正确答案。JSON格式如下:
{
  "questions": [
    {
      "answer": "正确答案"
    },
    ...
  ]
}
"""

translate_question = """请帮我解答以下英语翻译题目, 中文要翻译成英文! 英文要翻译成中文! 并将答案以JSON格式输出,题目的答案应包含正确答案。JSON格式如下:
{
  "questions": [
    {
      "answer": "正确答案"
    },
    ...
  ]
}
"""

blank_change_question = """请帮我解答以下英语填空题, 请用给的单词来填空, 可以改变形式! 注意语法时态! 做完后检查一次, 并将答案以JSON格式输出, 如果一个题目有多个空请把那一题的全部答案放在一个"answer"里, 相互之间要用|隔开!!! 每个题目的答案应包含正确答案。JSON格式如下:
{
  "questions": [
    {
      "answer": "正确答案"
    },
    ...
  ]
}
"""