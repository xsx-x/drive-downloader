import os
import json
import requests
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# הגדרות מתוך משתני סביבה (Secrets)
SERVICE_ACCOUNT_JSON = os.getenv('GDRIVE_SERVICE_ACCOUNT_JSON')
FOLDER_ID = os.getenv('TARGET_FOLDER_ID')

def download_file(url):
    """מוריד את הקובץ מהאינטרנט לשרת הזמני של GitHub"""
    local_filename = url.split('/')[-1] or "downloaded_file"
    print(f"מתחיל הורדה: {url}")
    
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    
    file_size = os.path.getsize(local_filename)
    if file_size == 0:
        raise Exception("הקובץ שהורד ריק!")
        
    print(f"הורדה הושלמה: {local_filename} ({file_size} bytes)")
    return local_filename

def upload_to_drive(file_path):
    """מעלה את הקובץ ל-Google Drive"""
    if not SERVICE_ACCOUNT_JSON:
        raise Exception("חסר מפתח Service Account ב-Secrets")

    # טעינת פרטי ההתחברות
    info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(info)
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [FOLDER_ID] if FOLDER_ID else []
    }
    
    # תמיכה בהעלאת קבצים גדולים (Resumable Media)
    media = MediaFileUpload(file_path, resumable=True)
    
    print(f"מתחיל העלאה ל-Google Drive...")
    request = service.files().create(body=file_metadata, media_body=media, fields='id')
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"התקדמות העלאה: {int(status.progress() * 100)}%")

    print(f"העלאה הסתיימה בהצלחה! מזהה קובץ: {response.get('id')}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("שגיאה: לא סופק קישור להורדה")
        sys.exit(1)
        
    target_url = sys.argv[1]
    try:
        temp_file = download_file(target_url)
        upload_to_drive(temp_file)
        # ניקוי קובץ זמני
        os.remove(temp_file)
    except Exception as e:
        print(f"שגיאה בתהליך: {str(e)}")
        sys.exit(1)
