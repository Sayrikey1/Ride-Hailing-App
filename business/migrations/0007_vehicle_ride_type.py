# Generated by Django 5.1.6 on 2025-02-14 15:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0006_vehicle_grade'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='ride_type',
            field=models.CharField(choices=[('R', 'Regular'), ('C', 'Comfort'), ('E', 'Exotic'), ('S', 'Super')], default='R', max_length=2),
        ),
    ]
