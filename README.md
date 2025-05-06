# U校园AI版，调用硅基流动的api自动答题
从VonEquinox的版本进行了一些修改，主要是把reloading去掉了，避免编码切换的麻烦。
# 安装教程
在硅基流动自行注册账号，可以在tool里修改自己想要的模型，默认调用Qwen QwQ 32B
然后运行命令
```bash
pip install -r ./requirements.txt\
```
接着配置ffmpeg和cuda（可选），不配置cuda会调用cpu，速度相对较慢。
