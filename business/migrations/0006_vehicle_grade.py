# Generated by Django 5.1.6 on 2025-02-14 15:00

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0005_alter_trip_total_fare'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='grade',
            field=models.CharField(default=django.utils.timezone.now, max_length=100),
            preserve_default=False,
        ),
    ]
