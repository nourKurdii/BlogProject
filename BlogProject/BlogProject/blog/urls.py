from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token

app_name = 'blog'


urlpatterns = [
    path('', views.home, name='home'),
    path('login', views.log_in, name='login'),
    path('signUp', views.sign_up, name='signup'),
    path('listPosts', views.list_posts, name='list'),
    path('createPost', views.create_post, name='create'),
    path('generatePost', views.generate_post, name='generate'),
    path('logout', views.log_out, name='logout'),
    path('<slug:slug>', views.post_details, name='details'),
    path('<slug:slug>/like', views.like_post, name='like_post'),
    path('<slug:slug>/edit', views.edit_post, name='post_edit'),
    path('<slug:slug>/fix', views.fix_post, name='post_fix'),
    path('profile/<username>', views.user_profile, name='profile'),
    path('profile/<subscription>/subscribe', views.subscribe, name='subscribe'),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
]

