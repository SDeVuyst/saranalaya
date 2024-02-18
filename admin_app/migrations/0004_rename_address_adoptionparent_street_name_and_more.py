# Generated by Django 5.0.2 on 2024-02-18 03:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0003_alter_adoptionparent_children'),
    ]

    operations = [
        migrations.RenameField(
            model_name='adoptionparent',
            old_name='address',
            new_name='street_name',
        ),
        migrations.RenameField(
            model_name='sponsor',
            old_name='address',
            new_name='street_name',
        ),
        migrations.AddField(
            model_name='adoptionparent',
            name='address_number',
            field=models.IntegerField(default=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='adoptionparent',
            name='bus',
            field=models.IntegerField(blank=True, default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='adoptionparent',
            name='city',
            field=models.CharField(default='Bruges', max_length=40),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='adoptionparent',
            name='country',
            field=models.CharField(default='Belgium', max_length=40),
        ),
        migrations.AddField(
            model_name='adoptionparent',
            name='postcode',
            field=models.IntegerField(default=8210),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sponsor',
            name='address_number',
            field=models.IntegerField(default=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sponsor',
            name='bus',
            field=models.IntegerField(blank=True, default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sponsor',
            name='city',
            field=models.CharField(default='Bruges', max_length=40),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sponsor',
            name='country',
            field=models.CharField(default='Belgium', max_length=40),
        ),
        migrations.AddField(
            model_name='sponsor',
            name='postcode',
            field=models.IntegerField(default=8210),
            preserve_default=False,
        ),
    ]