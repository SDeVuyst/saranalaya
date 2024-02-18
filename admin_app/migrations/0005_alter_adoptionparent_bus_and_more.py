# Generated by Django 5.0.2 on 2024-02-18 03:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0004_rename_address_adoptionparent_street_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adoptionparent',
            name='bus',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='adoptionparent',
            name='children',
            field=models.ManyToManyField(blank=True, null=True, to='admin_app.child'),
        ),
        migrations.AlterField(
            model_name='adoptionparent',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='adoptionparent',
            name='firm',
            field=models.CharField(blank=True, max_length=45, null=True),
        ),
        migrations.AlterField(
            model_name='adoptionparentsponsoring',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='child',
            name='date_of_leave',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='child',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='child',
            name='link_website',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='donation',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sponsor',
            name='bus',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sponsor',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sponsor',
            name='firm',
            field=models.CharField(blank=True, max_length=45, null=True),
        ),
        migrations.AlterField(
            model_name='sponsor',
            name='phone_number',
            field=models.CharField(blank=True, max_length=12, null=True),
        ),
    ]