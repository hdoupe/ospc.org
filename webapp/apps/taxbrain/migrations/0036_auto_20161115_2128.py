# -*- coding: utf-8 -*-


from django.db import models, migrations
import webapp.apps.taxbrain.models


class Migration(migrations.Migration):

    dependencies = [
        ('taxbrain', '0035_auto_20161110_1624'),
    ]

    operations = [
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='ALD_Alimony_HC',
            new_name='ALD_Alimony_hc',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='ALD_EarlyWithdraw_HC',
            new_name='ALD_EarlyWithdraw_hc',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='ALD_KEOGH_SEP_HC',
            new_name='ALD_KEOGH_SEP_hc',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='ALD_SelfEmp_HealthIns_HC',
            new_name='ALD_SelfEmp_HealthIns_hc',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='ALD_SelfEmploymentTax_HC',
            new_name='ALD_SelfEmploymentTax_hc',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='ALD_StudentLoan_HC',
            new_name='ALD_StudentLoan_hc',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMED_thd_0',
            new_name='AMEDT_ec_0',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMED_thd_1',
            new_name='AMEDT_ec_1',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMED_thd_2',
            new_name='AMEDT_ec_2',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMED_thd_3',
            new_name='AMEDT_ec_3',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMED_thd_cpi',
            new_name='AMEDT_ec_cpi',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMED_trt',
            new_name='AMEDT_rt',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_CG_thd1_0',
            new_name='AMT_CG_brk1_0',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_CG_thd1_1',
            new_name='AMT_CG_brk1_1',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_CG_thd1_2',
            new_name='AMT_CG_brk1_2',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_CG_thd1_3',
            new_name='AMT_CG_brk1_3',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_CG_thd1_cpi',
            new_name='AMT_CG_brk1_cpi',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_CG_thd2_0',
            new_name='AMT_CG_brk2_0',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_CG_thd2_1',
            new_name='AMT_CG_brk2_1',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_CG_thd2_2',
            new_name='AMT_CG_brk2_2',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_CG_thd2_3',
            new_name='AMT_CG_brk2_3',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_CG_thd2_cpi',
            new_name='AMT_CG_brk2_cpi',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_tthd',
            new_name='AMT_brk1',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_tthd_cpi',
            new_name='AMT_brk1_cpi',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_trt1',
            new_name='AMT_rt1',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='AMT_trt2',
            new_name='AMT_rt2',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='CG_thd1_0',
            new_name='CG_brk1_0',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='CG_thd1_1',
            new_name='CG_brk1_1',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='CG_thd1_2',
            new_name='CG_brk1_2',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='CG_thd1_3',
            new_name='CG_brk1_3',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='CG_thd1_cpi',
            new_name='CG_brk1_cpi',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='CG_thd2_0',
            new_name='CG_brk2_0',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='CG_thd2_1',
            new_name='CG_brk2_1',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='CG_thd2_2',
            new_name='CG_brk2_2',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='CG_thd2_3',
            new_name='CG_brk2_3',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='CG_thd2_cpi',
            new_name='CG_brk2_cpi',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='ID_RealEstate_HC',
            new_name='ID_RealEstate_hc',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='ID_StateLocalTax_HC',
            new_name='ID_StateLocalTax_hc',
        ),
        migrations.RenameField(
            model_name='taxsaveinputs',
            old_name='NIIT_trt',
            new_name='NIIT_rt',
        ),
        migrations.AddField(
            model_name='taxsaveinputs',
            name='CTC_new_refund_limit_payroll_rt',
            field=webapp.apps.taxbrain.models.CommaSeparatedField(default=None, max_length=200, null=True, blank=True),
        ),
    ]