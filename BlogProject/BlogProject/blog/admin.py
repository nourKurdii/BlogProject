from django.contrib import admin
from .models import Post, Comment, Warnings, AccessedPosts, Like, Profile, SubscriptionsModel

# Register your models here.
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Warnings)
admin.site.register(AccessedPosts)
admin.site.register(Like)
admin.site.register(Profile)
admin.site.register(SubscriptionsModel)
