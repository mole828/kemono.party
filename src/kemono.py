
from enum import Enum
from functools import lru_cache
import json
import time
from typing import Callable, Iterable, List, Tuple
import requests
from bs4 import BeautifulSoup, PageElement, ResultSet, Tag
import pathlib

class Service(Enum):
    fanbox = 0
    fantia = 1
    patreon = 2

class Kemono:
    url = 'https://kemono.party'
    proxies = {}

    @lru_cache
    def creator(service: Service, id: str) -> dict :
        dir = pathlib.Path('./cache')
        if not dir.exists():dir.mkdir()
        path = pathlib.Path('./cache/creators.json')
        if not path.exists():
            with requests.get(f'{Kemono.url}/api/creators', proxies=Kemono.proxies) as response:
                buffer = response.content
                # contentLength = response.headers['Content-Length']
                creatorMap = json.loads(buffer)
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(json.dumps(creatorMap))
        with open(path,encoding='utf-8') as file:
            arr = json.loads(file.read())
            for creator in arr:
                if creator['service']==service.name and creator['id']==id:return creator


class Post:
    url: str
    service: Service
    uid: str 
    pid: str
    def __init__(self, url: str) -> None:
        self.url = url
        words = url.split('/')
        self.service = Service[words[3]]
        self.uid = words[5]
        self.pid = words[7]

    def __nameitermaker():
        i = 0
        while True:
            yield str(i)
            i+=1
    
    @property
    def cache_path(self) -> pathlib.Path:
        return pathlib.Path(f'./cache/{self.service.name}-{self.uid}-{self.pid}')
        

    @property
    def cached(self) -> bool:   
        return self.cache_path.exists()

    @property
    def __text(self) -> str:
        path = self.cache_path
        if not self.cached:
            begin = time.time()
            resp = requests.get(self.url,proxies=Kemono.proxies)
            end = time.time()
            print(f'reqjests.get({self.url}), spend: {end-begin}')
            with open(path,mode='w',encoding='utf-8') as file:
                file.write(resp.text)
        with open(path,encoding='utf-8') as file:
            return file.read()
        
    
    @property
    @lru_cache
    def __soup(self) -> BeautifulSoup:
        return BeautifulSoup(self.__text, features='html.parser')
    
    @property
    def title(self) -> str:
        return self.__soup.find(attrs={'class':'post__title'}).find_next('span').text

    @property
    def content(self) -> str:
        try:
            return self.__soup.find(attrs={'class':'post__content'}).text
        except AttributeError as e:
            return ""
            

    def download2dir(self, dir:pathlib.Path, nameitermaker: Callable[[],Iterable] = __nameitermaker) -> tuple[int,int]:
        '''
        just for manga 
        '''
        print(f'start: {dir.name}')
        if not dir.exists():dir.mkdir()
        contentpath = dir/'content.html'
        with open(contentpath, mode='w', encoding='utf-8') as file:
            try:
                file.write(self.content)
            except UnicodeEncodeError as e:
                raise e
        # TODO: get file name from <a ... download="{name}"></a>
        urls:List[str] = [file.a['href'] for file in self.__soup.find_all(attrs={'class': 'post__thumbnail'})]+[file.a['href'] for file in self.__soup.find_all(attrs={'class': 'post__attachment'})]
        urls = [f'{url}' for url in urls]
        downloads, skips = 0, 0
        nameiter = nameitermaker()
        for url in urls:
            lastname = url.split('.')[-1]
            firstname= next(nameiter)
            filename = f'{firstname}.{lastname}'
            filepath = dir/filename
            # download 
            if not filepath.exists():
                downloads += 1
                with requests.get(url,proxies=Kemono.proxies) as response:
                    buffer = response.content
                    contentLength = int(response.headers['Content-Length'])
                    if len(buffer) == contentLength:
                        with open(filepath, mode='wb') as file:
                            file.write(buffer)
                    else: 
                        print({'len(buffer)':len(buffer), 'contentLength':contentLength})
            else: 
                skips += 1
        print(f"end: {dir.name}, downloads: {downloads}, skips: {skips}")
        return downloads, skips


class Creator():
    service: Service
    id: str 
    name: str

    def __init__(self, url: str) -> None:
        words = url.split('/')
        self.service = Service[words[-3]]
        self.id = words[-1]
        self.name = Kemono.creator(self.service, self.id)['name']

    def page(self, p: int = 0) -> List[Tuple[str, str]]:
        '''
        :return List[Tuple[name, href]]
        '''
        url = f'{Kemono.url}/{self.service.name}/user/{self.id}?o={p*50}'
        resp = requests.get(url,proxies=Kemono.proxies)
        html = BeautifulSoup(resp.text, features='html.parser')
        article_htmls = html.find(
            attrs={'class': 'card-list__items'}
        ).find_all(
            attrs={'class': 'post-card'}
        )
        ans:List[Tuple[str, str]] = []
        article_html:Tag
        for article_html in article_htmls:
            name:str = article_html.find(name='header').string .replace('\n','')
            href:str = article_html.find(name='a').attrs['href']
            href = f'{Kemono.url}{href}'
            tup = (name, href)
            ans.append(tup)
        return ans
    
    @property
    def posts(self):
        '''
        A posts iter
        :return Generator[Tuple[name, href]]
        '''
        page = 0 
        while True:
            posts = self.page(page)
            for post in posts:
                yield post
            if len(posts)<50:break
            page+=1

    def download(self, root: pathlib.Path=pathlib.Path('./creators'), banner:Callable[[str],bool]=lambda name:False):
        if not root.exists():root.mkdir()
        creatorDir = root/self.name
        if not creatorDir.exists():creatorDir.mkdir()
        for posttup in self.posts:
            [name, url] = posttup
            post = Post(url)
            cached = post.cached
            name = post.title
            def f(s:str):
                if s[0]==' ':return f(s[1:])
                if s[-1]==' ':return f(s[:-1])
                return s
            name = f(name)
            for s in ['<', '>', '/', '\\', '|', ':', '*', '?', '"']:name = name.replace(s,'-')
            while name.endswith('.'):name.replace('.','-')
            postDir = creatorDir / name
            if not postDir.exists():postDir.mkdir()
            
            if banner(name):
                print('skip: ',name)
                continue
            downloads, skips = post.download2dir(postDir)
            sleep_time = 5 if downloads!=0 else 0 if cached else 1
            print(f'sleep {sleep_time} sec')
            time.sleep(
                sleep_time
            )


if __name__ == '__main__':
    from urllib.parse import unquote
    encoded_url = "%E3%83%96%E3%83%AC%E3%83%9E%E3%83%BC%E3%83%88%E3%83%B3%E3%82%BB%E3%83%AB%E3%83%95%E3%83%95%E3%82%A7%E3%83%A9T.mp4"
    decoded_url = unquote(encoded_url)
    print(decoded_url)