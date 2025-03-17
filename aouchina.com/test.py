from main import download_book, create_epub
import json

# book_info = download_book("https://www.aouchina.com/shu/6/")
# json.dump(book_info, open("book.json", "w"))
book_info=json.load(open("book.json", "r"))
create_epub(book_info, ".")