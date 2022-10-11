# -*- coding: utf-8 -*-
########################################################################################################
# 自动合并txt文件，并自动进行内容过滤和遮码 - 作者：i126@126.com
# 特别注意：外文语料需要特别处理，若使用此脚本合并，请在FILTER_WORDS中去掉对空格的过滤
########################################################################################################

import os,chardet,shutil,sys
import re

# ======================
# 以下为遮码处理时需要引入
from LAC import LAC
from ltp import LTP
lac = LAC(mode="lac")
ltp = LTP()
# ======================



# 原始txt文件存放的路径
input_path= './input'
# 输出的txt合并文件存放的文件路径及文件名
out_txt = './out/out.txt'
# 无法读取的原始txt文件会被挪到此目录（一般为编码非utf-8的文件，需要转码才能处理）
error_path = './error'

# 是否自动遮码。默认启用遮码。即是否对人名、地名、组织机构进行遮码处理。缺省为否。如果设置为Ture，整体处理速度会非常慢。这也是没有办法的事儿。
# 缺省不对人名进行遮码，如果一定要将人名也进行遮码，请将 obscuration(line,is_name=False) 函数中的 False 修改为 True
is_obscuration = False

# 字符过滤。注意，包含了过滤所有空格。如果文中英文较多，则需要将空格字符去掉。另行处理。
""" 此处主要简单过滤掉一些非法或者不常见的干扰行文的字符 """
FILTER_WORDS = '＂ \'＃＄＆＇＊＋－-／＜＝=＞◆●☆@€＠［＼］＾＿｀｛｜｝～｟｠｢｣､\u3000、〃〈〉「」『』【】〔〕〖〗〘〙〚〛〜〟〰〾〿﹑、\r\n﻿'

# 字符串过滤。以 | 进行间隔的长字符串。每个单独的字符串之间必须用 | 进行间隔。
""" 要严格过滤掉的字符串，即找到该字符串，则直接置换为空。举例说明过滤的优先级：比如先过滤'序言'，后过滤'序'，则是不至于漏掉'言'字。 """
WORDS_ARR = '分割线|该章节已被锁定|(大结局)|（大结局）|未完待续:|未完待续：|未完待续|人物介绍:|人物介绍：|人物介绍|楔子|正文卷|正文卷:|正文卷：|全部章节|' \
            '红袖添香网|红袖添香文学网|绿色资源网|全文完|全书完|Tag列表：|Tag列表:|Tag列表|用户上传之内容|作品仅供读者预览|搜索关键字|本图书由|' \
            '下载后24小时|更多txt|新书开张|Bud1%E%DSDB`|Bud1%E%DSDB|作者：|作者:|作者|内容简介：|内容简介:|内容简介|内容提要：|内容提要:|内容提要|作品赏析：|作品赏析:|作品赏析' \
            '|（完）|(完)|( 完 )|（ 完 ）|{全文完}|{ 全文完 }|-正文-|……|…|序言|前言|序|知乎'

# 长字符串过滤。数组形式。数组中每个元素均要用单引号框住。数组元素之间用逗号间隔。之所以不采用通配符直接过滤整行，原因在于某些文章中会在段中插入这些混淆字符串。如果整行去掉，则意味着可能可清除了无关文字。
""" 对过滤不掉的，且必须清楚的部分正常字符串予以清除 """
STRING_ARR = ['()', '（）', '[]',
              'XX电子书·电子书下载乐园—Ｗww.XXX.Ｃom',
              'XX电子书|Www.XXX.com'
              ]

# 行首过滤。数组形式。数组中每个元素均要用单引号框住。数组元素之间用逗号间隔。此处也是要注意过滤的优先级的。比如  （《,》） 先过滤，再过滤 《,》
""" 行首开始两字符串间，含两字符串及中间包含部分，一起清除 """
LINESTART_BETWEEN2WORDS = ['《(,)》','（《,》）','《,》','本章第,章', '第,章',
                           '第,节', '第,篇', '第,幕', '第,首', '第,卷', '第,段', '第,部', '第,回', '第,册', '第,炮', '第,季', '第,集']

