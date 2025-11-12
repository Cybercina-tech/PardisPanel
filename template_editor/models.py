from django.db import models


class Template(models.Model):
    name = models.CharField(max_length=100)
    background = models.ImageField(upload_to="templates/backgrounds/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Template"
        verbose_name_plural = "Templates"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class Element(models.Model):
    class ElementType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"

    template = models.ForeignKey(
        Template,
        related_name="elements",
        on_delete=models.CASCADE,
    )
    type = models.CharField(
        max_length=16,
        choices=ElementType.choices,
    )
    content = models.TextField(blank=True, null=True)
    x = models.FloatField()
    y = models.FloatField()
    font_size = models.IntegerField(default=16)
    color = models.CharField(max_length=20, default="#000000")

    class Meta:
        verbose_name = "Element"
        verbose_name_plural = "Elements"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.get_type_display()} element on {self.template}"

