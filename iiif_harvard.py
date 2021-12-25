# 从哈佛的图书馆的iiif下载图片
import urllib.request
import json

# murl = "https://iiif.lib.harvard.edu/manifests/drs:430972227"
murl = input("input the IIIF Manifest url:")
s = urllib.request.urlopen(urllib.request.Request(url=murl, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
})).read().decode("utf-8")
dej = json.loads(s)
count = 1
for v in dej["sequences"][0]["canvases"]:
    print(count)
    purl = v["thumbnail"]["@id"]
    purl = str.replace(purl, ",150", ",2160")
    nr = urllib.request.urlopen(urllib.request.Request(url=purl, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
    })).read()
    f=open("" + str(count) + ".jpg", "wb")
    f.write(nr)
    count += 1
