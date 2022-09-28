# -*- coding: utf-8 -*-
import chardet
import codecs
import os
from django.utils.encoding import force_str
from django.utils.functional import Promise

class txtfile:


    def path_txt_encoding_to_utf8(input_path, file_ext='.txt|.csv'):
        """ 某目录下所有文本文件编码格式全部转为UTF-8
            传入参数：绝对路径
        """
        dis = os.listdir(input_path)
        for filename in dis:
            try:
                if os.path.splitext(filename)[1] in file_ext:
                    full_path_of_file = input_path + "/" + filename
                    txtfile.file_txt_encoding_to_utf8(full_path_of_file)
            except Exception as ERR:
                print('Error:', ERR)

    def file_txt_encoding_to_utf8(input_file, file_ext='.txt|.csv'):
        """ 某文本编码格式转为UTF-8
            传入参数：绝对路径下某文本文件名
        """
        if os.path.splitext(input_file)[1] in file_ext:
            f_type = txtfile.check_file_charset(input_file)
            print(input_file, "字符集为：", f_type['encoding'])
            try:
                if f_type and 'encoding' in f_type.keys() and f_type['encoding'] != 'utf-8':
                    with codecs.open(input_file, 'rb', f_type['encoding'], errors='ignore') as f:
                        content = txtfile.smart_str(f.read())
                    with codecs.open(input_file, 'wb', 'utf-8') as f:
                        f.write(content)
                    print("字符集转换成功")
                else:
                    print("字符集为 utf-8，不需要进行转换")
            except Exception as ERR:
                """
                此处对转换失败的某些GBK编码的文本文件进行了再次尝试转换。经测试有效。
                """
                try:
                    content = codecs.open(input_file, 'r', encoding='GBK').read()
                    codecs.open(input_file, 'w', encoding='UTF-8-SIG').write(content)
                    print("字符集转换成功：latin1-->UTF-8")
                except Exception as ERR:
                    print('Error:', ERR)
                    print('error ERR')
                    pass
        else:
            print(input_file,'文件(扩展名)不在允许转换范围内...')
            pass


    def check_file_charset(file):
        with open(file, 'rb') as f:
            # 此处由 chardet.detect(f.read()) 修改成了 chardet.detect(f.read()[0:1024])
            # 其目的是只读取文件头部1024个字节就对文件进行编码格式判断。加快了速度的同时，也避免了将全部读入后，可能导致无法获取真实的编码格式（或返回None，或无返回值导致异常退出读取）。部分GB2312格式的文本文件会出现此问题。
            return chardet.detect(f.read()[0:1024])

    def smart_str(s, encoding="utf-8", strings_only=False, errors="strict"):
        """
        返回表示“s”的字符串。使用“encoding”处理字节字符串编解码器。
        如果strings_only为True，则不转换（某些）非字符串类对象。
        """
        if isinstance(s, Promise):
            # 输入是gettext_lazy（）调用的结果
            return s
        return force_str(s, encoding, strings_only, errors)