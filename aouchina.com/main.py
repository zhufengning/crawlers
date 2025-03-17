import requests
import time
import random
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import ebooklib
from ebooklib import epub
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

def extract_chapters_from_toc(html_content, base_url="https://www.aouchina.com"):
    """
    Extract chapter names and links from the table of contents HTML.
    
    Args:
        html_content (str): The HTML content of the table of contents page
        base_url (str): The base URL of the website, used for creating absolute URLs
    
    Returns:
        dict: A dictionary containing book info and chapter list
    """
    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the book title
    book_title = soup.find('div', id='info').find('h1').text.strip()
    print(f"Book title: {book_title}")
    
    # Find the author
    author = soup.find('div', id='info').find_all('p')[0].text.strip().replace('作者：', '')
    print(f"Author: {author}")
    
    # Find the book description
    description = soup.find('div', id='intro').text.strip()
    
    # Extract chapters from the list div
    chapters_list = []
    
    # The chapters are in dd elements within a dl element inside the 'list' div
    list_div = soup.find('div', id='list')
    if list_div:
        chapter_elements = list_div.find_all('dd')
        
        for chapter in chapter_elements:
            link = chapter.find('a')
            if link:
                title = link.text.strip()
                url = urljoin(base_url, link.get('href'))
                
                chapters_list.append({
                    'title': title,
                    'url': url
                })
    
    # Sort chapters based on URL to ensure correct order
    # This works because the chapter URLs usually contain sequential numbers
    chapters_list.sort(key=lambda x: extract_chapter_number(x['url']))
    
    print(f"Found {len(chapters_list)} chapters")
    return {
        'book_title': book_title,
        'author': author,
        'description': description,
        'chapters': chapters_list
    }

def extract_chapter_number(url):
    """Extract the chapter number from a URL to help with sorting"""
    match = re.search(r'/(\d+)\.html$', url)
    if match:
        return int(match.group(1))
    return 0

def extract_chapter_content(html_content):
    """
    Extract chapter title and content from the chapter page HTML.
    
    Args:
        html_content (str): The HTML content of the chapter page
        
    Returns:
        dict: A dictionary containing 'title' and 'content' of the chapter
    """
    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract the chapter title
    title_element = soup.find('div', class_='bookname').find('h1')
    title = title_element.text.strip() if title_element else "Unknown Title"
    
    # Extract the chapter content
    content_element = soup.find('div', id='content')
    
    if not content_element:
        return {'title': title, 'content': ""}
    
    # Get the content HTML as a string
    content_html = str(content_element)
    
    # Clean up the content
    # Remove any script tags that might be inside the content
    content_html = re.sub(r'<script.*?</script>', '', content_html, flags=re.DOTALL)
    
    # Replace <br> tags with newlines
    content_html = content_html.replace('<br/>', '\n').replace('<br />', '\n').replace('<br>', '\n')
    content_html = content_html.replace('</p>', '\n').replace('<p>', '')
    
    # Remove all other HTML tags
    content_html = re.sub(r'</?[^>]+>', '', content_html)
    
    # Remove non-breaking spaces and other special characters
    content_html = content_html.replace('&nbsp;', ' ')
    
    # Remove excessive whitespace and normalize line breaks
    content_html = re.sub(r'\n+', '\n\n', content_html)
    content_html = re.sub(r' +', ' ', content_html)
    content_html = content_html.strip()
    
    return {
        'title': title,
        'content': content_html
    }

def download_chapter(url, headers=None, timeout=10, retries=3, delay=1):
    """
    Download and extract content from a chapter URL
    
    Args:
        url (str): URL of the chapter
        headers (dict): HTTP headers for the request
        timeout (int): Request timeout in seconds
        retries (int): Number of retry attempts
        delay (int): Delay between retries in seconds
        
    Returns:
        dict: Chapter information with title and content
    """
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Try to detect the encoding if not properly set
            response.encoding = "gb18030"
            
            # Extract the chapter content
            chapter_info = extract_chapter_content(response.text)
            chapter_info['url'] = url
            return chapter_info
            
        except requests.exceptions.RequestException as e:
            attempt += 1
            print(f"Error downloading {url}: {e}")
            print(f"Retrying ({attempt}/{retries})...")
            time.sleep(delay)  # Wait before retrying
    
    # Return an empty result if all retries failed
    return {
        'title': "Download Failed",
        'content': f"Failed to download chapter from {url} after {retries} attempts.",
        'url': url
    }

