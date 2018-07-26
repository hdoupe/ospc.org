import csv
import pdfkit
import json
import os


from mock import Mock
import sys

import taxcalc
import datetime
from django.utils import timezone
from urllib.parse import urlparse, parse_qs
from ipware.ip import get_real_ip

from django.contrib.auth.decorators import permission_required
from django.http import (HttpResponseRedirect, HttpResponse, Http404,
                         JsonResponse)
from django.shortcuts import (render, render_to_response, get_object_or_404,
                              redirect)
from django.template.context import RequestContext
from django.contrib.auth.models import User

from .forms import TaxBrainForm
from .models import TaxSaveInputs
from .helpers import (taxcalc_results_to_tables, format_csv,
                      json_int_key_encode, make_bool)
from .param_displayers import nested_form_parameters
from ..core.compute import (Compute, JobFailError,
                            NUM_BUDGET_YEARS, NUM_BUDGET_YEARS_QUICK)
from ..taxbrain.models import TaxBrainRun, JSONReformTaxCalculator
from .mock_compute import MockCompute

from ..constants import (DISTRIBUTION_TOOLTIP, DIFFERENCE_TOOLTIP,
                         PAYROLL_TOOLTIP, INCOME_TOOLTIP, BASE_TOOLTIP,
                         REFORM_TOOLTIP, FISCAL_CURRENT_LAW, FISCAL_REFORM,
                         FISCAL_CHANGE, INCOME_BINS_TOOLTIP,
                         INCOME_DECILES_TOOLTIP, START_YEAR, START_YEARS,
                         DATA_SOURCES, DEFAULT_SOURCE, OUT_OF_RANGE_ERROR_MSG)

from ..formatters import get_version
from .param_formatters import (get_reform_from_file, get_reform_from_gui,
                               to_json_reform, append_errors_warnings)
from .submit_data import PostMeta, BadPost

from django.conf import settings

# Mock some module for imports because we can't fit them on Heroku slugs
MOCK_MODULES = ['matplotlib', 'matplotlib.pyplot', 'mpl_toolkits',
                'mpl_toolkits.mplot3d']
ENABLE_QUICK_CALC = bool(os.environ.get('ENABLE_QUICK_CALC', ''))
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

dropq_compute = Compute()

WEBAPP_VERSION = settings.WEBAPP_VERSION

tcversion_info = taxcalc._version.get_versions()

TAXCALC_VERSION = tcversion_info['version']

JOB_PROC_TIME_IN_SECONDS = 35


def log_ip(request):
    """
    Attempt to get the IP address of this request and log it
    """
    ip = get_real_ip(request)
    if ip is not None:
        # we have a real, public ip address for user
        print("BEGIN DROPQ WORK FROM: ", ip)
    else:
        # we don't have a real, public ip address for user
        print("BEGIN DROPQ WORK FROM: unknown IP")


def save_model(post_meta):
    """
    Save user input data
    returns OutputUrl object
    """
    model = post_meta.model
    # create model for file_input case
    if model is None:
        model = TaxSaveInputs()
    model.json_text = post_meta.json_reform
    model.first_year = int(post_meta.start_year)
    model.data_source = post_meta.data_source
    model.quick_calc = not post_meta.do_full_calc
    model.save()

    # create OutputUrl object
    if post_meta.url is None:
        unique_url = TaxBrainRun()
    else:
        unique_url = post_meta.url
    unique_url.job_ids = post_meta.submitted_ids
    unique_url.inputs = model
    unique_url.save()

    if post_meta.user:
        unique_url.user = post_meta.user
    elif post_meta.request and post_meta.request.user.is_authenticated():
        current_user = User.objects.get(pk=post_meta.request.user.id)
        unique_url.user = current_user

    if unique_url.upstream_vers is None:
        unique_url.upstream_vers = TAXCALC_VERSION
    if unique_url.webapp_vers is None:
        unique_url.webapp_vers = WEBAPP_VERSION

    cur_dt = timezone.now()
    future_offset_seconds = ((2 + post_meta.max_q_length) *
                             JOB_PROC_TIME_IN_SECONDS)
    future_offset = datetime.timedelta(seconds=future_offset_seconds)
    expected_completion = cur_dt + future_offset
    unique_url.exp_comp_datetime = expected_completion
    unique_url.save()

    return unique_url


