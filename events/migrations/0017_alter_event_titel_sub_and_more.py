# Generated by Django 5.0.6 on 2024-08-06 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0016_alter_participant_options_event_titel_sub_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='titel_sub',
            field=models.CharField(max_length=100, verbose_name='Title Subscript'),
        ),
        migrations.AlterField(
            model_name='historicalevent',
            name='titel_sub',
            field=models.CharField(max_length=100, verbose_name='Title Subscript'),
        ),
    ]
