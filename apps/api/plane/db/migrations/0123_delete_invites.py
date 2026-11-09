# Invitations are not used in this project: people are added to workspaces from Chandelier.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0122_alter_draftissue_assignees_alter_issue_assignees_and_more'),
    ]

    operations = [
        migrations.DeleteModel(name='ProjectMemberInvite'),
        migrations.DeleteModel(name='WorkspaceMemberInvite'),
    ]
