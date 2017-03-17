# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='owner',
            field=models.ForeignKey(related_name='jobs', on_delete=django.db.models.deletion.PROTECT, to='webapp.User'),
        ),
        migrations.AlterField(
            model_name='job',
            name='process',
            field=models.ForeignKey(related_name='jobs', on_delete=django.db.models.deletion.PROTECT, to='webapp.Process'),
        ),
        migrations.AlterField(
            model_name='job',
            name='time_series',
            field=models.ForeignKey(related_name='jobs', on_delete=django.db.models.deletion.PROTECT, to='webapp.TimeSeries'),
        ),
        migrations.AlterField(
            model_name='result',
            name='eoobj',
            field=models.OneToOneField(related_name='damats_result', on_delete=django.db.models.deletion.PROTECT, verbose_name=b'Related EO Object', to='coverages.RectifiedDataset'),
        ),
        migrations.AlterField(
            model_name='sourceseries',
            name='eoobj',
            field=models.OneToOneField(related_name='damats_sources', on_delete=django.db.models.deletion.PROTECT, verbose_name=b'Related Dataset Series', to='coverages.DatasetSeries'),
        ),
        migrations.AlterField(
            model_name='sourceseries',
            name='name',
            field=models.CharField(max_length=256, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='timeseries',
            name='eoobj',
            field=models.OneToOneField(related_name='damats_time_series', on_delete=django.db.models.deletion.PROTECT, verbose_name=b'Related Dataset Series', to='coverages.DatasetSeries'),
        ),
        migrations.AlterField(
            model_name='timeseries',
            name='name',
            field=models.CharField(max_length=256, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='timeseries',
            name='owner',
            field=models.ForeignKey(related_name='time_series', on_delete=django.db.models.deletion.PROTECT, to='webapp.User'),
        ),
        migrations.AlterField(
            model_name='timeseries',
            name='source',
            field=models.ForeignKey(related_name='time_series', on_delete=django.db.models.deletion.PROTECT, to='webapp.SourceSeries'),
        ),
    ]
