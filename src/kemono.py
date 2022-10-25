
from enum import Enum
from functools import lru_cache
import json
import time
from typing import Callable, Iterable, List, Tuple
import requests
from bs4 import BeautifulSoup, PageElement, ResultSet, Tag
import pathlib

class Kemono:
    url = 'https://kemono.party'

    @lru_cache
    def creator(id: str) -> dict :
        dir = pathlib.Path('./cache')
        if not dir.exists():dir.mkdir()
        paths = [f for f in dir.iterdir()]
        if len(paths) == 0:
            with requests.get(f'{Kemono.url}/api/creators') as response:
                buffer = response.content
                # contentLength = response.headers['Content-Length']
                creatorMap = json.loads(buffer)
                filepath = dir/f'{len(buffer)}.json'
                if not filepath.exists():
                    with open(filepath, 'w') as file:
                        file.write(json.dumps(creatorMap))
                paths.append(filepath)
        path = paths[-1]
        with open(path) as file:
            arr = json.loads(file.read())
            for creator in arr:
                if creator['id']==id:return creator

class ArtistType(Enum):
    fanbox = 0
    fantia = 1


class Post:
    url: str
    def __init__(self, url: str) -> None:
        self.url = url
    
    def __names():
        i = 0
        while True:
            yield str(i)
            i+=1

    def download(self, dir:pathlib.Path, nameitermaker: Callable[[],Iterable] = __names):
        '''
        just for manga 
        '''
        nameiter = nameitermaker()
        if not dir.exists():dir.mkdir()
        resp = requests.get(self.url)
        html = BeautifulSoup(resp.text, features='html.parser')
        contentpath = dir/'content.html'
        with open(contentpath, mode='w') as file:
            file.write(html.find(attrs={'class':'post__content'}).text)
        files = html.find_all(attrs={'class': 'post__thumbnail'})
        urls:List[str] = [file.a['href'] for file in files]
        urls = [f'{Kemono.url}{url}' for url in urls]
        for url in urls:
            lastname = url.split('.')[-1]
            firstname= next(nameiter)
            filename = f'{firstname}.{lastname}'
            filepath = dir/filename
            # download 
            if not filepath.exists():
                with requests.get(url) as response:
                    buffer = response.content
                    contentLength = int(response.headers['Content-Length'])
                    if len(buffer) == contentLength:
                        with open(filepath, mode='wb') as file:
                            file.write(buffer)
                    else: 
                        print({'len(buffer)':len(buffer), 'contentLength':contentLength})


class Creator():
    type: ArtistType
    id: str 
    name: str

    def __init__(self, url: str) -> None:
        words = url.split('/')
        self.type = ArtistType[words[-3]]
        self.id = words[-1]
        self.name = Kemono.creator(self.id)['name']

    def page(self, p: int = 0) -> List[Tuple[str, str]]:
        '''
        :return List[Tuple[name, href]]
        '''
        url = f'{Kemono.url}/{self.type.name}/user/{self.id}?o={p*50}'
        resp = requests.get(url)
        html = BeautifulSoup(resp.text, features='html.parser')
        article_htmls = html.find(
            attrs={'class': 'card-list__items'}
        ).find_all(
            attrs={'class': 'post-card'}
        )
        ans:List[Tuple[str, str]] = []
        article_html:Tag
        for article_html in article_htmls:
            name:str = article_html.find(name='header').string.replace(' ', '').replace('\n','')
            href:str = article_html.find(name='a').attrs['href']
            href = f'{Kemono.url}{href}'
            tup = (name, href)
            ans.append(tup)
        return ans
    
    def postiter(self):
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
        for posttup in self.postiter():
            [name, url] = posttup
            for tup in [(':','-')]:name = name.replace(tup[0],tup[1])
            postDir = creatorDir / name
            if not postDir.exists():postDir.mkdir()
            post = Post(url)
            if banner(name):
                print('skip: ',name)
                continue
            print('start: ', name)
            post.download(postDir)
            time.sleep(5)

if __name__ == '__main__':
    print(__file__)
    a= Creator('https://kemono.party/fantia/user/26476')
    a.download()
    