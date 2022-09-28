from src.textfile import txtfile

file_ext = '.txt|.csv'
yourpath = '../kehuan_error'
yourfile = '../kehuan_error/你的文本文件.txt'

def path_txt():
    txtfile.path_txt_encoding_to_utf8(yourpath, file_ext)

def file_txt():
    txtfile.file_txt_encoding_to_utf8(yourfile, file_ext)


# 程序入口
if __name__ == '__main__':
    # 入口：

    # 整体转换一个目录下所有文本文件
    # path_txt(yourpath, file_ext)

    # 单独转换一个文件
    file_txt(yourfile, file_ext)
