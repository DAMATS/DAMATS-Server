# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coverages', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Entity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.CharField(unique=True, max_length=256)),
                ('name', models.CharField(max_length=256, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
            ],
            options={
                'verbose_name': 'DAMATS User or Group',
                'verbose_name_plural': '0. DAMATS Users and Groups',
            },
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.CharField(unique=True, max_length=256)),
                ('name', models.CharField(max_length=256, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(default=b'C', max_length=1, choices=[(b'C', b'CREATED'), (b'E', b'ACCEPTED'), (b'R', b'IN_PROGRESS'), (b'S', b'FINISHED'), (b'A', b'ABORTED'), (b'F', b'FAILED')])),
                ('inputs', models.TextField(null=True, blank=True)),
                ('outputs', models.TextField(null=True, blank=True)),
                ('wps_job_id', models.CharField(max_length=256, null=True, blank=True)),
                ('wps_response_url', models.CharField(max_length=512, null=True, blank=True)),
            ],
            options={
                'verbose_name': 'DAMATS Process Job',
                'verbose_name_plural': '7. DAMATS Process Jobs',
            },
        ),
        migrations.CreateModel(
            name='Process',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.CharField(unique=True, max_length=512)),
                ('name', models.CharField(max_length=256, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
            ],
            options={
                'verbose_name': 'DAMATS Process',
                'verbose_name_plural': '6. DAMATS Processes',
            },
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.CharField(max_length=256)),
                ('name', models.CharField(max_length=256, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('eoobj', models.OneToOneField(related_name='damats_result', verbose_name=b'Related EO Object', to='coverages.RectifiedDataset')),
                ('job', models.ForeignKey(related_name='results', to='webapp.Job')),
            ],
            options={
                'verbose_name': 'DAMATS Job Result',
                'verbose_name_plural': '8. DAMATS Job Results',
            },
        ),
        migrations.CreateModel(
            name='SourceSeries',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('eoobj', models.OneToOneField(related_name='damats_sources', verbose_name=b'Related Dataset Series', to='coverages.DatasetSeries')),
            ],
            options={
                'verbose_name': 'DAMATS Source Image Series',
                'verbose_name_plural': '3. DAMATS Source Image Series',
            },
        ),
        migrations.CreateModel(
            name='TimeSeries',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(null=True, blank=True)),
                ('selection', models.TextField(null=True, blank=True)),
                ('editable', models.BooleanField(default=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('eoobj', models.OneToOneField(related_name='damats_time_series', verbose_name=b'Related Dataset Series', to='coverages.DatasetSeries')),
            ],
            options={
                'verbose_name': 'DAMATS Image Time Series',
                'verbose_name_plural': '4. DAMATS Image Time Series',
            },
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('entity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='webapp.Entity')),
            ],
            options={
                'verbose_name': 'DAMATS Group',
                'verbose_name_plural': '2. DAMATS Groups',
            },
            bases=('webapp.entity',),
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('entity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='webapp.Entity')),
                ('active', models.BooleanField(default=True)),
                ('groups', models.ManyToManyField(related_name='users', to='webapp.Group', blank=True)),
            ],
            options={
                'verbose_name': 'DAMATS User',
                'verbose_name_plural': '1. DAMATS Users',
            },
            bases=('webapp.entity',),
        ),
        migrations.AddField(
            model_name='timeseries',
            name='readers',
            field=models.ManyToManyField(related_name='time_series_ro', to='webapp.Entity', blank=True),
        ),
        migrations.AddField(
            model_name='timeseries',
            name='source',
            field=models.ForeignKey(related_name='time_series', to='webapp.SourceSeries'),
        ),
        migrations.AddField(
            model_name='sourceseries',
            name='readers',
            field=models.ManyToManyField(related_name='sources', to='webapp.Entity', blank=True),
        ),
        migrations.AddField(
            model_name='process',
            name='readers',
            field=models.ManyToManyField(related_name='processes', to='webapp.Entity', blank=True),
        ),
        migrations.AddField(
            model_name='job',
            name='process',
            field=models.ForeignKey(related_name='jobs', to='webapp.Process'),
        ),
        migrations.AddField(
            model_name='job',
            name='readers',
            field=models.ManyToManyField(related_name='jobs_ro', to='webapp.Entity'),
        ),
        migrations.AddField(
            model_name='job',
            name='time_series',
            field=models.ForeignKey(related_name='jobs', to='webapp.TimeSeries'),
        ),
        migrations.AddField(
            model_name='timeseries',
            name='owner',
            field=models.ForeignKey(related_name='time_series', to='webapp.User'),
        ),
        migrations.AddField(
            model_name='job',
            name='owner',
            field=models.ForeignKey(related_name='jobs', to='webapp.User'),
        ),
    ]
