# kemono.party downloader

## example 
```python
from src.kemono import Kemono,Creator

# Kemono.proxies = { "http": "http://localhost:7890/", "https": "http://localhost:7890/", }

if __name__ == '__main__':
    a = Creator('https://kemono.party/xxx/user/xxx')
    print(a.service,a.name,'begin')
    a.download()
```