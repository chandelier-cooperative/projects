# Published boards (apps/space) are not part of this project.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0123_delete_invites'),
    ]

    operations = [
        migrations.DeleteModel(name='DeployBoard'),
        migrations.DeleteModel(name='ProjectDeployBoard'),
        migrations.DeleteModel(name='ProjectPublicMember'),
    ]
