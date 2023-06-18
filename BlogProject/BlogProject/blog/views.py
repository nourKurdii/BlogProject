import datetime
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from rest_framework.exceptions import PermissionDenied
from .models import Post, Comment, Warnings, Like, AccessedPosts, Profile, SubscriptionsModel
from .forms import commentForm, registerForm, postEditForm, createPostForm, generatePost
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
from .notifications import pusher_client
from .utils import chat_bot, max_post_per, user_is_blocked

BLOCK_DURATION = 10
MAX_POSTS_ALLOWED_TO_READ = 3


@login_required
def list_posts(request):
    user_warnings, created = Warnings.objects.get_or_create(user=request.user)
    if user_warnings.new_warning:
        messages.warning(request, 'You Got a new warning')
        user_warnings.new_warning = False
        user_warnings.save()

    AccessedPosts.objects.filter(created_at__lt=datetime.date.today()).delete()
    posts_list = Post.published.all()
    p = Paginator(posts_list, 3)
    page_number = request.GET.get('page')
    posts = p.get_page(page_number)

    # loop to find all channels that request.user is subscribing
    subscriptions = SubscriptionsModel.objects.filter(Subscriber=request.user)
    channels = []
    for subscription in subscriptions:
        channel_name = f"{subscription.Subscription.username}"
        channels.append(channel_name)
    # channels = json.dumps([channel_name, ])
    return render(request, 'blog/postsList.html', {'posts': posts, 'channels': channels})


@login_required
def post_details(request, slug):
    post = get_object_or_404(Post, slug=slug)
    comments = Comment.objects.filter(post=post)

    user_accessed_posts = AccessedPosts.objects.filter(user=request.user)
    count = user_accessed_posts.filter(created_at__gte=datetime.date.today()).count()

    if not AccessedPosts.objects.filter(user=request.user, post=post).exists():
        if count == MAX_POSTS_ALLOWED_TO_READ:
            raise PermissionDenied("You have exceeded the maximum number for reading.")
        else:
            AccessedPosts.objects.create(user=request.user, post=post)

    # to get each post number of view
    # views = AccessedPosts.objects.filter(post=post).count()

    likes = post.likes
    dislikes = post.dislikes
    liked = False
    disliked = False
    summarized = False
    body = post.body

    if Like.objects.filter(post=post, user=request.user, type=0).exists():
        liked = True
    if Like.objects.filter(post=post, user=request.user, type=1).exists():
        disliked = True

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        comment_form = commentForm(request.POST, user=request.user)

        # check whether it's valid:
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            if request.user.is_authenticated:
                comment.name = request.user.username
                comment.email = request.user.email
            comment.save()

        else:
            messages.error(request, 'Something went wrong please try again')
        # if a GET (or any other method) we'll create a blank form

    elif request.method == 'GET':
        if request.GET.get('summarized') == 'True':
            prompt = f"summarize this article:\n {post.body}"
            chat_response = chat_bot(prompt, max_tokens=500)
            body = chat_response
            summarized = True

        comment_form = commentForm(user=request.user)

    context = {'body': body, 'post': post, 'comments': comments, 'form': comment_form, 'likes': likes,
               'dislikes': dislikes, 'liked': liked, 'disliked': disliked, 'summarized': summarized}

    return render(request, 'blog/postDetails.html', context)


def home(request):
    logout(request)
    return render(request, 'blog/main.html')


def sign_up(request):
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = registerForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "'Account created successfully")
            return redirect("blog:list")
        messages.error(request, "Unsuccessful registration. Invalid information.")
    form = registerForm()

    return render(request, 'blog/signUp.html', {'form': form})


def log_in(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user=user)
                messages.info(request, "")
                return redirect("blog:list")
            else:
                messages.error(request, "Invalid username or Password")
        else:
            messages.error(request, "Invalid username or registration")
    form = AuthenticationForm()
    return render(request, 'blog/login.html', {"form": form})


def log_out(request):
    logout(request)
    messages.info(request, "You've successfully logged out.")
    return redirect("blog:home")


