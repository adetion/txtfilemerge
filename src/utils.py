# -*- coding: UTF-8 -*-
########################################################################################################
# 类文件：语料文本语言编码转码与内容数据初步清洗 - 作者：i126@126.com
########################################################################################################

import chardet
import codecs
import os
import re
import io
from django.utils.encoding import force_str
from django.utils.functional import Promise
from src.langconv import Converter

class filter:

    def is_chinese(uchar):
        """判断一个unicode是否是汉字"""
        if uchar >= u'\u4e00' and uchar <= u'\u9fa5':
            return True
        else:
            return False

    def is_number(uchar):
        """判断一个unicode是否是半角数字"""
        if uchar >= u'\u0030' and uchar <= u'\u0039':
            return True
        else:
            return False

    def is_Qnumber(uchar):
        """判断一个unicode是否是全角数字"""
        if uchar >= u'\uff10' and uchar <= u'\uff19':
            return True
        else:
            return False

    def is_alphabet(uchar):
        """判断一个unicode是否是半角英文字母"""
        if (uchar >= u'\u0041' and uchar <= u'\u005a') or (uchar >= u'\u0061' and uchar <= u'\u007a'):
            return True
        else:
            return False

    def is_Qalphabet(uchar):
        """判断一个unicode是否是全角英文字母"""
        if (uchar >= u'\uff21' and uchar <= u'\uff3a') or (uchar >= u'\uff41' and uchar <= u'\uff5a'):
            return True
        else:
            return False

    def is_other(uchar):
        """判断是否非汉字，数字和英文字符"""
        if not (filter.is_chinese(uchar) or filter.is_number(uchar) or filter.is_alphabet(uchar)):
            return True
        else:
            return False

    def Q2B(uchar):
        """单个字符 全角转半角"""
        inside_code = ord(uchar)
        if inside_code == 0x3000:
            inside_code = 0x0020
        else:
            inside_code -= 0xfee0
        if inside_code < 0x0020 or inside_code > 0x7e:  # 转完之后不是半角字符返回原来的字符
            return uchar
        return chr(inside_code)

    def stringQ2B(ustring):
        """把字符串全角转半角"""
        return "".join([filter.Q2B(uchar) for uchar in ustring])

    def stringpartQ2B(ustring):
        """把字符串中数字和字母全角转半角"""
        return "".join([filter.Q2B(uchar) if filter.is_Qnumber(uchar) or filter.is_Qalphabet(uchar) else uchar for uchar in ustring])


    def stemming(string):
        # 标点符号/特殊符号词典
        PUNCTUATION_LIST = [
            " ", "　", ",", "，", ".", "。", "!", "?", ";", "、", "~", "|", "·", ":", "+", "\-", "—", "*", "/", "／", "\\",
            "%",
            "=", "\"", "'", "（", "）", "(", ")", "\[", "\]", "【", "】", "{", "}", "《", "》", "→", "←", "↑", "↓", "↖", "↗",
            "↙",
            "↘", "$", "%", "_", "#", "@", "&", "√", "X", "♂", "♡", "♿", "⭐", "❤", "■", "⭕",
            "✂", "✈", "█", "ð", "▓", "ж", "⛽", "☞", "♥", "☯", "⚽", "☺", "㊙", "✨", "＊", "✌", "⚡", "⛷", "✊", "☔", "✌", "░"
        ]

        # 将大于等于2个连续的相同标点符号均替换为1个
        punctuation_list = "".join(PUNCTUATION_LIST)
        for match_punctuation in re.findall("([" + punctuation_list + "])\\1{2,}", string):
            string = re.sub("[" + match_punctuation + "]{2,}", match_punctuation * 3, string)
        string = re.sub("-{2,}", "---", string)  # 处理特殊的短横杠

        # 将大于等于3个连续的中文汉字均替换为3个
        for chinese_character in re.findall("([\u4e00-\u9fa5])\\1{3,}", string):
            string = re.sub("[" + chinese_character + "]{3,}", chinese_character * 3, string)

        # 将大于等于3个连续的英文字母均替换为3个
        for chinese_character in re.findall("([A-Za-z])\\1{3,}", string):
            string = re.sub("[" + chinese_character + "]{3,}", chinese_character * 3, string)

        return string

    def filter_phone(linestr):
        for i in re.findall(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', linestr):
            linestr = linestr.replace(i,'')
        return linestr

    def filter_email(linestr):
        email = re.compile(r'[a-z0-9\-\.]+@[0-9a-z\-\.]+')
        emailset = set()  # 创建集合
        for em in email.findall(linestr):
            emailset.add(em)
        for eml in sorted(emailset):
            linestr = linestr.replace(eml,'')
        return linestr


    def filter_cn(linestr):
        return re.sub('[\u4e00-\u9fa5]', '', linestr)

    def filter_emoji(linestr, restr=''):
        # 过滤表情
        try:
            co = re.compile(u'['u'\U0001F300-\U0001F64F' u'\U0001F680-\U0001F6FF'u'\u2600-\u2B55]+')
        except re.error:
            co = re.compile(u'('u'\ud83c[\udf00-\udfff]|'u'\ud83d[\udc00-\ude4f\ude80-\udeff]|'u'[\u2600-\u2B55])+')
        return co.sub(restr, linestr)

    def filter_html(text):
        htmltags = ['div', 'ul', 'li', 'ol', 'p', 'span', 'form', 'br',
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'hr', 'input',
                    'title', 'table', 'tbody', 'a',
                    'i', 'strong', 'b', 'big', 'small', 'u', 's', 'strike',
                    'img', 'center', 'dl', 'dt', 'font', 'em',
                    'code', 'pre', 'link', 'meta', 'iframe', 'ins']
        # blocktags = ['script', 'style']
        tabletags = ['tr', 'th', 'td']
        for tag in htmltags:
            # filter html tag with its attribute descriptions
            text = re.sub(f'<{tag}[^<>]*[/]?>', '', text)
            text = re.sub(f'</{tag}>', '', text)
        # '''
        buffer = io.StringIO(text)
        text = ''
        line = buffer.readline()
        while line is not None and line != '':
            for tag in tabletags:
                if '<' + tag in line or '</' + tag in line:
                    if len(line) < 2:
                        # len('\n') == 1
                        if ascii(line) == '\\n':
                            line = ''
                    while '\n' in line:
                        line = line.replace('\n', '')
                    line = re.sub(f'<{tag}[^<>]*[/]?>', '', line)
                    line = re.sub(f'</{tag}>', '', line)
                    # filter multiple spaces
                    line = line.replace(' ', '')
            text += line
            line = buffer.readline()
        # '''

        # filter multiple empty lines
        while '\n\n' in text:
            text = text.replace("\n\n", '\n')
        return text

    def filter_url(linestr):
        regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        url = re.findall(regex, linestr)
        newlist = []
        for i in range(len(url)):
            newlist.append(filter.filter_cn(url[i]))
        for j in range(len(newlist)):
            linestr = linestr.replace(newlist[j], '')
        return linestr

    def filter_html_tags(linestr):
        dr = re.compile(r'<[^>]+>', re.S)
        dd = dr.sub('', linestr)
        return dd

    def filter_Html_Tag(htmlstr):
        '''
        过滤html中的标签
        '''
        # 兼容换行
        s = htmlstr.replace('\r\n', '\n')
        s = htmlstr.replace('\r', '\n')

        # 规则
        re_cdata = re.compile('//<!\[CDATA\[[^>]*//\]\]>', re.I)  # 匹配CDATA
        re_script = re.compile('<\s*script[^>]*>[\S\s]*?<\s*/\s*script\s*>', re.I)  # script
        re_style = re.compile('<\s*style[^>]*>[\S\s]*?<\s*/\s*style\s*>', re.I)  # style
        re_br = re.compile('<br\\s*?\/??>', re.I)  # br标签换行
        re_p = re.compile('<\/p>', re.I)  # p标签换行
        re_h = re.compile('<[\!|/]?\w+[^>]*>', re.I)  # HTML标签
        re_comment = re.compile('<!--[^>]*-->')  # HTML注释
        re_hendstr = re.compile('^\s*|\s*$')  # 头尾空白字符
        re_lineblank = re.compile('[\t\f\v ]*')  # 空白字符
        re_linenum = re.compile('\n+')  # 连续换行保留1个
        re_blanks = re.compile(' +')  # 连续多个空格

        # 处理
        s = re_cdata.sub('', s)  # 去CDATA
        s = re_script.sub('', s)  # 去script
        s = re_style.sub('', s)  # 去style
        s = re_br.sub('\n', s)  # br标签换行
        s = re_p.sub('\n', s)  # p标签换行
        s = re_h.sub('', s)  # 去HTML标签
        s = re_comment.sub('', s)  # 去HTML注释
        # s = re_lineblank.sub('', s)  # 去空白字符
        s = re_linenum.sub('\n', s)  # 连续换行保留1个
        s = re_hendstr.sub('', s)  # 去头尾空白字符
        s = re_blanks.sub(' ',s) # 连续空格保留1个

        # 替换实体
        s = filter.replaceCharEntity(s)
        s = " ".join(s.split())

        return s

    def replaceCharEntity(htmlStr):
        '''
          替换html中常用的字符实体
          使用正常的字符替换html中特殊的字符实体
          可以添加新的字符实体到CHAR_ENTITIES 中
          CHAR_ENTITIES是一个字典前面是特殊字符实体  后面是其对应的正常字符
          :param htmlStr:
          '''
        CHAR_ENTITIES = {'nbsp': ' ', '160': ' ',
                         'lt': '<', '60': '<',
                         'gt': '>', '62': '>',
                         'amp': '&', '38': '&',
                         'quot': '"', '34': '"', }
        re_charEntity = re.compile(r'&#?(?P<name>\w+);')
        sz = re_charEntity.search(htmlStr)
        while sz:
            entity = sz.group()  # entity全称，如>
            key = sz.group('name')  # 去除&;后的字符如（" "--->key = "nbsp"）    去除&;后entity,如>为gt
            try:
                htmlStr = re_charEntity.sub(CHAR_ENTITIES[key], htmlStr, 1)
                sz = re_charEntity.search(htmlStr)
            except KeyError:
                # 以空串代替
                htmlStr = re_charEntity.sub('', htmlStr, 1)
                sz = re_charEntity.search(htmlStr)
        return htmlStr

    def filter_cn_space(linestr):
        dd = re.sub(r'(?<=[\u4e00-\u9fa5]) +(?=[\u4e00-\u9fa5])', '', linestr)
        dd = re.sub("(?<![ -~]) (?![ -~])", "", dd)
        return dd

    def clean_cn_line(s):
        """
        :param s: 清洗爬取的中文语料格式
        :return:
        """
        import re
        from string import digits, punctuation
        rule = re.compile(
            u'[^a-zA-Z.,;《》？！“”‘’@#￥%…&×（）——+【】{};；●，。&～、|\s:：' + digits + punctuation + '\u4e00-\u9fa5]+')
        s = re.sub(rule, '', s)
        s = re.sub('[、]+', '，', s)
        s = re.sub('\'', '', s)
        s = re.sub('[#]+', '，', s)
        s = re.sub('[?]+', '？', s)
        s = re.sub('[;]+', '，', s)
        s = re.sub('[,]+', '，', s)
        s = re.sub('[!]+', '！', s)
        s = re.sub('[.]+', '.', s)
        s = re.sub('[，]+', '，', s)
        s = re.sub('[。]+', '。', s)
        s = s.strip().lower()
        return s

    def clean_en_line(s):
        """
        :param s: 清洗爬取的外文语料格式
        :return:
        """
        import re
        from string import digits, punctuation
        rule = re.compile(
            u'[^.,;《》？！“”‘’@#￥%…&×（）——+【】{};；●，。&～、|\s:：' + digits + punctuation + '\u4e00-\u9fa5]+')
        s = re.sub(rule, '', s)
        s = re.sub('[、]+', '，', s)
        s = re.sub('\'', '', s)
        s = re.sub('[#]+', '，', s)
        s = re.sub('[?]+', '？', s)
        s = re.sub('[;]+', '，', s)
        s = re.sub('[,]+', '，', s)
        s = re.sub('[!]+', '！', s)
        s = re.sub('[.]+', '.', s)
        s = re.sub('[，]+', '，', s)
        s = re.sub('[。]+', '。', s)
        s = s.strip().lower()
        return s

    def zh_to(text, flag=''):  # text为要转换的文本，flag=0代表简化繁，flag=1代表繁化简
        if flag == 'zh2cn':
            rule = 'zh-hans'
        elif flag == 'zh2tw':
            rule = 'zh-hant'
        else:
            return text
        return Converter(rule).convert(text)

    def linedata(line='', flag=''):
        # 过滤前后空格
        line = line.strip()
        # 过滤表情
        line = filter.filter_emoji(line)
        # 过滤html
        line = filter.filter_html(line)
        # 过滤html标签
        line = filter.filter_html_tags(line)
        # 二次过滤html
        line = filter.filter_Html_Tag(line)
        # 三次过滤url地址
        line = filter.filter_url(line)
        # 过滤email电子邮件地址
        line = filter.filter_email(line)
        # 过滤电话号码
        line = filter.filter_phone(line)
        # 过滤中文字符之间空格
        line = filter.filter_cn_space(line)
        # 文本规范化(侧重全角转半角)
        line = filter.stringpartQ2B(line)
        # 文本变形词标准化
        line = filter.stemming(line)
        # 文本简繁体转换
        line = filter.zh_to(line,flag)
        # 过滤中文字符之间空格
        line = filter.filter_cn_space(line)
        # 空行清空
        if line == '\n': line = ''
        return line

    def file(inputfile, outpath, file_ext='.txt|.csv', flag=''):
        out_txt = outpath + '/' + os.path.basename(inputfile)
        with open(inputfile, "r", encoding='utf-8') as f1, \
                open(out_txt, "w", encoding='utf-8') as f2:
            for line in f1:
                line = filter.linedata(line,flag)
                if line == ' ' or line == '':
                    line = line.strip("")
                    f2.write(line)
                else:
                    f2.write("{}\n".format(line))
            f2.write('\n')
            f2.close()
        print(out_txt,' 初级数据清洗完毕！')

    def allpath(input_path, outpath, file_ext='.txt|.csv', flag=''):
        for dirpath, dirnames, filenames in os.walk(input_path):
            for filename in filenames:
                try:
                    if os.path.splitext(filename)[1].lower() in file_ext:
                        full_path_of_file = dirpath + "/" + filename
                        toutf8.file_txt_encoding_to_utf8(full_path_of_file, file_ext)
                        filter.file(full_path_of_file,outpath,file_ext,flag)
                except Exception as ERR:
                    print('Error:', ERR)


class toutf8:

    def allpath(yourpath, file_ext):
        toutf8.allpath_txt_encoding_to_utf8(yourpath, file_ext)

    def path(yourpath, file_ext):
        toutf8.path_txt_encoding_to_utf8(yourpath, file_ext)

    def file(yourfile, file_ext):
        toutf8.file_txt_encoding_to_utf8(yourfile, file_ext)

    def allpath_txt_encoding_to_utf8(input_path, file_ext='.txt|.csv'):
        """ 某目录下(含子目录)所有文本文件编码格式全部转为UTF-8
            传入参数：绝对路径
        """
        for dirpath, dirnames, filenames in os.walk(input_path):
            for filename in filenames:
                # print(os.path.join(dirpath, filename))
                try:
                    if os.path.splitext(filename)[1].lower() in file_ext:
                        full_path_of_file = dirpath + "/" + filename
                        toutf8.file_txt_encoding_to_utf8(full_path_of_file)
                except Exception as ERR:
                    print('Error:', ERR)

    def path_txt_encoding_to_utf8(input_path, file_ext='.txt|.csv'):
        """ 某目录下（不含子目录）所有文本文件编码格式全部转为UTF-8
            传入参数：绝对路径
        """
        dis = os.listdir(input_path)
        for filename in dis:
            try:
                if os.path.splitext(filename)[1].lower() in file_ext:
                    full_path_of_file = input_path + "/" + filename
                    toutf8.file_txt_encoding_to_utf8(full_path_of_file)
            except Exception as ERR:
                print('Error:', ERR)

    def file_txt_encoding_to_utf8(input_file, file_ext='.txt|.csv'):
        """ 某文本编码格式转为UTF-8
            传入参数：绝对路径下某文本文件名
        """
        if os.path.splitext(input_file)[1].lower() in file_ext:
            f_type = toutf8.check_file_charset(input_file)
            print(input_file, "原始字符集为：", f_type['encoding'])
            try:
                if f_type and 'encoding' in f_type.keys() and f_type['encoding'] != 'utf-8':
                    with codecs.open(input_file, 'rb', f_type['encoding'], errors='ignore') as f:
                        content = toutf8.smart_str(f.read())
                    with codecs.open(input_file, 'wb', 'utf-8') as f:
                        f.write(content)
                    print("字符集转换成功：自动")
                else:
                    pass
                    #print("字符集为 utf-8，无需转换")
            except Exception as ERR:
                """
                此处对转换失败的某些GBK编码的文本文件进行了再次尝试转换。先测试用GBK解，再测试用GB18030解，经测试有效。
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
                        try:
                            content = codecs.open(input_file, 'rb', encoding='big5').read()
                            codecs.open(input_file, 'w', encoding='UTF-8-SIG').write(content)
                            print("字符集转换成功：gb18030 --> UTF-8")
                        except Exception as ERR3:
                            print('error ERR3')
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

    def open_txt(input_file):
        """
        读取超大文本
        :param input_file: 文本文件
        :return: 行数据
        示例：
        for line in open_txt(input_file):
            print(line)
        """
        with open(input_file, 'r+') as f:
            while True:
                line = f.readline()
                if not line:
                    return
                yield line.strip()



