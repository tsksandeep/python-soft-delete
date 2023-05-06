from django.db import models
from django.apps.registry import Apps
from django.core.exceptions import ImproperlyConfigured


def check_model_object_manager(django_apps: Apps, ignore_models: list) -> None:
    """
    Check if any Django model object has a foreign key field to a model with soft deletion
    but it still uses the default manager.

    :param django_apps: List of Django apps
    :param ignore_models: List of models to ignore

    :rtype: None
    :raises ImproperlyConfigured: If a model uses the default manager with a
            SoftDeletionModel foreign key field
    """

    app_configs = django_apps.get_app_configs()

    for app_config in app_configs:
        if not app_config.name.startswith("app."):
            continue

        for model in app_config.get_models():
            if not issubclass(model, models.Model) or model in ignore_models:
                continue

            has_soft_delete = any(
                isinstance(field, models.ForeignKey)
                and issubclass(field.remote_field.model, SoftDeletionModel)
                for field in model._meta.fields
            )

            if has_soft_delete and type(model.objects) == models.Manager:
                raise ImproperlyConfigured(
                    f"{model.__name__} has a foreign key field to a model with soft deletion"
                    " but it still uses the default manager. Please override the default manager"
                    " with custom manager that filters out objects based on the foreign key field."
                )


class SoftDeletionManager(models.Manager):
    """
    Manager that filters out objects that have been soft deleted.
    """

    def get_queryset(self):
        """
        Return queryset that filters out objects that have been soft deleted.
        """
        return super().get_queryset().filter(deleted_at=None)

    def soft_delete(self, *args, **kwargs):
        """
        Soft delete objects that match the given query.
        """
        return (
            super()
            .get_queryset()
            .filter(*args, **kwargs)
            .update(deleted_at=models.functions.Now())
        )


class SoftDeletionModel(models.Model):
    """
    Abstract model that adds a deleted_at field and a custom manager that filters out
    """

    deleted_at = models.DateTimeField(null=True, default=None)
    objects = SoftDeletionManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


# ------------------------------------------------------------------------------
#                                   Models.py
# ------------------------------------------------------------------------------
from django.apps import apps
from django.dispatch import receiver


@receiver(models.signals.post_migrate)
def check_models(sender, **kwargs):
    ignore_models = []
    check_model_object_manager(apps, ignore_models)


class DeletedFilterManager(models.Manager):
    """Manager used to filter out objects based on soft deleted foreign key"""

    def __init__(self, query_param=None, **kwargs):
        super().__init__(**kwargs)
        self.query_param = query_param

    def get_queryset(self):
        """
        Return queryset that filters out objects based on soft deleted foreign key
        """

        kwargs = {}
        if self.query_param:
            kwargs[self.query_param] = None

        return super().get_queryset().filter(**kwargs)


class SampleModel(SoftDeletionModel):
    """Model class representing a sample model"""

    id = models.AutoField(primary_key=True)
    unique_name = models.CharField(max_length=128)
    display_name = models.CharField(max_length=128, blank=True)


# If the model has foreign key to a model with soft deletion, use the custom DeletedFilterManager
class SampleModelWithForeignKey(models.Model):
    """Table storing instances of unique vehicle software configurations"""

    id = models.AutoField(primary_key=True)
    sample = models.ForeignKey(SampleModel, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=128, blank=True)

    objects = DeletedFilterManager("sample__deleted_at")
    all_objects = models.Manager()