def submit_reform(request, user=None, json_reform_id=None):
    """
    Parses user input data and submits reform

    returns dictionary of arguments intended to be inputs for `save_model`
    """
    fields = dict(request.GET)
    fields.update(dict(request.POST))
    fields = {k: v[0] if isinstance(v, list) else v
              for k, v in list(fields.items())}
    start_year = fields.get('start_year', START_YEAR)
    # TODO: migrate first_year to start_year to get rid of weird stuff like
    # this
    fields['first_year'] = fields['start_year']
    has_errors = make_bool(fields['has_errors'])

    # get files from the request object
    request_files = request.FILES

    # which file to use, front-end not yet implemented
    data_source = fields.get('data_source', 'PUF')
    use_puf_not_cps = (data_source == 'PUF')

    # declare a bunch of variables--TODO: clean this up
    taxcalc_errors = False
    taxcalc_warnings = False
    is_valid = True
    has_parse_errors = False
    _ew = {'warnings': {}, 'errors': {}}
    errors_warnings = {'policy': _ew.copy(), 'behavior': _ew.copy()}
    reform_dict = {}
    assumptions_dict = {}
    reform_text = ""
    assumptions_text = ""
    personal_inputs = None
    model = None
    is_file = False
    submitted_ids = None
    max_q_length = None
    # Assume we do the full calculation unless we find out otherwise
    do_full_calc = False if fields.get('quick_calc') else True
    if do_full_calc and 'full_calc' in fields:
        del fields['full_calc']
    elif 'quick_calc' in fields:
        del fields['quick_calc']

    # re-submission of file for case where file-input generated warnings
    if json_reform_id:
        try:
            json_reform = JSONReformTaxCalculator.objects.get(
                id=int(json_reform_id)
            )
        except Exception:
            msg = "ID {} is not in JSON reform database".format(json_reform_id)
            return BadPost(
                http_response_404=HttpResponse(msg, status=400),
                has_errors=True
            )
        reform_dict = json_int_key_encode(json.loads(json_reform.reform_text))
        assumptions_dict = json_int_key_encode(
            json.loads(json_reform.assumption_text))
        reform_text = json_reform.raw_reform_text
        assumptions_text = json_reform.raw_assumption_text
        errors_warnings = json_reform.get_errors_warnings()

        if "docfile" in request_files or "assumpfile" in request_files:
            if "docfile" in request_files or len(reform_text) == 0:
                reform_text = None
            if "assumpfile" in request_files or len(assumptions_text) == 0:
                assumptions_text = None

            (reform_dict, assumptions_dict, reform_text, assumptions_text,
                errors_warnings) = get_reform_from_file(request_files,
                                                        reform_text,
                                                        assumptions_text)

            json_reform.reform_text = json.dumps(reform_dict)
            json_reform.assumption_text = json.dumps(assumptions_dict)
            json_reform.raw_reform_text = reform_text
            json_reform.raw_assumption_text = assumptions_text
            json_reform.errors_warnings_text = json.dumps(errors_warnings)
            json_reform.save()

            has_errors = False

    else:  # fresh file upload or GUI run
        if 'docfile' in request_files:
            is_file = True
            (reform_dict, assumptions_dict, reform_text, assumptions_text,
                errors_warnings) = get_reform_from_file(request_files)
        else:
            personal_inputs = TaxBrainForm(start_year, use_puf_not_cps, fields)
            # If an attempt is made to post data we don't accept
            # raise a 400
            if personal_inputs.non_field_errors():
                return BadPost(
                    http_response_404=HttpResponse(
                        "Bad Input!", status=400
                    ),
                    has_errors=True
                )
            is_valid = personal_inputs.is_valid()
            if is_valid:
                model = personal_inputs.save(commit=False)
                model.set_fields()
                model.save()
                (reform_dict, assumptions_dict, reform_text, assumptions_text,
                    errors_warnings) = model.get_model_specs()
        json_reform = JSONReformTaxCalculator(
            reform_text=json.dumps(reform_dict),
            assumption_text=json.dumps(assumptions_dict),
            raw_reform_text=reform_text,
            raw_assumption_text=assumptions_text,
            errors_warnings_text=json.dumps(errors_warnings)
        )
        json_reform.save()

    # TODO: account for errors
    # 5 cases:
    #   0. no warning/error messages --> run model
    #   1. has seen warning/error messages and now there are no errors
    #        --> run model
    #   2. has not seen warning/error messages --> show warning/error messages
    #   3. has seen warning/error messages and there are still error messages
    #        --> show warning/error messages again
    #   4. no user input --> do not run model

    # We need to stop on both! File uploads should stop if there are 'behavior'
    # or 'policy' errors
    warn_msgs = any(len(errors_warnings[project]['warnings']) > 0
                    for project in ['policy', 'behavior'])
    error_msgs = any(len(errors_warnings[project]['errors']) > 0
                     for project in ['policy', 'behavior'])
    stop_errors = not is_valid or error_msgs
    stop_submission = stop_errors or (not has_errors and warn_msgs)
    if stop_submission:
        taxcalc_errors = bool(error_msgs)
        taxcalc_warnings = bool(warn_msgs)
        if personal_inputs is not None:
            # ensure that parameters causing the warnings are shown on page
            # with warnings/errors
            personal_inputs = TaxBrainForm(
                start_year,
                use_puf_not_cps,
                initial=json.loads(personal_inputs.data['raw_input_fields'])
            )
            # TODO: parse warnings for file_input
            # only handle GUI errors for now
            if ((taxcalc_errors or taxcalc_warnings) and
                    personal_inputs is not None):
                # we are only concerned with adding *static* reform errors to
                # the *static* reform page.
                append_errors_warnings(
                    errors_warnings['policy'],
                    lambda param, msg: personal_inputs.add_error(param, msg)
                )
            has_parse_errors = any('Unrecognize value' in e[0]
                                   for e
                                   in list(personal_inputs.errors.values()))
            if taxcalc_warnings or taxcalc_errors:
                personal_inputs.add_error(None, OUT_OF_RANGE_ERROR_MSG)
            if has_parse_errors:
                msg = ("Some fields have unrecognized values. Enter comma "
                       "separated values for each input.")
                personal_inputs.add_error(None, msg)
    else:
        log_ip(request)
        user_mods = dict({'policy': reform_dict}, **assumptions_dict)
        data = {'user_mods': user_mods,
                'first_budget_year': int(start_year),
                'use_puf_not_cps': use_puf_not_cps}
        if do_full_calc:
            data_list = [dict(year=i, **data) for i in range(NUM_BUDGET_YEARS)]
            submitted_ids, max_q_length = (
                dropq_compute.submit_calculation(data_list))
        else:
            data_list = [dict(year=i, **data)
                         for i in range(NUM_BUDGET_YEARS_QUICK)]
            submitted_ids, max_q_length = (
                dropq_compute.submit_quick_calculation(data_list))

    return PostMeta(
        request=request,
        personal_inputs=personal_inputs,
        json_reform=json_reform,
        model=model,
        stop_submission=stop_submission,
        has_errors=any([taxcalc_errors, taxcalc_warnings,
                        not is_valid]),
        errors_warnings=errors_warnings,
        start_year=start_year,
        data_source=data_source,
        do_full_calc=do_full_calc,
        is_file=is_file,
        reform_dict=reform_dict,
        assumptions_dict=assumptions_dict,
        reform_text=reform_text,
        assumptions_text=assumptions_text,
        submitted_ids=submitted_ids,
        max_q_length=max_q_length,
        user=user,
        url=None
    )


