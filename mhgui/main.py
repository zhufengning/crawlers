from urllib.parse import quote
import json
from urllib.parse import unquote 
import subprocess
import sys
import os
import requests
from bs4 import BeautifulSoup
if len(sys.argv) >= 2:
    url = sys.argv[1]
    fjww = ["all"]
    if len(sys.argv) >= 3:
        fjww = list(map(lambda v: v.split('-'), sys.argv[2].split(',')))
    content_h = requests.get(url).text
    content_soup = BeautifulSoup(content_h, 'lxml')
    chas = content_soup.find_all(id="chapter-list-0")
    labels = content_soup.find_all("h4")
    content = list(map(
                lambda x: (
                    x[0].span.text, 
                    list(reversed(
                        list(map(
                            lambda y: (
                                y.a["href"], y.a["title"]
                            ), 
                            x[1].ul.find_all("li")
                        ))
                    ))
                )
                , zip(labels, chas)
            ))
    i = 0
    for (tp, li) in content:
        for (url, title) in li:
            i += 1
            flag = False
            for v in fjww:
                if len(v) == 1:
                    if v[0] == str(i) or v[0] == "all":
                        flag = True
                        break
                elif len(v) == 2:
                    if int(v[0]) <= i and int(v[1]) >= i:
                        flag = True
                        break
            if not(flag):
                continue
            url = "https://www.mhgui.com" + url
            path = "out/" + tp + "/" + title  + "/"
            os.makedirs(path, exist_ok=True)
            print(title)
            cha_data = BeautifulSoup(requests.get(url).text, "lxml").find_all("script")[3].text.replace('window["\\x65\\x76\\x61\\x6c"]', "console.log")
            jscmd = """
var LZString = require("./lz-string.js")
String.prototype.splic=function(f){return LZString.decompressFromBase64(this).split(f)}
""" + cha_data
            open("cmd.js", "w").write(jscmd)
            p = subprocess.Popen("node cmd.js" ,stdout=subprocess.PIPE)
            cmd_res = p.stdout.read().decode(encoding="utf-8")
            os.remove("cmd.js")
            img_json = json.loads(cmd_res[12:-13])
            for v in img_json["files"]:
                filename = path + unquote(v)
                if os.path.exists(filename):
                    continue
                pic_url = "https://i.hamreus.com" + img_json["path"] + v + "?e=" + str(img_json["sl"]["e"]) + "&m=" + img_json["sl"]["m"]
                print(filename)
                File = requests.get(pic_url, stream=True, headers={"Referer":"https://www.mhgui.com/"})
                with open(filename,'wb+') as f:
                    for chunk in File.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)

else:
    print("fuck")
