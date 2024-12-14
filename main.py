from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import re
import string
import random
import time
from bs4 import BeautifulSoup

app = FastAPI()

class DoodStreamProcessor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Referer": "https://dood.li/",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Mobile Safari/537.36",
        })

    @staticmethod
    def extract_file_code(url):
        match = re.search(r'.*/(.*)', url.rstrip('/'))
        return match.group(1) if match else None

    @staticmethod
    def generate_random_string(length=10):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    @staticmethod
    def extract_meta_data(code):
        url = f"https://dood.li/d/{code}"
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            info_div = soup.find('div', class_='info')
            video_info = {}
            if info_div:
                title = info_div.find('h4')
                if title:
                    video_info['title'] = title.get_text(strip=True)
                
                details_div = info_div.find('div', class_='d-flex')
                if details_div:
                    length = details_div.find('div', class_='length')
                    size = details_div.find('div', class_='size')
                    upload_date = details_div.find('div', class_='uploadate')
                    
                    if length:
                        video_info['length'] = length.get_text(strip=True).replace(" ", "")
                    if size:
                        video_info['size'] = size.get_text(strip=True).replace(" ", "")
                    if upload_date:
                        video_info['upload_date'] = upload_date.get_text(strip=True)
            
            return video_info
        else:
            return None
        
    def process_url(self, url):
        file_code = self.extract_file_code(url)
        if not file_code:
            return {
                "status": "failed",
                "message": "Invalid URL format."
            }
        video_info = self.extract_meta_data(file_code)
        if not video_info:
            return {
                "status": "failed",
                "message": "Unable to extract meta data."
            }

        doodstream_url = f"https://dood.li/e/{file_code}"

        response = self.session.get(doodstream_url)

        if response.status_code == 200:
            match = re.search(r"\$.get\('([^']+)',\s*function\(data\)", response.text)
            if match:
                url_inside_get = match.group(1)
                last_value = re.search(r"/([^/]+)$", url_inside_get).group(1)
                full_url = f"https://dood.li{url_inside_get}"

                response = self.session.get(full_url)
                if response.ok:
                    part_1 = response.text
                    random_string = self.generate_random_string()
                    token = last_value
                    expiry = int(time.time() * 1000)
                    part_2 = f"{random_string}?token={token}&expiry={expiry}"
                    final_url = f"{part_1}{part_2}"
                    return {
                        "status": "success",
                        "download_url": final_url,
                        "title": video_info['title'],
                        "length": video_info['length'],
                        "size": video_info['size'],
                        "upload_date": video_info['upload_date']
                    }
                else:
                    return {
                        "status": "failed",
                        "message": "Unable to fetch the Doodstream page."
                    }
            else:
                return {
                    "status": "failed",
                    "message": "Unable to extract the required data from the Doodstream page."
                }
        else:
            return {
                "status": "failed",
                "message": f"Failed to fetch the Doodstream page. HTTP status code: {response.status_code}"
            }

class URLRequest(BaseModel):
    url: str

@app.post("/process_doodstream/")
async def process_doodstream(request: URLRequest):
    processor = DoodStreamProcessor()
    result = processor.process_url(request.url)
    return result