# 整行过滤。数组形式。数组中每个元素均要用单引号框住。数组元素之间用逗号间隔。
""" 行内只要包含该字符串，则整行清除 """
DEL_ROW_WORDS = ['XX电子书', 'txt', '找好书，看好书', '本作品来自互联网', '连载完毕', '本站所有资源', '内容简介：',
                 '导读：', '序言：', '仅供试阅', '简介:', 'chapter', '跪求各位', '有话要说：', '文案：', '内容标签：', '-正文-']

""" 注意：过滤数据是逐行过滤。而非对文本txt文件整体过滤。鉴于是读一行过滤一行，所以处理速度上会有些慢。 """
def filter_data(line=''):

    """ 备注：整体过滤风格从保守到粗暴，循序渐进，尽量不过滤掉有用内容 """

    """ 1、过滤不可见字符 """
    for i in range(0, 32):
        line = line.replace(chr(i), '')
    line = line.replace(chr(127), '')

    """ 2、字符串中多空格变单空格,不需要的字符过滤掉 """
    words = '['+ FILTER_WORDS + ']'
    line = re.sub(words, '', line)
    if '--' in line: line = ''

    """ 3、要严格过滤掉的字符串，即找到该字符串，则直接置换为空 """
    line = re.sub(WORDS_ARR, '', line)

    """ 4、对过滤不掉的，且必须清楚的部分正常字符串予以清除 """
    array_str_length = len(STRING_ARR)
    for j in range(array_str_length):
        if STRING_ARR[j] in line:
            line = line.replace(STRING_ARR[j], '')

    """ 5、行首开始两字符串间，含两字符串及中间包含部分，一起清除 """
    array_str_length = len(LINESTART_BETWEEN2WORDS)
    for k in range(array_str_length):
        array_str = LINESTART_BETWEEN2WORDS[k]
        start_str = array_str.split(',')[0]
        end_str = array_str.split(',')[1]
        if start_str and end_str in line:
            if start_str == line[0:len(start_str)]:
                res = start_str + '(.*?)' + end_str
                #filter_str = start_str + re.findall(res, line)[k] + end_str
                #line = line.replace(filter_str, '')
                line = ''

    # 以下是过滤不干净的，单独进行过滤处理。部分有用文字虽然也被清除，但整体对文章没多大影响。如果过滤关键字为纯英文的，则统一自动转小写进行匹配。
    """ 6、对过滤仍然不干净的，单独处理。这个处理手段比较粗暴。只要包含过滤词，则整行清除。 """
    array_str_length = len(DEL_ROW_WORDS)
    for l in range(array_str_length):
        import string
        for m in DEL_ROW_WORDS[l]:
            if m in string.ascii_lowercase + string.ascii_uppercase:
                if DEL_ROW_WORDS[l].lower() in line.lower():
                    line = ''
            elif DEL_ROW_WORDS[l] in line:
                line = ''

    return line


# ==============遮码处理函数开始==============
"""
# 遮码处理函数：obscuration(line)
# line 也是逐行自动处理遮码  
# is_name 是决定是否对人名进行遮码，缺省为False，原因在于语料中过多的[人物]可能会让语料训练加快，但却影响到了行为，并对最终训练结果产生较大影响。
# 备注：运行过程中 会出现警告：analysis_predictor.cc:1736] Deprecated. Please use CreatePredictor instead. 可忽略
# 缺省不对人名进行遮码，如果一定要将人名也进行遮码，请将 obscuration(line,is_name=False) 函数中的 False 修改为 True
"""

def obscuration(line,is_name=False):
    # 自动提取并遮码人名、地名、组织机构

    if is_name:
        lis1 = obscuration_name(line, 'lac', 'PER')
        if len(lis1) > 0:
            my_list = lis1
            for ele in my_list:
                line = line.replace(ele, '[人物]')
        else:
            line = line

    lis1 = obscuration_name(line, 'lac', 'ORG')
    if len(lis1) > 0:
        my_list = lis1
        for ele in my_list:
            line = line.replace(ele, '[组织机构]')
    else:
        line = line
    lis1 = obscuration_name(line, 'lac', 'LOC')
    if len(lis1) > 0:
        my_list = lis1
        for ele in my_list:
            line = line.replace(ele, '[地点]')
    else:
        line = line

    return line


