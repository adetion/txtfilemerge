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
from tqdm import tqdm
import time

# 注释全局变量
global notes
notes = ''

class filter:
    """ 清洗过滤类 """

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
        """ 文本变形词标准化 """
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

        # 将特殊引号置换为统一的双引号
        string = string.replace('「','“')
        string = string.replace('」', '”')

        return string

    def filter_phone(linestr):
        """ 过滤电话号码 """
        for i in re.findall(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', linestr):
            linestr = linestr.replace(i,'')
        return linestr

    def filter_email(linestr):
        """ 过滤电子邮件 """
        email = re.compile(r'[a-z0-9\-\.]+@[0-9a-z\-\.]+')
        emailset = set()  # 创建集合
        for em in email.findall(linestr):
            emailset.add(em)
        for eml in sorted(emailset):
            linestr = linestr.replace(eml,'')
        return linestr


    def filter_cn(linestr):
        """ 过滤中文字符 """
        return re.sub('[\u4e00-\u9fa5]', '', linestr)

    def filter_emoji(linestr, restr=''):
        """ 过滤表情 """
        try:
            co = re.compile(u'['u'\U0001F300-\U0001F64F' u'\U0001F680-\U0001F6FF'u'\u2600-\u2B55]+')
        except re.error:
            co = re.compile(u'('u'\ud83c[\udf00-\udfff]|'u'\ud83d[\udc00-\ude4f\ude80-\udeff]|'u'[\u2600-\u2B55])+')
        return co.sub(restr, linestr)

    def filter_html(text):
        """ 过滤HTML """
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
        """ 过滤非HTML嵌套的URL网址 """
        regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        url = re.findall(regex, linestr)
        newlist = []
        for i in range(len(url)):
            newlist.append(filter.filter_cn(url[i]))
        for j in range(len(newlist)):
            linestr = linestr.replace(newlist[j], '')
        return linestr

    def filter_html_tags(linestr):
        """ 过滤部分HTML标签 """
        dr = re.compile(r'<[^>]+>', re.S)
        dd = dr.sub('', linestr)
        return dd

    def filter_Html_Tag(htmlstr):
        """ 过滤 HTML 标签 """
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
        # s = re_lineblank.sub('', s)  # 去空白字符，鉴于会对英文字符间隔造成影响，此处暂不过滤空格
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
        """ 过滤中文字符间隔 """
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

    def zh_to(text, flag=''):
        """ text 为要转换的文本，flag=zh2tw 代表简化繁，flag=zh2cn 代表繁化简，默认不转 """
        if flag == 'zh2cn':
            rule = 'zh-hans'
        elif flag == 'zh2tw':
            rule = 'zh-hant'
        else:
            return text
        return Converter(rule).convert(text)

    def filter_hidden_char(linestr):
        """ 过滤不可见字符 """
        for i in range(0, 32):
            linestr = linestr.replace(chr(i), '')
        linestr = linestr.replace(chr(127), '')
        return linestr

    def linedata(line='', flag=''):
        """ 主函数：调用清洗过滤规则，对行数据进行清洗 """
        # 过滤前后空格
        line = line.strip()
        # 过滤不可见字符
        line = filter.filter_hidden_char(line)
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
        # 过滤中文字符之间空格。二次过滤中文字符间空格的目的在于，有可能简繁体转码中出现异常情况。但测试中异常情况暂未发现。
        line = filter.filter_cn_space(line)
        # 符合条件的强行删行
        line = filter_delline(line)
        # 空行清空
        if line == '\n': line = ''
        return line

    def file(inputfile, outpath, file_ext='.txt|.csv', flag=''):
        """ 单文件数据清洗，带进度条 """
        out_txt = outpath + '/' + os.path.basename(inputfile)
        total = sum(1 for _ in open(inputfile))
        with open(inputfile, "r", encoding='utf-8') as f1, \
                open(out_txt, "w", encoding='utf-8') as f2, tqdm(
                    desc='文件：' + os.path.basename(inputfile) + ' 编码：' + notes + ' ',
                    unit=' 行',
                    total=total,
                    unit_scale=True,
                    ncols=120,
            ) as bar:
            for line in f1:
                line = filter.linedata(line,flag)
                time.sleep(0.001)
                bar.update()
                if line == ' ' or line == '':
                    line = line.strip("")
                    f2.write(line)
                else:
                    f2.write("{}\n".format(line))
            bar.close()
            f2.write('\n')
            f2.close()

        #print(out_txt,' 初级数据清洗完毕！')

    def allpath(input_path, outpath, file_ext='.txt|.csv', flag=''):
        """ 目录级数据清洗，含所有子目录下文件 """
        print('='*50,'数据清洗中','='*50)
        for dirpath, dirnames, filenames in os.walk(input_path):
            for filename in filenames:
                try:
                    if os.path.splitext(filename)[1].lower() in file_ext:
                        full_path_of_file = dirpath + "/" + filename
                        # 强制转码UTF-8
                        toutf8.file_txt_encoding_to_utf8(full_path_of_file, file_ext)
                        # 逐个文件清洗
                        filter.file(full_path_of_file,outpath,file_ext,flag)
                except Exception as ERR:
                    print('Error:', ERR)
        print('=' * 50, '数据清洗完成', '=' * 50)


class toutf8:
    """ 转码utf-8类 """

    def allpath(yourpath, file_ext):
        """ 目录级转码，含子目录 """
        toutf8.allpath_txt_encoding_to_utf8(yourpath, file_ext)

    def path(yourpath, file_ext):
        """ 单目录转码，不含子目录 """
        toutf8.path_txt_encoding_to_utf8(yourpath, file_ext)

    def file(yourfile, file_ext):
        """ 单文件转码 """
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
        global notes
        if os.path.splitext(input_file)[1].lower() in file_ext:
            f_type = toutf8.check_file_charset(input_file)
            #print(input_file, "原始字符集为：", f_type['encoding'])
            #notes = "原始字符集为：" + f_type['encoding']
            # print(notes)
            try:
                if f_type and 'encoding' in f_type.keys() and f_type['encoding'] != 'utf-8':
                    with codecs.open(input_file, 'rb', f_type['encoding'], errors='ignore') as f:
                        content = toutf8.smart_str(f.read())
                    with codecs.open(input_file, 'wb', 'utf-8') as f:
                        f.write(content)
                    notes = "字符集转换成功：自动"
                    # print(notes)
                else:
                    pass
                    notes = "utf-8"
                    #print("字符集为 utf-8，无需转换")
            except Exception as ERR:
                """
                此处对转换失败的某些其他编码的文本文件进行了再次尝试转换。反复测试用GBK、GB18030、BIG5解，经测试有效。
                """
                try:
                    content = codecs.open(input_file, 'rb', encoding='gbk').read()
                    codecs.open(input_file, 'w', encoding='UTF-8-SIG').write(content)
                    notes = "字符集转换成功：GBK --> UTF-8"
                    # print(notes)
                except Exception as ERR1:
                    try:
                        content = codecs.open(input_file, 'rb', encoding='gb18030', errors='ignore').read()
                        codecs.open(input_file, 'w', encoding='UTF-8-SIG').write(content)
                        notes = "字符集转换成功：gb18030 --> UTF-8"
                        # print(notes)
                    except Exception as ERR2:
                        try:
                            content = codecs.open(input_file, 'rb', encoding='big5').read()
                            codecs.open(input_file, 'w', encoding='UTF-8-SIG').write(content)
                            notes = "字符集转换成功：big5 --> UTF-8"
                            #print(notes)
                        except Exception as ERR3:
                            print('error ERR3')
                            pass

        else:
            print(input_file,'文件(扩展名)不在允许转换范围内...')
            pass


    def check_file_charset(file):
        """ 获取文件编码格式 """
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


def filter_delline(line):
    """ 行清洗 """
    # 字符串过滤。以 | 进行间隔的长字符串。每个单独的字符串之间必须用 | 进行间隔。
    """ 要严格过滤掉的字符串，即找到该字符串，则直接置换为空。举例说明过滤的优先级：比如先过滤'序言'，后过滤'序'，则是不至于漏掉'言'字。 """
    WORDS_ARR = '分割线|该章节已被锁定|三五中文网|(大结局)|（大结局）|未完待续:|未完待续：|未完待续|人物介绍:|人物介绍：|人物介绍|楔子|正文卷|正文卷:|正文卷：|全部章节|' \
                '红袖添香网|红袖添香文学网|绿色资源网|全文完|全书完|Tag列表：|Tag列表:|Tag列表|downcc.com|久久电子书|用户上传之内容|作品仅供读者预览|搜索关键字|本图书由|' \
                '八_零_电_子_书|下载后24小时|更多txt|新书开张|Bud1%E%DSDB`|Bud1%E%DSDB|作者：|作者:|作者|内容简介：|内容简介:|内容简介|内容提要：|内容提要:|内容提要|作品赏析：|作品赏析:|作品赏析' \
                '|（完）|(完)|( 完 )|（ 完 ）|{全文完}|{ 全文完 }|-正文-|序言|前言|序幕|序言|知乎|简介：|</div>|<br/>|bxzw.com|</p>|&nbsp|&nbsp;|( )|&amp;|(图)|[目录]|，且听下回分解|7017k' \
                '|正文'
    """ 要严格过滤掉的字符串，即找到该字符串，则直接置换为空 """
    line = re.sub(WORDS_ARR, '', line)



    # 行首过滤。数组形式。数组中每个元素均要用单引号框住。数组元素之间用逗号间隔。此处也是要注意过滤的优先级的。比如  （《,》） 先过滤，再过滤 《,》
    """ 行首开始两字符串间，含两字符串及中间包含部分，一起清除 """
    LINESTART_BETWEEN2WORDS = ['《(,)》', '（《,》）', '【,】', '本章第,章', '第,章：', '第,章，', '第,章、', '第,章.', '第,章','第,节：',
                               '第,节', '第,篇', '第,幕', '第,首', '第,卷', '第,段', '第,部分', '第,部', '第,回', '第,册', '第,炮',
                               '第,季', '第,集', '第,更', '###第,章', '未知,后来如何', '第,折', '第,出']

    """ 行首开始两字符串间，含两字符串及中间包含部分，一起清除 """
    array_str_length = len(LINESTART_BETWEEN2WORDS)
    for k in range(array_str_length):
        array_str = LINESTART_BETWEEN2WORDS[k]
        start_str = array_str.split(',')[0]
        end_str = array_str.split(',')[1]
        if start_str in line:
            if end_str in line:
                line = deleteByStartAndEnd(line, start_str, end_str)
                if start_str in line:
                    if end_str in line:
                        line = deleteByStartAndEnd(line, start_str, end_str)
        else:
            line = line

    # 字符过滤。注意，包含了过滤所有空格。如果文中英文较多，则需要将空格字符去掉。另行处理。
    """ 此处主要简单过滤掉一些非法或者不常见的干扰行文的字符 """
    FILTER_WORDS = '＂\'・＃＄＆＇＊＋－-／~＜＝=＞◆★●☆@€＠［＼］＾＿｀｛｜｝～｟｠｢｣､\u3000、〃〈〉【】〔〕〖〗〘〙〚〛〜〟〰〾〿﹑﻿'
    """ 字符串中多空格变单空格,不需要的字符过滤掉 """
    words = '[' + FILTER_WORDS + ']'
    line = re.sub(words, '', line)

    # 整行过滤。数组形式。数组中每个元素均要用单引号框住。数组元素之间用逗号间隔。
    """ 行内只要包含该字符串，则整行清除 """
    DEL_ROW_WORDS = ['找好书，看好书', '本作品来自互联网', '连载完毕', '本站所有资源', '内容简介：', '作者：', '・ 序言',
                     '导读：', '序言：', '仅供试阅', '简介:', 'chapter', '跪求各位', '有话要说：', '文案：',
                     '内容标签：', '-正文-', '本章字数', '17k.com', '更新时间:', '更新时间：', '内容介绍：', '内容介绍:',
                     '主角资料', '正文第', '分节阅读', '书名：', '24小时内删除', '备注：', '——BY', '请支持正版',
                     '标签：', '晋江文学', '总点击', '本文又', '全本精校', '?书名:','关注公众号', '切勿商用', '书友上传',
                     '起点首页', '起点女生网', '鲜花支持哦', '邀请驻站', '上推荐了', '起点榜', '正文故事', '故事背景：', '故事背景:',
                     '作品相关', '鲸鱼阅读', '编辑推荐', '久久网', '起点读书', '起点app', '银河奖', '出版社:', '出版时间',
                     "ISBN", '本书', '推荐收藏', '更多精彩图书', 'qisuwang','txtsk.com.cn', 'txt书库',
                     '群已成立', 'lvsetxt.com', '全书完', '上一页', 'blackjasmine', '后一页', '前一页', '回目录',
                     'abada.cn', 'txt小说', '电子书来自', '小说开头', '*****', '更新时间', '起点中文网', '书友群',
                     '剧情省略', '存稿已到', '由于最近比较忙', '没时间上线', '喜欢cosplay的朋友们', '看来打错字了',
                     '免费小说阅读', '真 意 书 盟', '牛bb小说阅读网', '翻译：', '修订：', '终审：', 'DDD', 'PS.', 'PS:',
                     'PS：', '下一页', '主要人物表', 'shouda8', '作者有话说','章节内容开始','本文内容由','书籍介绍:',
                     '内容版权','一鸣扫描，雪儿校对','小说来自','-开始-','---','TXT电子书','全本小说','-结束-',
                     'txt80.com', '(求收藏求推荐)', '求收藏', '求月票', '求推荐', '求三连', '点赞收藏', '求转发',
                     '写在前面', '本站 0', '本站0','cncnz.net','┗','┃','┏','谢谢大家，爱你们','喜欢网配的',
                     '免费电子书','电子书城','q━','qrqr','(n)','┊','t━','瑶池电子书','发新文了','所以如果大家还想继续看下去的话',
                     '(*^','∩_∩','（￣￣','如有雷同，实属巧合','16K小说网','┇','主角：','配角：','书快电子书','书快书快',
                     '（放心','―END―','― END ―'
                     ]
    # 以下是过滤不干净的，单独进行过滤处理。部分有用文字虽然也被清除，但整体对文章没多大影响。如果过滤关键字为纯英文的，则统一自动转小写进行匹配。
    """ 对过滤仍然不干净的，单独处理。这个处理手段比较粗暴。只要包含过滤词，则整行清除。 """
    array_str_length = len(DEL_ROW_WORDS)
    for l in range(array_str_length):
        import string
        for m in DEL_ROW_WORDS[l]:
            if m in string.ascii_lowercase + string.ascii_uppercase:
                if DEL_ROW_WORDS[l].lower() in line.lower():
                    line = ''
            elif DEL_ROW_WORDS[l] in line:
                line = ''

    line = line.replace('。。','。')
    line = line.replace('，，', '，')
    line = line.replace('，。', '。')
    line = line.replace('。，', '，')
    return line


def deleteByStartAndEnd(s, start, end):
    """ 清洗某字符串中，两子字符串（含两字符串）间内容 """
    # 找出两个字符串在原始字符串中的位置，开始位置是：开始始字符串的最左边第一个位置，结束位置是：结束字符串的最右边的第一个位置
    x1 = s.index(start)
    x2 = s.index(end) + len(end)  # s.index()函数算出来的是字符串的最左边的第一个位置
    # 找出两个字符串之间的内容
    x3 = s[x1:x2]
    # 将内容替换为控制符串
    result = s.replace(x3, "")
    return result


def formatsize(bytes):
    """ 字节换算 """
    try:
        bytes = float(bytes)  # 默认字节
        kb = bytes / 1024  # 换算KB
    except:
        print("字节格式有误")
        return "Error"

    if kb >= 1024:
        M = kb / 1024  # KB换成M
        if M >= 1024:
            G = M / 1024
            return "%fG" % G
        else:
            return "%fM" % M
    else:
        return "%fkb" % kb


def Getfile(path):
    """ 获取文件大小 """
    try:
        size = os.path.getsize(path)
        return formatsize(size)
    except:
        print("获取文件大小错误")

