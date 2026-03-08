"""
Erosion model refinements:
  1. Rename compare_model → parent_model, compare_id → parent_id
  2. Add 'action' and 'question_answer' to source/parent model choices
  3. Add db_index on parent_id
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_create_erosion_model"),
    ]

    operations = [
        # 1. Rename compare_model → parent_model
        migrations.RenameField(
            model_name="erosion",
            old_name="compare_model",
            new_name="parent_model",
        ),
        # 2. Rename compare_id → parent_id
        migrations.RenameField(
            model_name="erosion",
            old_name="compare_id",
            new_name="parent_id",
        ),
        # 3. Update choices on source_model to include action + question_answer
        migrations.AlterField(
            model_name="erosion",
            name="source_model",
            field=models.CharField(
                max_length=50,
                choices=[
                    ("proposal", "Proposal"),
                    ("order", "Order"),
                    ("invoice", "Invoice"),
                    ("purchase", "Purchase"),
                    ("payment", "Payment"),
                    ("credit_memo", "Credit Memo"),
                    ("action", "Action"),
                    ("question_answer", "Question / Answer"),
                ],
                help_text="Transaction type where erosion was detected",
            ),
        ),
        # 4. Update choices on parent_model (formerly compare_model)
        migrations.AlterField(
            model_name="erosion",
            name="parent_model",
            field=models.CharField(
                max_length=50,
                blank=True,
                null=True,
                choices=[
                    ("proposal", "Proposal"),
                    ("order", "Order"),
                    ("invoice", "Invoice"),
                    ("purchase", "Purchase"),
                    ("payment", "Payment"),
                    ("credit_memo", "Credit Memo"),
                    ("action", "Action"),
                    ("question_answer", "Question / Answer"),
                ],
                help_text="Transaction type being compared (e.g., proposal for margin erosion on invoice)",
            ),
        ),
        # 5. Add db_index on parent_id
        migrations.AlterField(
            model_name="erosion",
            name="parent_id",
            field=models.BigIntegerField(
                blank=True,
                null=True,
                db_index=True,
                help_text="PK of the parent/comparison transaction",
            ),
        ),
    ]
