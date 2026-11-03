from django.db import migrations, models


OLD_HERO = "Корпусная мебель, созданная именно для вас"
NEW_HERO = "Корпусная мебель на заказ по вашим размерам"
OLD_SUBTITLE = "По индивидуальным размерам. С вниманием к качеству исполнения и каждой детали."
NEW_SUBTITLE = "Кухни, шкафы, гардеробные и другая мебель по индивидуальному проекту. Продумываем детали вместе с вами, а материалы и цвета выбираем по настоящим образцам."


def update_default_copy_and_add_faq(apps, schema_editor):
    SiteSettings = apps.get_model("catalog", "SiteSettings")
    FAQ = apps.get_model("catalog", "FAQ")
    using = schema_editor.connection.alias

    # Preserve copy already customized in the admin panel.
    SiteSettings.objects.using(using).filter(hero_title=OLD_HERO).update(hero_title=NEW_HERO)
    SiteSettings.objects.using(using).filter(hero_text=OLD_SUBTITLE).update(hero_text=NEW_SUBTITLE)

    common_questions = [
        ("Какую корпусную мебель можно заказать?",
         "Кухни, шкафы, гардеробные, прихожие и другую корпусную мебель по индивидуальным размерам."),
        ("Как узнать стоимость?",
         "Стоимость зависит от размеров, конструкции и материалов. Оставьте телефон — обсудим задачу и уточним детали для расчёта."),
        ("Можно выбрать цвет и материалы?",
         "Да. Цвета и материалы подбираем при личном обсуждении, по настоящим образцам, а не по изображению на экране."),
        ("В каких городах вы работаете?",
         "Стерлитамак, Салават и Ишимбай."),
    ]
    FAQ.objects.using(using).bulk_create([
        FAQ(question=question, answer=answer, order=position)
        for position, (question, answer) in enumerate(common_questions, 1)
    ])


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="FAQ",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.CharField(max_length=220, verbose_name="Вопрос")),
                ("answer", models.TextField(verbose_name="Ответ")),
                ("published", models.BooleanField(default=True, verbose_name="Опубликовано")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
            ],
            options={
                "verbose_name": "Вопрос и ответ",
                "verbose_name_plural": "Частые вопросы",
                "ordering": ["order", "id"],
            },
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="hero_title",
            field=models.CharField(
                default=NEW_HERO, max_length=220, verbose_name="Заголовок"
            ),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="hero_text",
            field=models.TextField(default=NEW_SUBTITLE, verbose_name="Подзаголовок"),
        ),
        migrations.RunPython(update_default_copy_and_add_faq, migrations.RunPython.noop),
    ]