def process_reform(request, user=None, **kwargs):
    """
    Submits TaxBrain reforms.  This handles data from the GUI interface
    and the file input interface.  With some tweaks this model could be used
    to submit reforms for all PolicyBrain models

    returns OutputUrl object with parsed user input and warning/error messages
            if necessary
            boolean variable indicating whether this reform has errors or not
    """
    post_meta = submit_reform(request, user=user, **kwargs)
    if isinstance(post_meta, BadPost) or post_meta.stop_submission:
        return None, post_meta
        # (args['personal_inputs'], args['json_reform'], args['has_errors'],
        #  errors_warnings)
    else:
        url = save_model(post_meta)
        return url, post_meta


def file_input(request):
    """
    Receive request from file input interface and returns parsed data or an
    input form
    """
    form_id = request.POST.get('form_id', None)
    if form_id == 'None':
        form_id = None

    start_year = START_YEAR
    data_source = DEFAULT_SOURCE
    errors = []
    has_errors = False
    print('files', request.FILES)
    if request.method == 'POST':
        print('method=POST get', request.GET)
        print('method=POST post', request.POST)
        # save start_year
        start_year = (request.GET.get('start_year', None) or
                      request.POST.get('start_year', None))
        assert start_year is not None
        data_source = (request.GET.get('data_source', None) or
                       request.POST.get('start_year', None))
        assert data_source is not None

        # File is not submitted
        if 'docfile' not in dict(request.FILES) and form_id is None:
            errors = ["Please specify a tax-law change before submitting."]
            json_reform = None
        else:
            obj, post_meta = process_reform(request, json_reform_id=form_id)
            if isinstance(post_meta, BadPost):
                return post_meta.http_response_404
            else:
                unique_url = obj

            if post_meta.stop_submission:
                errors_warnings = post_meta.errors_warnings
                json_reform = post_meta.json_reform
                has_errors = post_meta.has_errors
                errors.append(OUT_OF_RANGE_ERROR_MSG)
                for project in ['policy', 'behavior']:
                    append_errors_warnings(
                        errors_warnings[project],
                        lambda _, msg: errors.append(msg)
                    )
            else:
                return redirect(unique_url)
    else:
        # Probably a GET request, load a default form
        print('method=GET get', request.GET)
        print('method=GET post', request.POST)
        params = parse_qs(urlparse(request.build_absolute_uri()).query)
        if 'start_year' in params and params['start_year'][0] in START_YEARS:
            start_year = params['start_year'][0]

        if ('data_source' in params and
                params['data_source'][0] in DATA_SOURCES):
            data_source = params['data_source'][0]

        json_reform = None

    init_context = {
        'form_id': json_reform.id if json_reform is not None else None,
        'errors': errors,
        'has_errors': has_errors,
        'upstream_version': TAXCALC_VERSION,
        'webapp_version': WEBAPP_VERSION,
        'params': None,
        'start_years': START_YEARS,
        'start_year': start_year,
        'data_sources': DATA_SOURCES,
        'data_source': data_source,
        'enable_quick_calc': ENABLE_QUICK_CALC,
        'input_type': "file"
    }

    return render(request, 'taxbrain/input_file.html', init_context)


