from src.textfile import txtfile

file_ext = '.txt|.csv'
yourpath = '../txt/03古典相关'
yourfile = '../txt/03古典相关/红楼梦/红楼梦.txt'

# 函数声明开始
def allpath_txt(yourpath, file_ext):
    txtfile.allpath_txt_encoding_to_utf8(yourpath, file_ext)

def path_txt(yourpath, file_ext):
    txtfile.path_txt_encoding_to_utf8(yourpath, file_ext)

def file_txt(yourfile, file_ext):
    txtfile.file_txt_encoding_to_utf8(yourfile, file_ext)
# 函数声明结束

# 程序入口
if __name__ == '__main__':
    # 入口：

    # 整体转换一个目录（含子目录）下所有文件
    allpath_txt(yourpath,file_ext)

    # 整体转换一个目录（不含子目录）下所有文本文件
    #path_txt(yourpath, file_ext)

    # 单独转换一个文件
    #file_txt(yourfile, file_ext)
