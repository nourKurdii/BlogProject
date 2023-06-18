import httpx
from django.core import serializers

post_name = None
data = {"key": "val"}


class Client:
    def __init__(self):
        self.headers = {
            'Authorization': 'Token 8dc24db8831db7f985d14caf503899b0c58a5c3e'
        }
        # create httpx sync client instance and pass the proper headers to it
        self.httpx_client = httpx.Client(headers=self.headers)

    def list_posts(self):
        try:
            response = self.httpx_client.get(
                url="http://127.0.0.1:8000/api/blog/posts/",
            )
            if response.status_code == 200:
                deserialized_data = serializers.deserialize("json", response.text)
                global post_name
                post_name = deserialized_data[0]['title']

                for post in deserialized_data:
                    print(post.object)
            else:
                print("error getting posts")

        except httpx.HTTPError as exc:
            print(str(exc))
            self.httpx_client.close()

    def create_post(self):
        try:
            response = self.httpx_client.post(
                url="http://127.0.0.1:8000/api/blog/create/",
                data={
                    "title": "Post",
                    "body": "",
                    "status": 1
                })
            return response.text

        except httpx.HTTPError as exc:
            print(str(exc))
            self.httpx_client.close()

    def create_comment(self):
        try:
            response = self.httpx_client.post(
                url="http://127.0.0.1:8000/api/blog/create/",
                data={
                    "name": "Commenter",
                    "email": "commenter@gmail.com",
                    "body": "Comment"
                })
            return response.text

        except httpx.HTTPError as exc:
            print(str(exc))
            self.httpx_client.close()

    def list_comments(self):
        try:
            response = self.httpx_client.get(
                url=f"http://127.0.0.1:8000/api/blog/{post_name}/comments",
            )
            if response.status_code == 200:
                deserialized_data = serializers.deserialize("json", response.text)
                for comment in deserialized_data:
                    print(comment.object)
            else:
                print("error getting comments")
            return response.text

        except httpx.HTTPError as exc:
            print(str(exc))
            self.httpx_client.close()

    def update_post(self):
        try:
            response = self.httpx_client.put(
                url=f"http://127.0.0.1:8000/api/blog/{post_name}/edit",
                data=
                {
                    "title": "Post",
                    "body": "",
                    "status": 1
                },

            )
            return response.text

        except httpx.HTTPError as exc:
            error = (str(exc))
            print(error)
            self.httpx_client.close()
