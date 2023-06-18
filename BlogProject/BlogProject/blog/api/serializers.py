from django.utils import timezone
from rest_framework import serializers

from ..models import Post, Comment


class CommentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Comment
        fields = ['name', 'email', 'body']

class CommentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('name', 'email', 'body')


class PostSerializer(serializers.HyperlinkedModelSerializer):
    author = serializers.SerializerMethodField('get_author')
    published = serializers.SerializerMethodField('get_published_time')
    comments = CommentSummarySerializer(many=True, read_only=True)
    created = serializers.DateTimeField(default=timezone.now)

    class Meta:
        model = Post
        fields = ('author', 'published', 'title', 'body', 'status', 'created', 'comments')

    def create(self, validated_data):
        post = Post.objects.create(**validated_data)
        return post

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.body = validated_data.get('body', instance.body)
        instance.status = validated_data.get('status', instance.status)
        instance.updated = timezone.now
        instance.save()
        return instance

    def get_author(self, post):
        return post.author

    def get_published_time(self, post):
        return post.publish