def personal_results(request):
    """
    Receive data from GUI interface and returns parsed data or default data if
    get request
    """
    start_year = START_YEAR
    has_errors = False
    data_source = DEFAULT_SOURCE
    if request.method == 'POST':
        print('method=POST get', request.GET)
        print('method=POST post', request.POST)
        obj, post_meta = process_reform(request)
        # case where validation failed in forms.TaxBrainForm
        # TODO: assert HttpResponse status is 404
        if isinstance(post_meta, BadPost):
            return post_meta.http_response_404

        # No errors--submit to model
        if not post_meta.stop_submission:
            return redirect(obj)
        # Errors from taxcalc.tbi.reform_warnings_errors
        else:
            personal_inputs = post_meta.personal_inputs
            start_year = post_meta.start_year
            data_source = post_meta.data_source
            use_puf_not_cps = (data_source == 'PUF')
            has_errors = post_meta.has_errors

    else:
        # Probably a GET request, load a default form
        print('method=GET get', request.GET)
        print('method=GET post', request.POST)
        params = parse_qs(urlparse(request.build_absolute_uri()).query)
        if 'start_year' in params and params['start_year'][0] in START_YEARS:
            start_year = params['start_year'][0]

        # use puf by default
        use_puf_not_cps = True
        if ('data_source' in params and
                params['data_source'][0] in DATA_SOURCES):
            data_source = params['data_source'][0]
            if data_source != 'PUF':
                use_puf_not_cps = False

        personal_inputs = TaxBrainForm(first_year=start_year,
                                       use_puf_not_cps=use_puf_not_cps)

    init_context = {
        'form': personal_inputs,
        'params': nested_form_parameters(int(start_year), use_puf_not_cps),
        'upstream_version': TAXCALC_VERSION,
        'webapp_version': WEBAPP_VERSION,
        'start_years': START_YEARS,
        'start_year': start_year,
        'has_errors': has_errors,
        'data_sources': DATA_SOURCES,
        'data_source': data_source,
        'enable_quick_calc': ENABLE_QUICK_CALC
    }

    return render(request, 'taxbrain/input_form.html', init_context)


