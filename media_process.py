import requests
import os
from pydub import AudioSegment


def download_media(url):
    file_extension = os.path.splitext(url)[-1].lower()
    file_path = f"./.cache/Temp{file_extension}"
    print(f"下载文件 {file_extension}")
    response = requests.get(url, stream=True)
    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return [file_path, file_extension]


def export_wav(file_path, file_extension):
    print("尝试转换为WAV格式音频")
    if file_extension == ".mp3":
        audio = AudioSegment.from_file(file_path, format="mp3")
    elif file_extension == ".mp4":
        audio = AudioSegment.from_file(file_path, format="mp4")
    else:
        raise ValueError(f"不支持的文件格式: {file_extension}")
    audio.export("./.cache/Temp.wav", format="wav")
    print("成功转换为WAV格式音频")


if __name__ == "__main__":
    from main import main

    print("It seems you're not running main.py, but it's okay, we're calling main() now.")
    main()
