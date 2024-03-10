import httpx
from datetime import datetime
from dataclasses import dataclass
from typing import Any
from collections import Counter
import sys
import config


@dataclass
class Post:
    id: str
    author: str
    created_utc: datetime

@dataclass
class Comment:
    id: str
    author: str
    created_utc: datetime


class Authentication:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.body = {'grant_type': 'client_credentials'}
        self.auth_url = "https://www.reddit.com/api/v1/access_token"

    def get_token(self) -> str | None:
        token = None
        auth = httpx.BasicAuth(username=self.client_id, password=self.client_secret)
        data = self.body
        auth_url = self.auth_url
        with httpx.Client() as client:
            try:
                response = client.post(auth_url, auth=auth, data=data)
                response.raise_for_status()
                token = response.json().get('access_token')    
            except httpx.RequestError as exc:
                print(f"Произошла ошибка при запросе {exc.request.url!r}.")
            except httpx.HTTPStatusError as exc:
                print(f"Ошибочный код запроса {exc.response.status_code} при выполнении запроса {exc.request.url!r}.")
            except Exception as exc:
                print(f"Неожиданное исключение: {type(exc).__name__}, {exc}")
        return token
        
class Parsing:
    def __init__(self, subreddit: str, token: str) -> None:
        self.subreddit = subreddit
        self.bearer_token = f'Bearer {token}'
    
    def __get_subreddit_content(self, parse_url)-> dict:
        content = None
        headers = {'Authorization': self.bearer_token}
        with httpx.Client() as client:
            try:
                content = client.get(parse_url, headers=headers)
                content.raise_for_status()
                if not content:
                    raise ValueError("Ответ не содержит необходимых данных.")
                return content.json()
            except httpx.RequestError as exc:
                print(f"Произошла ошибка при запросе {exc.request.url!r}.")
                return {}
            except httpx.HTTPStatusError as exc:
                print(f"Ошибочный код запроса {exc.response.status_code} при выполнении запроса {exc.request.url!r}.")
                return {}
            except Exception as exc:
                print(f"Неожиданное исключение: {type(exc).__name__}, {exc}")
                return {}
    
    def get_posts(self) -> list[Post]:
        parse_url = f'https://oauth.reddit.com/r/{self.subreddit}/new'
        content = self.__get_subreddit_content(parse_url)
        posts: list[Post] = []
        for item in content['data']['children']:
            #TODO Проверять кол-во дней (3 дня)
            date = datetime.fromtimestamp(item['data']['created_utc'])
            post = Post(id=item['data']['id'] ,author=item['data']['author'], created_utc=date)
            posts.append(post)
        print(f'Найдено {len(posts)} постов.')
        return posts
    
    def get_comments(self, posts: list[Post]) -> list[Comment]:
        comments: list[Comment] = []
        
        #Рекурсивно вытаскивает все ответы на комментарии за один запрос к посту
        def comments_tree(item: dict[str, Any]) -> None:
            comment = Comment(id=item['data']['id'],
                            author=item['data']['author'],
                            created_utc=datetime.fromtimestamp(item['data']['created_utc']))
            comments.append(comment)
            if 'replies' in item['data'] and item['data']['replies']:
                for item in item['data']['replies']['data']['children']:
                    comments_tree(item)

        for post in posts:
            parse_url = f'https://oauth.reddit.com/r/{self.subreddit}/comments/{post.id}'
            content = self.__get_subreddit_content(parse_url)
            if content[1]['data']['children']:
                for item in content[1]['data']['children']:
                    comments_tree(item)
        return comments

class Analyze:
    def __init__ (self, posts: list[Post], comments: list[Comment]):
        self.posts = posts
        self.comments = comments

    def get_author_rank(self):
        top_post_authors = Counter([post.author for post in self.posts])
        top_comments_authors = Counter([comment.author for comment in self.comments])
        return top_post_authors, top_comments_authors



def main():
    token = Authentication(config.client_id, config.client_secret).get_token()
    if not token:
        print('Не удалось получить токен')
        sys.exit(1)
    try:
        posts = Parsing('bikecommuting', token).get_posts()
        comments = Parsing('bikecommuting', token).get_comments(posts)
        result = Analyze(posts, comments).get_author_rank()
        print(f'Топ авторов постов: \n {result[0]}')
        print(f'Топ авторов комментариев: \n {result[1]}')
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()