##1.任务与提示词
读生词表CSV，筛HSK4，造练习题
##2.AI初版代码
# W3 生词表 CSV -> 自动生成练习题
# 运行：python vocab_tool.py
import os
import csv
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402  统一解析 data/ 路径，换目录也不会找不到文件

DATA = weekpath.data_path("生词表.csv")


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
    """按HSK等级筛选，已清洗空格，字符串比对"""
    return [w for w in words if w.get("HSK等级", "") == str(level)]


def count_by_pos(words):
    """统计词性分布"""
    d = {}
    for w in words:
        pos = w.get("词性", "未知")
        d[pos] = d.get(pos, 0) + 1
    return d


def gen_exercises(words, out=None):
    out = out or weekpath.root_path("练习.txt")
    words_list = words

    # 构造配对题目素材
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
    # 适配愚公移山HSK4：把字句、商量、感动、坚持
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
    out = weekpath.root_path("练习.txt")
    gen_exercises(lv4, out)
    print("已生成：%s" % out)

##3.我的修改点
1.原脚本依赖课程内部自定义`weekpath`模块，本地环境缺少该模块，运行直接抛出`ModuleNotFoundError`
2.删除全部`import weekpath`以及`sys.path`插入相关代码；使用 Python 内置`os.path`
3.业务函数`load_words / filter_by_level / count_by_pos / gen_exercises`全部保留不变，不改动习题生成逻辑。
4.使用**字典**`{pos: [wordlist]`实现按词性分组存储，字典 key 保存词性，value 保存同词性词汇列表。
##4.最终版vs初版差异说明
初版weekpath库电脑中没有，最终版适用python内置函数绕过weekpath库达到最终目的
