from dotenv import load_dotenv
from .models import Post, Warnings
from rest_framework.exceptions import PermissionDenied
from datetime import date
import openai
import os
import datetime

load_dotenv()
api_key = os.getenv("OPENAI_KEY", None)
MAX_POSTS_ALLOWED_TO_POST = 4
MAX_POSTS_ALLOWED_TO_READ = 3
BLOCK_DURATION = 10


def chat_bot(prompt, max_tokens):
    chat_response = None
    if api_key is not None:
        openai.api_key = api_key
        try:
            response = openai.Completion.create(
                model='text-davinci-003',
                prompt=prompt,
                temperature=0.5,
                stop=None,
                max_tokens=max_tokens
            )
            chat_response = response['choices'][0]['text']
        except Exception as e:
            print(e)

    return chat_response


def max_post_per(user):
    user_created_posts = Post.objects.filter(author=user)
    count = user_created_posts.filter(created__gte=datetime.date.today()).count()
    print(count)
    if count > MAX_POSTS_ALLOWED_TO_POST:
        raise PermissionDenied("You have exceeded the maximum number for posting.")

    return True


def user_is_blocked(user):
    user_warnings, created = Warnings.objects.get_or_create(user=user)

    # check block period if still didn't end
    block_diff = date.today() - user_warnings.blocked_date
    if block_diff.days < BLOCK_DURATION:
        return True
    return False