def obscuration_name(sentence: str, type='lac', label='PER'):
    user_name_lis = []
    if type == 'lac':
        _result = lac.run(sentence)
        for _index, _label in enumerate(_result[1]):
            if label == 'PER':
                if _label == "PER": user_name_lis.append(_result[0][_index])
            if label == "ORG":
                if _label == "ORG": user_name_lis.append(_result[0][_index])
            if label == "LOC":
                if _label == "LOC": user_name_lis.append(_result[0][_index])
    elif type == 'ltp':
        _seg, _hidden = ltp.seg([sentence])
        _pos_hidden = ltp.pos(_hidden)
        for _seg_i, _seg_v in enumerate(_seg):
            _hidden_v = _pos_hidden[_seg_i]
            for _h_i, _h_v in enumerate(_hidden_v):
                if _h_v == "nh":
                    user_name_lis.append(_seg_v[_h_i])
    else:
        raise Exception('type not suppose')
    return user_name_lis

# ==============遮码处理函数结束==============

def main():

    """ 以下文件合并代码源自网友。来源：QQ群：143626394 群文件 """
    dis = os.listdir(input_path)
    c = 3
    b = int(len(dis))
    for i in dis:
        c += 1
        try:
            t = len(dis)
            a = input_path + "/" + i
            f = open(a, 'rb')
            r = f.read()
            f_charInfo = chardet.detect(r)
            f.close()

            if f_charInfo['encoding'] != 'None':
                with open(a, "r", encoding=f_charInfo['encoding']) as f1, \
                        open(out_txt, "a", encoding='utf-8') as f2:
                    # print(f'正在导入  {i}')
                    for line in f1:
                        # 此处引入了行过滤
                        line = filter_data(line)
                        # 此处引入了自动遮码
                        if is_obscuration:
                            line = obscuration(line)
                        if line == ' ' or line == '':
                            # 此处引入了行过滤
                            line = line.strip("")
                            f2.write(line)
                        else:
                            f2.write("{}\n".format(line))
                    f2.write('\n')
                    f2.close()

            elif f_charInfo['encoding'] != 'gb2312':
                with open(a, "r", encoding="ansi") as f1, \
                        open(out_txt, "a", encoding='utf-8') as f2:
                    # print(f'正在导入  {i}')
                    for line in f1:
                        # 此处引入了行过滤
                        line = filter_data(line)
                        # 此处引入了自动遮码
                        if is_obscuration:
                            line = obscuration(line)
                        if line == ' ' or line == '':
                            # 此处引入了行过滤
                            line = line.strip("")
                            f2.write(line)
                        else:
                            f2.write("{}\n".format(line))
                    f2.write('\n')
                    f2.close()

            else:
                with open(a, "r", encoding='utf-8') as f1, \
                        open(out_txt, "a", encoding='utf-8') as f2:
                    # print(f'正在导入  {i}')
                    for line in f1:
                        # 此处引入了行过滤
                        line = filter_data(line)
                        # 此处引入了自动遮码
                        if is_obscuration:
                            line = obscuration(line)
                        if line == ' ' or line == '':
                            # 此处引入了行过滤
                            line = line.strip("")
                            f2.write(line)
                        else:
                            f2.write("{}\n".format(line))
                    f2.write('\n')
                    f2.close()

        except:  # 总之是遇到错误用来存放的文件

            if error_path == '':
                sys.stdout.write('\r发现错误文件: ' + i)
                sys.stdout.flush()
                continue
            else:
                print(f'发现错误文件   {i}   ！！！！！！')
                file_path = input_path + "/" + i
                new_file_path = error_path + '/' + i
                shutil.move(file_path, new_file_path)

        # 这个进度有点XX，鉴于原作就是如此，影响不大，就没有修改。（ 按：i126@126.com ）
        # 备注：若需要合并所有txt文件为一个语料txt文件，请取消以下两行注释
        # sys.stdout.write('\r进度: ' + '%.2f%%' % (int(c) / int(b)))
        # sys.stdout.flush()


# 程序入口
if __name__ == '__main__':
    # 入口：
    main()
