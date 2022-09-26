# -*- coding: utf-8 -*-
########################################################################################################
# txt语料素材爬虫 - 作者：i126@126.com
# 备注：不同的txt语料素材网站爬网的规则不同，可自行根据其html源码修改截取。
########################################################################################################

import requests
import os,time
from tqdm import tqdm
# 请求头
headers = {
    'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
    'cookie':'Hm_lvt_f0807d162858098480d5e8769665057c=1663876235; clickbids=7796,7792,7795,7694,7863,7692,7750,7724,7690,7683,7760,7732,7757,83908; Hm_lpvt_f0807d162858098480d5e8769665057c=1663876596'
}

# txt语料素材网站地址
downurl = 'http://www.xxx.com'

# 创建存储路径
pathname = './txt_files/'
if not os.path.exists(pathname):
    os.mkdir(pathname)

# 第一步：获取书籍列表
def get_booklist(url):
    try:
        response = requests.get(url=url, headers=headers)
        response.encoding = 'utf-8'
        tmp_html = response.text
        tmp_html = tmp_html.split('class="pages_table">')[1]
        tmp_html = tmp_html.split('</table>')[0]
        arrstr   = tmp_html.split('</a></p></td></tr>')

        i = 0
        while i < 20:
            new_arrstr = arrstr[i].split('width="85"><a href="')[1]
            new_arrstr = new_arrstr.split('" target="_blank"')[0]
            # 找下载地址
            search_downurl(new_arrstr)
            i += 1

    except Exception:
        print('get_booklist failed')


# 第二步：获取下载地址
def search_downurl(url):

    try:
        response = requests.get(url=url,headers=headers)
        response.encoding = 'utf-8'
        tmp_html = response.text
        tmp_html = tmp_html.split('</a></li><li><a href=\'')[1]
        tmp_html = tmp_html.split('\' target=')[0]
        downfileurl = tmp_html
        basename = pathname + os.path.basename(downfileurl)

        if not os.path.exists('下载失败文件列表.txt'):
            file = open('下载失败文件列表.txt', 'w')
            file.write('')
            file.close()

        if not os.path.exists(basename):
            download(downfileurl,basename)

    except Exception:
        print('search_downurl failed......now continue......')


# 下载失败的统一放在一个文件列表中备查，如果重复下载失败了，则添加记录
def seekandsave_text(listfile,strs):
    executeRecord = strs
    rec = open(listfile, 'r+')
    lineInfos = rec.readlines()
    recordFlag = True
    for row in lineInfos:
        #print(row.strip().find(strs))
        # find函数-1表示找不到匹配内容，其他输出结果为找到的索引值
        if row.strip().find(executeRecord) != -1:
            #print("%s 已经存在！" % (executeRecord))
            # 记录过即不再记录
            recordFlag = False
            break
    if recordFlag:
        executeRecord = '%s\n' % executeRecord
        rec.write(executeRecord)
        rec.close()


# 下载失败的统一放在一个文件列表中备查，如果重复下载成功了，则清除该记录
def seekanddelete_text(listfile,strs):
    executeRecord = strs
    rec = open(listfile, 'r+')
    lineInfos = rec.readlines()
    recordFlag = True
    i = 0
    for row in lineInfos:

        #print(row.strip().find(strs))
        # find函数-1表示找不到匹配内容，其他输出结果为找到的索引值
        if row.strip().find(executeRecord) == -1:
            #print("%s 已经存在！" % (executeRecord))
            # 记录过即不再记录
            lines = i
            recordFlag = False
            break
        i += 1
    if recordFlag:
        recs = open(listfile,'w')
        for line in recs.readlines():
            if lines not in line:
                recs.write(line)
        recs.close()
    rec.close()

# 第三步：下载txt语料
def download(url: str, fname: str):
    # 用流stream的方式获取url的数据
    resp = requests.get(url, stream=True)
    resp.encoding = 'UTF-8'
    # 拿到文件的长度，并把total初始化为0
    totals = resp.headers.get('content-length', 0)

    if totals == '':
        total = 0
    else:
        total = int(totals)
    # 打开当前目录的fname文件(名字你来传入)
    # 初始化tqdm，传入总数，文件名等数据，接着就是写入，更新等操作了
    with open(fname, 'wb') as file, tqdm(
            desc=fname,
            total=total,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
    ) as bar:
        for data in resp.iter_content(chunk_size=1024, decode_unicode=False):
            size = file.write(data)
            time.sleep(0.01)
            bar.update(size)
        file_info = os.stat(fname)
        file_size = file_info.st_size
        if file_size < 1024:
            seekandsave_text('下载失败文件列表.txt',url)
            os.remove(fname)
        else:
            seekanddelete_text('下载失败文件列表.txt',url)

# 程序入口
if __name__ == '__main__':

    # 入口：
    ii = 1
    # 有多少页，ii就设置为多少
    while ii <= 321:
        print('当前页码：',ii)
        url = 'http://www.xxx.com/wenxue/list-' + str(ii) + '.html'
        get_booklist(url)
        ii += 1
    print('已成功下载结束！累计下载了',ii-1,'页')