def download_book(book_url, output_folder=None, max_workers=5, delay_range=(1, 3)):
    """
    Download an entire book from a given URL
    
    Args:
        book_url (str): URL of the book's table of contents
        output_folder (str): Folder to save the epub file
        max_workers (int): Maximum number of concurrent download threads
        delay_range (tuple): Range of delay between requests (min, max) in seconds
        
    Returns:
        dict: Book information with downloaded chapters
    """
    if output_folder is None:
        output_folder = os.getcwd()
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Set up headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    # Download the table of contents
    print(f"Downloading table of contents from {book_url}")
    response = requests.get(book_url)
    response.raise_for_status()
    # Try to detect the encoding if not properly set
    response.encoding = 'gb18030'
    # Extract chapters from the table of contents
    book_info = extract_chapters_from_toc(response.text)
    
    chapters = book_info['chapters']
    
    # Download each chapter with a thread pool
    print(f"Downloading {len(chapters)} chapters...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {}
        for chapter in chapters:
            # Add a random delay to avoid overwhelming the server
            #time.sleep(random.uniform(delay_range[0], delay_range[1]))
            
            future = executor.submit(download_chapter, chapter['url'], headers)
            future_to_url[future] = chapter['url']
        
        # Process the results as they complete
        downloaded_chapters = []
        for future in tqdm(future_to_url, desc="Downloading chapters"):
            url = future_to_url[future]
            try:
                chapter_info = future.result()
                downloaded_chapters.append(chapter_info)
            except Exception as e:
                print(f"Exception while processing {url}: {e}")
    
    # Sort chapters based on URL again to ensure correct order
    downloaded_chapters.sort(key=lambda x: extract_chapter_number(x['url']))
    
    book_info['downloaded_chapters'] = downloaded_chapters
    
    return book_info


def create_epub(book_info, output_folder):
    """
    Create an EPUB file from the downloaded book information.
    
    Args:
        book_info (dict): Dictionary containing book metadata and chapters
        output_folder (str): Folder where the EPUB file will be saved
    
    Returns:
        str: Path to the saved EPUB file
    """
    book_title = book_info['book_title']
    author = book_info['author']
    description = book_info['description']
    chapters = book_info['downloaded_chapters']
    
    # Create an EPUB book
    book = epub.EpubBook()
    
    # Set metadata
    book.set_identifier(str(random.randint(100000, 999999)))
    book.set_title(book_title)
    book.set_language('zh')
    book.add_author(author)
    
    # Add book description as an introductory chapter
    intro_chapter = epub.EpubHtml(title='简介', file_name='intro.xhtml', lang='zh')
    intro_chapter.content = f'<h1>{book_title}</h1><h2>作者: {author}</h2><p>{description}</p>'
    book.add_item(intro_chapter)
    
    # Store chapter references for the TOC
    epub_chapters = [intro_chapter]
    
    for i, chapter in enumerate(chapters):
        chapter_title = chapter['title']
        chapter_content = chapter['content']
        
        # Create an EPUB chapter
        chapter_file = f'chap_{i+1}.xhtml'
        epub_chapter = epub.EpubHtml(title=chapter_title, file_name=chapter_file, lang='zh')
        chapter_content = chapter_content.replace("\n\n","\n")
        chapter_content = chapter_content.replace("\xa0","")
        content = f'<h1>{chapter_title}</h1><p>{chapter_content.replace("\n", "</p><p>")}</p>'
        content = content.replace("<p>","<p>    ")
        epub_chapter.content = content
        print(content)
        
        # Add to EPUB
        book.add_item(epub_chapter)
        epub_chapters.append(epub_chapter)
    
    # Define Table of Contents
    book.toc = (epub_chapters)
    
    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Define default EPUB spine
    book.spine = ['nav'] + epub_chapters
    
    # Save EPUB file
    epub_filename = f"{book_title}.epub"
    epub_path = os.path.join(output_folder, epub_filename)
    epub.write_epub(epub_path, book, {})
    
    print(f"EPUB created: {epub_path}")
    return epub_path

if __name__ == "__main__":
    book_info = download_book("https://www.aouchina.com/shu/6/")
    import json
    json.dump(book_info, open("book.json", "w"))
    create_epub(book_info, ".")