from django.db import models
from django.contrib.auth.models import User
from awesome_avatar.fields import AvatarField
from category import sex_category
class Profile(models.Model):
    user = models.OneToOneField(User, related_name = "profile")
    sex = models.IntegerField(choices = sex_category, default = 0)
    avatar = AvatarField(upload_to = 'avatars', width = 100, height = 100)


