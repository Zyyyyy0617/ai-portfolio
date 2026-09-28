# W3 生词表 CSV -> 自动生成练习题
# 运行：python vocab_tool.py
import os
import csv

# ========== 替代 weekpath，纯标准库实现路径 ==========
# 当前脚本的绝对路径
SCRIPT_FILE = os.path.abspath(__file__)
# 当前脚本所在文件夹
SCRIPT_DIR = os.path.dirname(SCRIPT_FILE)
# 项目根目录：脚本目录向上一级（等价原来 weekpath.root_path）
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
# data目录下生词表csv
DATA = os.path.join(PROJECT_ROOT, "data", "生词表.csv")
# 输出练习txt到项目根目录
DEFAULT_OUT = os.path.join(PROJECT_ROOT, "练习.txt")


def load_words(path=DATA):
    """读取csv，并清洗所有key、value前后空格"""
    clean_list = []
    with open(path, encoding="utf-8") as f:
        raw_rows = csv.DictReader(f)
        for row in raw_rows:
            clean_row = {}
            for k, v in row.items():
                key_clean = k.strip()
                val_clean = v.strip() if v is not None else ""
                clean_row[key_clean] = val_clean
            clean_list.append(clean_row)
    return clean_list


def filter_by_level(words, level="4"):
    """按HSK等级筛选"""
    return [w for w in words if w.get("HSK等级", "") == str(level)]


def count_by_pos(words):
    """统计词性分布"""
    d = {}
    for w in words:
        pos = w.get("词性", "未知")
        d[pos] = d.get(pos, 0) + 1
    return d


def gen_exercises(words, out=None):
    out = out or DEFAULT_OUT
    words_list = words

    vocab = [item["词汇"] for item in words_list]
    meaning = [item["释义"] for item in words_list]

    lines = []
    lines.append("==== HSK4生词练习（自动生成）====\n\n")

    # 1 词义配对
    lines.append("一、词义配对：把词语和对应的释义相连\n")
    for idx, word in enumerate(vocab):
        lines.append(f"{idx+1}. {word}\n")
    lines.append("\n")
    for idx, mea in enumerate(meaning):
        lines.append(f"{chr(65+idx)}. {mea}\n")
    lines.append("\n")

    # 2 选词填空
    lines.append(f"二、选词填空，可选词：{'、'.join(vocab)}\n\n")
    fill_sents = [
        "做事情需要 ________，不要轻易放弃。",
        "大家在一起 ________ 这件事怎么办。",
        "这个故事深深 ________ 了我。",
        "学习汉语要多多练习 ________。"
    ]
    answers = ["坚持", "商量", "感动", "把字句"]
    for s in fill_sents:
        lines.append(s + "\n")
    lines.append("\n")

    # 3 造句小题（保留原程序原有功能）
    lines.append("三、用词语造句\n")
    for w in words_list:
        lines.append(f"用“{w['词汇']}”造一个句子。（{w['词性']}）\n")

    # 参考答案
    lines.append("\n====参考答案====\n")
    lines.append("【选词填空】\n")
    for sent, ans in zip(fill_sents, answers):
        lines.append(f"{sent} → {ans}\n")

    with open(out, "w", encoding="utf-8") as f:
        f.writelines(lines)


if __name__ == "__main__":
    words = load_words()
    lv4 = filter_by_level(words, "4")
    print("总词汇 %d 个，其中 HSK4 词汇 %d 个，词性分布：%s"
          % (len(words), len(lv4), count_by_pos(lv4)))
    out = DEFAULT_OUT
    gen_exercises(lv4, out)
    print("已生成：%s" % out)
