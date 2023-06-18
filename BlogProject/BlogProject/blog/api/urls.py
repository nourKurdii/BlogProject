from django.template.defaulttags import url
from django.urls import path
from rest_framework import routers

from .views import CommentsList, CreateComment, CreatePost
from ..api import views

app_name = 'blog'

router = routers.DefaultRouter()
router.register(r'posts', views.PostViewSet)

urlpatterns = [
    path('<slug>', views.PostViewSet.post_details_api, name='details'),
    path('<slug>/edit', views.post_edit_api, name='post_edit'),
    path('create/', CreatePost.as_view(), name='create'),
    path('<slug:slug>/comments', CommentsList.as_view(), name='list_comments'),
    path('<slug:slug>/comments/create', CreateComment.as_view(), name='create_comment')

]
urlpatterns += router.urls