@login_required
def edit_post(request, slug):
    if user_is_blocked(user=request.user):
        return render(request, 'blog/validationError.html')

    else:
        post = get_object_or_404(Post, slug=slug)
        # initial request to view the form
        if request.method == 'GET':
            form = postEditForm(instance=post)
            return render(request, 'blog/postEdit.html', {'form': form})
        # request to submit the form
        elif request.method == 'POST':
            # the instance argument tells django to pre-populate the form
            # with the existing post object
            form = postEditForm(request.POST, instance=post)
            if form.is_valid():
                # commit false to make the object with the data retrieved from form and
                # allow editing any other fields
                post = form.save(commit=False)
                post.updated = timezone.now
                post.save()
                messages.success(request, 'The post has been updated successfully')
                return redirect("blog:list")
            else:
                messages.error(request, 'Something went wrong please try again')
                return render(request, 'blog/postEdit.html', {'form': form})


@login_required
@user_passes_test(max_post_per)
def create_post(request):
    notify = False

    if user_is_blocked(user=request.user):
        return render(request, 'blog/validationError.html')

    else:

        form = createPostForm(request.POST)
        if form.is_valid():

            obj = form.save(commit=False)
            obj.created = timezone.now()
            obj.author = request.user
            obj.save()

            # if the post is published notify the subscribers
            if obj.status == 1:
                notify = True
            messages.success(request, 'New post created successfully')

            if notify:
                channel_name = f"{request.user}"
                pusher_client.trigger(channel_name, 'new-post', {'message': f'{channel_name} added a New Post '})

            return redirect("blog:list")
        else:
            return render(request, 'blog/postCreate.html', {'form': form})


def like_post(request, slug):
    post = get_object_or_404(Post, slug=slug)

    if 'like' in request.POST:
        like_object = Like.objects.filter(post=post, user=request.user, type=0)
        if like_object.exists():
            like_object.delete()

        else:
            Like.objects.create(post=post, user=request.user, type=0)

    elif 'dislike' in request.POST:
        dislike_object = Like.objects.filter(post=post, user=request.user, type=1)
        if dislike_object.exists():
            dislike_object.delete()
        else:
            Like.objects.create(post=post, user=request.user, type=1)

    return HttpResponseRedirect(reverse('blog:details', args=[slug]))


def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user)
    posts = profile.get_user_posts().count()
    subscriptions = profile.get_user_subscriptions().count()
    subscribers = profile.get_user_subscribers().count()
    followed = False
    if SubscriptionsModel.objects.filter(Subscriber=request.user, Subscription=user).exists():
        followed = True
    context = {
        'posts': posts,
        'user': profile.user,
        'username': profile.user.username,
        'email': profile.user.email,
        'Subscriptions': subscriptions,
        'Subscribers': subscribers,
        'followed': followed
    }
    return render(request, 'blog/profile.html', context)


def subscribe(request, subscription):
    user = get_object_or_404(User, username=subscription)
    if SubscriptionsModel.objects.filter(Subscriber=request.user, Subscription=user).exists():
        SubscriptionsModel.objects.filter(Subscriber=request.user, Subscription=user).delete()

    else:
        SubscriptionsModel.objects.create(Subscriber=request.user, Subscription=user)
        # beam_client.subscribe_user_to_interest()
    return HttpResponseRedirect(reverse('blog:profile', args=[subscription]))


def generate_post(request):
    if request.method == 'POST':

        form = generatePost(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            prompt = f"write an article about:\n {subject}"
            chat_response = chat_bot(prompt, max_tokens=100)
            post = Post.objects.create(body=chat_response, author=request.user, status=1, title=subject)

            return redirect("blog:list")

        else:
            messages.error(request, 'Something wend wrong please try again')
            return render(request, 'blog/generatedPost.html', {'form': form})
    else:
        form = generatePost()
        return render(request, 'blog/generatedPost.html', {'form': form})


def fix_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    body = post.body
    prompt = f"fix this articles grammar:\n{body}"
    chat_response = chat_bot(prompt, 500)
    post.body = chat_response
    post.save()
    return HttpResponseRedirect(reverse('blog:details', args=[slug]))