def submit_micro(request, pk):
    """
    This view handles the re-submission of a previously submitted microsim.
    Its primary purpose is to facilitate a mechanism to submit a full microsim
    job after one has submitted parameters for a 'quick calculation'
    """
    # TODO: get this function to work with process_reform
    url = get_object_or_404(TaxBrainRun, pk=pk)

    model = url.inputs
    start_year = model.start_year
    # This will be a new model instance so unset the primary key
    model.pk = None
    # Unset the computed results, set quick_calc to False
    # (this new model instance will be saved in process_model)
    model.job_ids = None
    model.jobs_not_ready = None
    model.quick_calc = False
    model.tax_result = None

    log_ip(request)

    # get microsim data
    is_file = model.json_text is not None
    json_reform = model.json_text
    # necessary for simulations before PR 641
    if not is_file:
        model.set_fields()
        (reform_dict, assumptions_dict, reform_text, assumptions_text,
            errors_warnings) = model.get_model_specs()
        json_reform = JSONReformTaxCalculator(
            reform_text=json.dumps(reform_dict),
            assumption_text=json.dumps(assumptions_dict),
            raw_reform_text=reform_text,
            raw_assumption_text=assumptions_text
        )
        json_reform.save()
    else:
        reform_dict = json_int_key_encode(
            json.loads(model.json_text.reform_text))
        assumptions_dict = json_int_key_encode(
            json.loads(model.json_text.assumption_text))

    user_mods = dict({'policy': reform_dict}, **assumptions_dict)
    print('data source', model.data_source)
    data = {'user_mods': user_mods,
            'first_budget_year': int(start_year),
            'use_puf_not_cps': model.use_puf_not_cps}

    # start calc job
    data_list = [dict(year=i, **data) for i in range(NUM_BUDGET_YEARS)]
    submitted_ids, max_q_length = dropq_compute.submit_calculation(
        data_list
    )

    post_meta = PostMeta(
        url=url,
        request=request,
        model=model,
        json_reform=json_reform,
        has_errors=False,
        start_year=start_year,
        data_source=model.data_source,
        do_full_calc=True,
        is_file=is_file,
        reform_dict=reform_dict,
        assumptions_dict=assumptions_dict,
        reform_text=(model.json_text.raw_reform_text
                     if model.json_text else ""),
        assumptions_text=(model.json_text.raw_assumption_text
                          if model.json_text else ""),
        submitted_ids=submitted_ids,
        max_q_length=max_q_length,
        user=None,
        personal_inputs=None,
        stop_submission=False,
        errors_warnings=None
    )

    url = save_model(post_meta)

    return redirect(url)


def edit_personal_results(request, pk):
    """
    This view handles the editing of previously entered inputs
    """
    url = get_object_or_404(TaxBrainRun, pk=pk)

    model = url.inputs
    start_year = model.first_year
    model.set_fields()

    msg = ('Field {} has been deprecated. Refer to the Tax-Calculator '
           'documentation for a sensible replacement.')
    form_personal_exemp = TaxBrainForm(
        first_year=start_year,
        use_puf_not_cps=model.use_puf_not_cps,
        instance=model
    )
    form_personal_exemp.is_valid()
    if model.deprecated_fields is not None:
        for dep in model.deprecated_fields:
            form_personal_exemp.add_error(None, msg.format(dep))

    taxcalc_vers_disp = get_version(url, 'upstream_vers', TAXCALC_VERSION)
    webapp_vers_disp = get_version(url, 'webapp_vers', WEBAPP_VERSION)

    init_context = {
        'form': form_personal_exemp,
        'params': nested_form_parameters(int(form_personal_exemp._first_year)),
        'upstream_version': taxcalc_vers_disp,
        'webapp_version': webapp_vers_disp,
        'start_years': START_YEARS,
        'start_year': str(form_personal_exemp._first_year),
        'is_edit_page': True,
        'has_errors': False,
        'data_sources': DATA_SOURCES,
        'data_source': model.data_source
    }

    return render(request, 'taxbrain/input_form.html', init_context)


@permission_required('taxbrain.view_inputs')
def csv_input(request, pk):
    url = get_object_or_404(TaxBrainRun, pk=pk)

    def filter_names(x):
        """
        Any of these field names we don't care about
        """
        return x not in ['outputurl', 'id', 'inflation', 'inflation_years',
                         'medical_inflation', 'medical_years', 'tax_result',
                         'creation_date']

    field_names = [f.name for f
                   in TaxSaveInputs._meta.get_fields(include_parents=False)]
    field_names = tuple(filter(filter_names, field_names))

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    now = timezone.now()
    suffix = "".join(map(str, [now.year, now.month, now.day, now.hour,
                               now.minute, now.second]))
    filename = "taxbrain_inputs_" + suffix + ".csv"
    response['Content-Disposition'] = 'attachment; filename="' + filename + '"'

    inputs = url_inputs

    writer = csv.writer(response)
    writer.writerow(field_names)
    writer.writerow([getattr(inputs, field) for field in field_names])

    return response
