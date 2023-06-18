from datetime import date
from django.core.exceptions import PermissionDenied
from django.db import models, IntegrityError
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from better_profanity import profanity
import uuid
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_delete
import random

# in seconds
SUBMIT_DELAY = 300
# in days
BLOCK_DURATION = 10


# custom manager to retrieve published books
class PublishedPostsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=1)


# posts model
class Post(models.Model):
    objects = models.Manager()  # The default manager.
    # Manager to retrieve the published posts
    published = PublishedPostsManager()
    # The first element in each tuple is the actual value to be set on the model,
    # and the second element is the human-readable name.
    status_choices = [(0, 'Draft'), (1, 'Published')]
    status = models.IntegerField(choices=status_choices, default='draft')

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, default=uuid.uuid1, unique=True)
    # foreign key
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created = models.DateTimeField(default=timezone.now)
    publish = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    likes = models.IntegerField(default=0)
    dislikes = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        # if the post is updated from draft to publish
        if self.status == 1 and not self.publish:
            self.publish = timezone.now()

        self.slug = slugify(self.title)
        words = ''.join(self.title).split()
        words += ''.join(self.body).split()

        self.title = profanity.censor(self.title)
        self.body = profanity.censor(self.body)

        user_warnings, created = Warnings.objects.get_or_create(user=self.author)
        for word in words:
            if profanity.contains_profanity(word):
                user_warnings.bad_words_count += 1

        # if somehow blocked user tries to save post
        block_diff = date.today() - user_warnings.blocked_date
        if block_diff.days < BLOCK_DURATION:
            raise PermissionDenied("You are blocked")

        else:
            try:
                # responsible for saving the object to the database
                super(Post, self).save(*args, **kwargs)
                # save changes only if post saved
                user_warnings.save()

            # if new post name exists
            except IntegrityError:
                random_num = random.randint(1, 9999)
                self.slug = f'{self.slug}-{random_num}'
                super(Post, self).save(*args, **kwargs)
                user_warnings.save()

    def __str__(self):
        return self.title


# Comment model
class Comment(models.Model):
    objects = models.Manager()  # The default manager.
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254)
    body = models.TextField()
    created_time = models.DateTimeField(default=timezone.now)
    updated_time = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=False)
    can_comment = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.can_comment:
            # responsible for saving the object to the database
            self.body = profanity.censor(self.body)

            super(Comment, self).save(*args, **kwargs)
        else:
            raise Exception("You've already Submitted a comment")


# Warning model
class Warnings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bad_words_count = models.IntegerField(default=0)
    warnings_count = models.IntegerField(default=0)
    blocked_date = models.DateField(auto_now=False, default=date(1000, 1, 1))
    new_warning = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.bad_words_count > 3:
            self.warnings_count += 1
            self.new_warning = True
            self.bad_words_count = 0

            if self.warnings_count % 3 == 0:
                self.blocked_date = date.today()
        super(Warnings, self).save(*args, **kwargs)


class Like(models.Model):
    like_choices = [(0, 'Like'), (1, 'Dislike')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    type = models.IntegerField(choices=like_choices, default='Dislike')

    class Meta:
        unique_together = ("user", "post")

    def save(self, *args, **kwargs):
        if self.type == 0:
            self.post.likes += 1
        elif self.type == 1:
            self.post.dislikes += 1
        self.post.save()
        super(Like, self).save(*args, **kwargs)


class AccessedPosts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="accessed_post")


class SubscriptionsModel(models.Model):
    Subscription = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
    Subscriber = models.ForeignKey(User, on_delete=models.CASCADE, related_name="follower")

    def save(self, *args, **kwargs):
        profile1, created = Profile.objects.get_or_create(user=self.Subscriber)
        profile1.Subscriptions += 1
        profile2, created = Profile.objects.get_or_create(user=self.Subscription)
        profile2.Subscribers += 1
        profile1.save()
        profile2.save()
        super(SubscriptionsModel, self).save(*args, **kwargs)


class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    Subscriptions = models.IntegerField(default=0)
    Subscribers = models.IntegerField(default=0)

    def get_user_posts(self):
        return Post.objects.filter(author=self.user)

    def get_user_subscriptions(self):
        return SubscriptionsModel.objects.filter(Subscriber=self.user)

    def get_user_subscribers(self):
        return SubscriptionsModel.objects.filter(Subscription=self.user)


@receiver(signal=pre_save, sender=Comment)
def can_comment_now(sender, instance, **kwargs):
    last_comment = Comment.objects.filter(post=instance.post, email=instance.email).order_by('created_time').last()

    if last_comment is None:
        instance.can_comment = True
    else:
        time_diff = timezone.now() - last_comment.created_time
        if time_diff.total_seconds() < SUBMIT_DELAY:
            instance.can_comment = False
            instance.save()


@receiver(signal=post_delete, sender=Like)
def delete_like_object(sender, instance, **kwargs):
    if instance.type == 0:
        instance.post.likes -= 1
    elif instance.type == 1:
        instance.post.dislikes -= 1
    instance.post.save()


@receiver(signal=post_delete, sender=SubscriptionsModel)
def delete_subscriptions_object(sender, instance, **kwargs):
    profile1 = Profile.objects.get(user=instance.Subscriber)
    profile1.Subscriptions -= 1
    profile2 = Profile.objects.get(user=instance.Subscription)
    profile2.Subscribers -= 1
    profile1.save()
    profile2.save()


pre_save.connect(can_comment_now, sender=Comment)
post_delete.connect(delete_like_object, sender=Like)
