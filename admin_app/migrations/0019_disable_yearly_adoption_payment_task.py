from django.db import migrations

YEARLY_PAYMENT_TASK = "admin_app.tasks.add_yearly_adoption_parent_payments"


def disable_yearly_payment_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task=YEARLY_PAYMENT_TASK).update(enabled=False)


class Migration(migrations.Migration):

    dependencies = [
        ("admin_app", "0018_sponsor_letters_childtrait"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(disable_yearly_payment_task, migrations.RunPython.noop),
    ]
