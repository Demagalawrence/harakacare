from django.contrib import admin
from .models import Conversation, Message

# Register your models here.
admin.site.register(Conversation)
admin.site.register(Message)