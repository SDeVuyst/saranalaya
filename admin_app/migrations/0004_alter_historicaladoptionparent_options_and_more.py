# Generated by Django 5.0.6 on 2024-07-09 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0003_sponsor_letters_historicaladoptionparent_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='historicaladoptionparent',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'History', 'verbose_name_plural': 'historical Adoption Parents'},
        ),
        migrations.AlterModelOptions(
            name='historicaladoptionparentsponsoring',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'History', 'verbose_name_plural': 'historical Adoption Parent Payments'},
        ),
        migrations.AlterModelOptions(
            name='historicalchild',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'History', 'verbose_name_plural': 'historical Children'},
        ),
        migrations.AlterModelOptions(
            name='historicaldonation',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'History', 'verbose_name_plural': 'historical Donations'},
        ),
        migrations.AlterModelOptions(
            name='historicalsponsor',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'History', 'verbose_name_plural': 'historical Sponsors'},
        ),
    ]