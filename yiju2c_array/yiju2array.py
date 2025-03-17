# 持续从一句api获得诗句，并将其存为c语言数组的格式（中括号除外）
import urllib.request

while True:
    f = open("out.txt", "a")
    url = "https://yijuzhan.com/api/word.php"
    response = urllib.request.urlopen(url)
    html = response.read()         # 获取到页面的源代码
    res = html.decode('utf-8')
    res = res.replace("\r", "")
    res = res.replace("——", "\\n\\t——")
    f.write('"' + res + '",\n')
    print(res)
    f.close()
