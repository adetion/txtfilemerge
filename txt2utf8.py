# -*- coding: utf-8 -*-
########################################################################################################
# 语料文本编码转换为UTF8  - 作者：i126@126.com
# 备注：自动检查文件编码格式，强制转换。对某些GBK格式转换失败的进行了单独处理。测试有效。
########################################################################################################

import chardet
import codecs
import os
from django.utils.encoding import force_str
from django.utils.functional import Promise

# 设定待转换目录
input_path = r"../txterror"
# 设定待转换文件扩展名包含哪些，以|隔开
file_ext = '.txt|.csv'


def path_txt_encoding_to_utf8(input_path):
    """ 某目录下所有文本文件编码格式全部转为UTF-8
        传入参数：绝对路径
    """
    dis = os.listdir(input_path)
    for filename in dis:
        try:
            if os.path.splitext(filename)[1] in file_ext:
                full_path_of_file = input_path + "/" + filename
                file_txt_encoding_to_utf8(full_path_of_file)
        except Exception as ERR:
            print('Error:', ERR)


def file_txt_encoding_to_utf8(input_file):
    """ 某文本编码格式转为UTF-8
        传入参数：绝对路径下某文本文件名
    """
    f_type = check_file_charset(input_file)
    print (input_file,"字符集为：",f_type['encoding'])
    try:
        if f_type and 'encoding' in f_type.keys() and f_type['encoding'] != 'utf-8':
            with codecs.open(input_file, 'rb', f_type['encoding'],errors='ignore') as f:
                content = smart_str(f.read())
            with codecs.open(input_file, 'wb', 'utf-8') as f:
                f.write(content)
            print ("字符集转换成功")
        else:
            print("字符集为 utf-8，不需要进行转换")
    except Exception as ERR:
        """
        此处对转换失败的某些GBK编码的文本文件进行了再次尝试转换。经测试有效。
        """
        try:
            content = codecs.open(input_file, 'rb', encoding='gbk').read()
            codecs.open(input_file, 'w', encoding='UTF-8-SIG').write(content)
            print("字符集转换成功：GBK --> UTF-8")
        except Exception as ERR1:
            try:
                content = codecs.open(input_file, 'rb', encoding='gb18030', errors='ignore').read()
                codecs.open(input_file, 'w', encoding='UTF-8-SIG').write(content)
                print("字符集转换成功：gb18030 --> UTF-8")
            except Exception as ERR2:
                print('error ERR2')
                pass


def check_file_charset(file):
    with open(file, 'rb') as f:
        # 此处由 chardet.detect(f.read()) 修改成了 chardet.detect(f.read()[0:1024])
        # 其目的是只读取文件头部1024个字节就对文件进行编码格式判断。加快了速度的同时，也避免了全部读入后，可能导致无法获取真实的编码格式（或返回None，或无返回值导致异常退出读取）。部分GB2312格式的文本文件会出现此问题。
        return chardet.detect(f.read()[0,1024])


def smart_str(s, encoding="utf-8", strings_only=False, errors="strict"):
    """
    返回表示“s”的字符串。使用“encoding”处理字节字符串编解码器。
    如果strings_only为True，则不转换（某些）非字符串类对象。
    """
    if isinstance(s, Promise):
        # 输入是gettext_lazy（）调用的结果
        return s
    return force_str(s, encoding, strings_only, errors)


path_txt_encoding_to_utf8(input_path)
