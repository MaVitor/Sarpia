from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="presentation",
            name="context",
            field=models.CharField(
                choices=[
                    ("geral", "Geral"),
                    ("seminario", "Trabalho escolar ou seminário"),
                    ("defesa", "Defesa acadêmica"),
                    ("profissional", "Apresentação profissional"),
                    ("pitch", "Pitch ou proposta"),
                ],
                default="geral",
                max_length=16,
            ),
        ),
    ]
