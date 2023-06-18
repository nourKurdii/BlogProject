from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import api_view, permission_classes

from ..api.serializers import PostSerializer, CommentSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS, AllowAny

from ..models import Post, Comment
from better_profanity import profanity


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Instance must have an attribute named `owner`.
        return obj.author == request.user


class PostViewSet(viewsets.ModelViewSet):
    # view all posts
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated | ReadOnly]

    @api_view(('GET',))
    def post_details_api(self, slug):
        # get specific post
        post = get_object_or_404(Post, slug=slug)

        serializer = PostSerializer(post)
        return Response(serializer.data)


class CreatePost(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def perform_create(self, serializer):

        author = self.request.user
        serializer.save(author=author)

    def create_post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(('PATCH', 'PUT'))
@permission_classes((IsAuthenticated, IsOwnerOrReadOnly))
def post_edit_api(request, slug):
    # update existing post
    post = get_object_or_404(Post, slug=slug)

    serializer = PostSerializer(post, data=request.data, partial=True)

    data = {}
    if serializer.is_valid():
        if serializer.validated_data.get('status') == 1 and not post.publish:
            serializer.validated_data['publish'] = timezone.now()
        serializer.save()
        data['success'] = "updated successfully"
        return Response(data=data)
    return Response(serializer.errors)


class CommentsList(generics.ListAPIView):
    permission_classes = (AllowAny,)
    # view specific post comments
    serializer_class = CommentSerializer

    def get_queryset(self):
        post = Post.objects.get(slug=self.kwargs['slug'])
        return Comment.objects.filter(post=post)


class CreateComment(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    # add comment for specific post
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    # hook for setting attributes that are implicit in the request,
    # but are not part of the request data
    def perform_create(self, serializer):
        post = Post.objects.get(slug=self.kwargs['slug'])
        serializer.save(post=post, created_time=timezone.now())

    def create_comment(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
