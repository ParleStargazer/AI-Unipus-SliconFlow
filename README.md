# Fuck-AI-Unipus
No script for the AI Unipus? Let's fuck it together!\
The script is used for the FUCKING AI Unipus (Some question types are not yet supported.)\
**SO AI Unipus FUCK YOU**

## Usage Instructions
First, install the required dependencies.
```bash
pip install -r ./requirements.txt
```

Complete the `secret.py.example` file with your Unipus account and password for `username` and `password`, and your [DeepSeek API key](https://platform.deepseek.com/api_keys) for `api_key`.\
Then copy or rename the file to `secret.py`.
```bash
python -u ./main.py
```

## Notice
Known Issue: `reloading` does not work properly in non-UTF-8 environments. To resolve this, you need to remove all `@reloading` statements. Additionally, `whisper` requires `ffmpeg` to be present in the environment variables. If it is missing, an error will occur. Please make sure to configure the environment properly.