# Generated by Django 5.0.6 on 2024-07-16 09:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0006_remove_event_location_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participant',
            name='payment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to='events.payment', verbose_name='Payment'),
        ),
    ]
