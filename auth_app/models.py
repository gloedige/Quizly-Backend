from django.db import models

class AccessTokenStorage(models.Model):
    """Model to store access tokens in a custom storage mechanism."""
    access_token = models.TextField()
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = "Access Token Storage"
        verbose_name_plural = "Access Token Storages"

    def __str__(self):
        return f"AccessTokenStorage(id={self.id}, expires_at={self.expires_at})"
