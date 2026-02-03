from django.db import models

# Create your models here.



class Facility(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
