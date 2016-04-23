# encoding=utf8
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from django.shortcuts import render
from core.execute import logProfiler
from django.shortcuts import render_to_response, HttpResponse, HttpResponseRedirect
from django.conf import settings
import json
import time
import os
import datetime
import hashlib
import logging
from core.regularExtrator import regularExtrator
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
import json
import csv
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import auth
from django.contrib.auth import logout
from core.util import HistroyRecord
import shutil

logging.basicConfig(level = logging.DEBUG,
                    format ='%(asctime)s %(name)s %(levelname)s %(module)s:%(lineno)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                   )
logger = logging.getLogger("network")

def index(request):
    if hasattr(request, 'session') and request.session.session_key:
        if 'file' in request.session.keys():
            del request.session['file']

    return render_to_response("index.html", locals())

def debug(request):
    return render_to_response("zoomcircle.html", locals())


@login_required
def dashboard(request):
    username = request.user.username
    return render_to_response("dashboard.html", locals())


def login(request):
    if request.method == 'POST':
        try:
            username = request.POST.get('username', '')
            password = request.POST.get('password', '')
            user = auth.authenticate(username = username, password = password)
            if user is not None and user.is_active:
                auth.login(request, user)
                return HttpResponseRedirect("/dashboard/")
            else:
                # TODO
                logger.error("invalid user authentication")
        except:
            pass
    elif request.method == "GET":
        pass
    else:
        pass
    return render_to_response("login.html")

def logout_user(request):
    logout(request)
    return HttpResponseRedirect('/login/')


def register(request):
    if request.user.is_authenticated():
        logout(request)
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        email = request.POST.get('email', '')
        if username and password and email:
            u = User.objects.create_user(username, email, password)
            u.save()
            user = auth.authenticate(username = username, password = password)
            auth.login(request, user)
            return HttpResponseRedirect("/dashboard/")
        else:
            # TODO
            logger.error("invalid registeration")
            return HttpResponseRedirect("/error/500/")
    return render_to_response("register.html")

def upload_file_handler(request):
    save_file_to_local(request.FILES['file'])
    try:
        if 'file' in request.session.keys():
            if request.FILES['file'].name in request.session['file']:
                pass
            else:
                request.session['file'].append(request.FILES['file'].name)
            logger.info("Add session :" + str(request.session['file']))
        else:
            request.session['file'] = [request.FILES['file'].name]
            logger.info("Add session :" + str(request.session['file']))
        request.session.modified = True
    except Exception, e:
        logger.error(e)
    response = HttpResponse({})
    return response

def remove_file_handler(request):
    if hasattr(request, 'session') and request.session.session_key:
        file = request.POST['name']
        isExist = False
        for f in os.listdir(settings.MEDIA_ROOT):
            if f == file:
                os.remove(os.path.join(settings.MEDIA_ROOT, f))
                isExist = True
        # TODO
        if isExist is True:
            response = HttpResponse({'status': 200})
        else:
            response = HttpResponse({'status': 404})

        file_lst = []
        if file in request.session['file']:
            for file_name in request.session['file']:
                if file_name != file:
                    file_lst.append(file_name)
            request.session['file'] = file_lst
            logger.info("after remove session :" +  str(request.session['file']))
        return response
    else:
        return None
def remove_record_handler(request):
    if request.method == "POST" and request.is_ajax():
        date = request.POST.get("date", "")
        username = request.user.username
        if date:
            # construct directory path
            path = os.path.join(settings.JSON_ROOT, username) + "/" + date
            try:
                # remove the whole directory
                shutil.rmtree(path)
            except Exception,e:
                logger.error(e)
                return HttpResponseRedirect('/error/500/')
    return HttpResponse(json.dumps({'status':200}))
def execute(request):
    if hasattr(request, 'session') and request.session.session_key:
        if 'file' in request.session.keys():
            file_list = request.session['file']
            logger.info("data :" +  str(file_list))
            if len(file_list) == 0:
                del request.session['file']
                logger.info("no input file")
                # status 400 bad requset
                return HttpResponse(json.dumps({'status':400}))
                # return render_to_response("errors_no_file.html", locals())
            else:
                valid_data = []
                for file in file_list:
                    if check_validation(file):
                        valid_data.append(file)
                    else:
                        logger.info(file + "unsupported formmat, discard")
                if len(valid_data) == 0:
                    del request.session['file']
                    return HttpResponse(json.dumps({'status':401}))
                   # return render_to_response("errors_file_invalid.html", locals())
                tool = logProfiler()
                begin = time.clock()
                datetime_str = datetime.datetime.now().strftime("%I:%M%p on %B %d,%Y")
                services_tree, rank_lst = tool.run(valid_data, request.user.username, datetime_str)
                elapsed = time.clock() - begin

                del request.session['file']

                process_file = []

                total_size = 0
                for file in file_list:
                    size = get_file_size(file)
                    total_size = total_size + size
                    tmp = {'name':file , 'size':size}
                    if file in valid_data:
                        tmp['status'] = "Processed"
                        tmp['reason'] = None
                    else:
                        tmp['status'] = "Unprocessed"
                        tmp['reason'] = "Unsupported format"
                    process_file.append(tmp)

                services = []
                for tree in services_tree:
                    services.append({'serviceId': tree.serviceId, 'max': tree.max_time , 'min': tree.min_time, 'avg':tree.root.executeTime / tree.root.cnt, 'cnt': tree.root.cnt, 'hot_spot': tree.get_hotspot()})

                ## save to session
                services = sorted(services, lambda x,y : cmp(x['avg'], y['avg']), reverse = True)
                # save record
                save_record(process_file, services, rank_lst, total_size, elapsed, request.user.username, datetime_str)
                ## erase those session when user visit homepage again
                return HttpResponse(json.dumps({'status':200}))
        else:
            logger.info("no input file")
            return HttpResponse(json.dumps({'status':400}))
            # return render_to_response("errors_no_file.html", locals())
    else:
        #TODO ERROR page
        return HttpResponse(json.dumps({'status':500}))
        # return render_to_response("errors_500.html", locals())

@login_required
def show_result(request):
    """ show a analysis result
        this function called only when a analysis finished
        user view a histroy record via record_detail function
    """
    if hasattr(request, 'session') and request.session.session_key:
        try:
            record = restore_record(request.user.username)
            services = record['services']
            rank_lst = record['rank_list']

            # shorten function name
            rank_lst_with_shorten_name = shorten_function_name(rank_lst)
            elapsed = record['elapsed']
            process_file = record['file_list']
            total_size = record['total_size']

            ''' throughput '''
            path = os.path.join(settings.JSON_ROOT,request.user.username) + "/temp/date.json"
            with open(path, "r+") as f:
                all_date = json.load(f)
            all_date.sort(key=lambda x:x['year'])
            all_date_with_good_format = []
            for item in all_date:
                all_date_with_good_format.append(
                    {
                        "year":item['year'][item['year'].find(' ') + 1 : ],
                        "value":item['value']
                    }
                )
            return render_to_response("result.html", locals())
        except Exception,e:
            logger.error(e)
            return render_to_response("errors_500.html", locals())
    else:
        return render_to_response("errors_500.html", locals())
def show_history(request):
    """ gather all history record from the user directory
        get detail information for a specific record from ${USER}/${DATE}/record.json file
    """
    username = request.user.username
    repostory = os.path.join(settings.JSON_ROOT, username)
    if os.path.exists(repostory):
        directory_name_list = [n for n in os.listdir(repostory) if os.path.isdir(os.path.join(repostory, n)) and n != "temp" and n != "comparison"]
        history_records = []
        for index, directory_name in enumerate(directory_name_list):
            record_file_name = os.path.join(repostory, directory_name) + "/record.json"
            with open(record_file_name, "r") as f:
                record = json.load(f)
                log_name = ""
                for log_file in record['file_list']:
                    log_name = log_name + "," + log_file['name']
                log_name = log_name.strip(',')
                history_records.append(
                    {
                        'elapsed_time' : record['elapsed'],
                        'total_size' : record['total_size'],
                        'date': directory_name,
                        'id': index + 1,
                        'file' : log_name
                    }
                )
    return render_to_response("history.html", locals())

def service_detail(request, id, date = None):
    """ show service analysis result
    Args:
        1) id: service full name
        2) date: if exists, to specify a history record data (always call after analysis finish)
                 otherwise, use the temp directory (always call when user view a history record)
    """
    if hasattr(request, 'session') and request.session.session_key:
        if date:
            path_part = date
        else:
            path_part = "temp"
        # get service info from temp directory
        # file_name: path to zoom pack diagram data, used when html render
        file_name = request.user.username + "/" + path_part + "/" + id + '.json'
        path = "/static/assets/data/" + file_name
        record = restore_record(request.user.username, date)
        services = record['services']
        service = None
        for i in services:
            if i['serviceId'] == id:
                service = i
                break
        if service:
            avg_time = round(service['avg'], 2)
            min_time = round(service['min'], 2)
            max_time = round(service['max'], 2)
            count = service['cnt']
            serviceId = service['serviceId']
        # get throughput from json file
        throughput_file = os.path.join(settings.JSON_ROOT, request.user.username) + "/" + path_part + "/" + id + "_date.json"
        try:
            with open(throughput_file, "r") as f:
                all_date = json.load(f)
            all_date.sort(key=lambda x:x['year'])
            all_date_with_good_format = []
            for item in all_date:
                all_date_with_good_format.append({"year":item['year'][item['year'].find(' ') + 1 : ], "value":item['value']})
        except Exception,e:
            logger.error(e)
        # get response time from json file
        response_time_file = os.path.join(settings.JSON_ROOT, request.user.username) + "/" + path_part + "/" + id + "_response.json"
        try:
            with open(response_time_file, "r") as f:
                all_response_time = json.load(f)
            all_response_time.sort(key=lambda x:x['occur_time'])
        except Exception,e:
            logger.error(e)

        return render_to_response("service_detail.html", locals())

@login_required
def function_detail(request, id, date = None):
    """ show function analysis result
    Args:
        1) id: function full name
        2) date: if exists, to specify a history record data (always call after analysis finish)
                 otherwise, use the temp directory (always call when user view a history record)
    """

    if date:
        path_part = date
    else:
        path_part = "temp"
    # get function related data
    record_file = os.path.join(settings.JSON_ROOT, request.user.username) + "/" + path_part + "/record.json"
    try:
        with open(record_file) as f:
            record = json.load(f)
        rank_list = record['rank_list']
        # find function related data
        function_data = None
        for function in rank_list:
            if function[0] == id:
                function_data = function
        if function_data:
            info = {}
            info['method_name'] = function_data[0]
            info['method_cnt'] = function_data[1]['cnt']
            info['method_avg'] = function_data[1]['avg']
            info['method_max'] = function_data[1]['max']
            info['method_min'] = function_data[1]['min']
            info['method_score'] = function_data[1]['score']
            if function_data[1]['score'] > 0.3:
                status = "Dangerous"
            elif function_data[1]['score'] > 0.1:
                status = "Normal"
            else:
                status = "Great"

            related_services = function_data[1]['services']
            related_services_list = []
            count_id = 1
            more_70_percentage_count = 0
            isleaf = function_data[1]['isleaf']
            for service_name, percentage in related_services.items():
                related_services_list.append({
                    'name' : service_name,
                    'percentage' : round(percentage[0] * 100, 2),
                    # TODO
                    # simple use the first percentageChildren, ignore the other
                    'child_percentage' : round(percentage[1][0] * 100, 2),
                    'id' : count_id
                })
                if percentage[0] > 0.7:
                    more_70_percentage_count += 1
                count_id += 1
            # sort related_services_list depand on percentage relative to root
            related_services_list.sort(key = lambda x: x['percentage'], reverse = True)
            info['related_services'] = related_services_list
            top_10_related_services_list = related_services_list[:10]
            return render_to_response("function_detail.html", locals())
        else:
            return HttpResponseRedirect("/error/500/")
    except Exception, e:
        logger.error(e)
        return HttpResponseRedirect("/error/500/")
@login_required
def record_detail(request, id):
    """ to show a history record detail
    Args:
        1) id : to specify the date of the record
    """
    date = id
    username = request.user.username
    file_path = os.path.join(settings.JSON_ROOT, username) + '/' + date + "/record.json"
    try:
        f = open(file_path, 'r')
        record = json.load(f)
        services = record['services']
        rank_lst = record['rank_list']

        rank_lst_with_shorten_name = shorten_function_name(rank_lst)
        elapsed = record['elapsed']
        process_file = record['file_list']
        total_size = record['total_size']

        ''' throughput '''
        path = os.path.join(settings.JSON_ROOT,request.user.username) + '/' + date +"/date.json"
        with open(path, "r+") as f:
            all_date = json.load(f)
        all_date.sort(key=lambda x:x['year'])
        all_date_with_good_format = []
        for item in all_date:
            all_date_with_good_format.append(
                {
                    "year":item['year'][item['year'].find(' ') + 1 : ],
                    "value":item['value']
                }
            )
        return render_to_response("record_detail.html", locals())
    except Exception, e:
        logger.error(e)
        return HttpResponseRedirect('/error/500/')
@login_required
def make_comparison(request):
    """ handle the comparison http request
        gather all request info to a json and transfer all data to comparison function
    Args:
        1) Http Request Object
    Returns:

    Raises:
    """
    # TODO specify the main record
    '''
        json file format
        [
            {
                'file' : filename,
                'date' : record_date
            },
            {
                'file' : filename,
                'date' : record_date
            },
            ...
            main_record_position
        ]
    '''
    if request.method == "POST" and request.is_ajax():
        all_record = []
        for key, value in request.POST.items():
            if key == 'baseline':
                baseline = value
            else:
                all_record.append({
                    'file' : value,
                    'date' : key
                })
        if len(all_record) != 2:
            logger.error("comparison record item must be 2")
            return HttpResponse(json.dumps({'status':800}))
        file_path = os.path.join(settings.JSON_ROOT, request.user.username) + "/temp/comparison.json"
        # temporary set the first record is the main record
        # TODO
        for index, record in enumerate(all_record):
            if record['file'] == baseline:
                baseline_position = index

        all_record.append(baseline_position)
        try:
            f = open(file_path, 'w+')
            json.dump(all_record, f, indent = 2)
        except Exception, e:
            logger.error(e)
            return HttpResponseRedirect('/error/500/')
        finally:
            f.close()
    return HttpResponse(json.dumps({'status':200}))

@login_required
def comparison_result(request):
    """demostrate result that target record compared to the baseline
    Args:
        1) Http Request Object

    Returns:

    Raises:
    """
    file_path = os.path.join(settings.JSON_ROOT, request.user.username) + "/temp/comparison.json"
    try:
        f = open(file_path, 'r')
        records = json.load(f)
        if len(records) != 3:
            logger.error("comparison record error")
            return HttpResponseRedirect("/error/500")
    except Exception, e:
        logger.error(e)
        return HttpResponseRedirect('/error/500/')
    finally:
        f.close()

    record_contents = []
    # get the position of the main record
    baseline_position = records[-1]
    if baseline_position is 0:
        analysis_position = 1
    else:
        analysis_position = 0
    # last element in records is the position of the main record
    # the length of the records should be 3, contain 2 comparison records and a position to specify the main record
    for record in records[:-1]:
        file_path = os.path.join(settings.JSON_ROOT, request.user.username) + "/" + record['date'] + "/record.json"
        try:
            f = open(file_path, 'r')
            record_content = json.load(f)
            '''
                record_contents contain the mapping between the date and relevant record content
            '''
            record_contents.append({
                'date': record['date'],
                'content': record_content
            })
        except Exception, e:
            logger.error(e)
            return HttpResponseRedirect('/error/500/')
        finally:
            f.close()
    # get the target record and baseline record
    target_record = record_contents[analysis_position]['content']
    baseline_record = record_contents[baseline_position]['content']
    target_date = record_contents[analysis_position]['date']
    baseline_date = record_contents[baseline_position]['date']
    '''
        function level process
        compare all function in score, response time aspects
    '''
    baseline_function_list = baseline_record['rank_list']
    target_record_scores, target_record_response_times = get_all_function_info(target_record['rank_list'], baseline_function_list)
    baseline_record_scores, baseline_record_response_times = get_all_function_info(baseline_record['rank_list'], baseline_function_list)
    function_name_list_with_shorten_name = shorten_function_name(baseline_function_list)
    # construct response data
    response_data_function_level = []
    for index, entry in enumerate(function_name_list_with_shorten_name):
        target_score = target_record_scores[index]
        baseline_score = baseline_record_scores[index]
        target_avg_response_time = target_record_response_times[index]
        baseline_avg_response_time = baseline_record_response_times[index]
        if target_score < baseline_score:
            status = "Imporved"
        else:
            status = "Not Improved"
        # calcu GR
        try:
            GR_score = (target_score - baseline_score) / target_score
        except ZeroDivisionError, e:
            GR_score = 0
        except TypeError, e:
            GR_score = None
        try:
            GR_response_time = (target_avg_response_time - baseline_avg_response_time) / target_avg_response_time
        except ZeroDivisionError, e:
            GR_response_time = 0
        except TypeError, e:
            GR_response_time = None

        if GR_score:
            GR_score = round(GR_score * 100, 2)
        if GR_response_time:
            GR_response_time = round(GR_response_time * 100, 2)
        function_name = entry
        response_data_function_level.append({
            'function_name' : function_name,
            'baseline_score' :  baseline_score,
            'target_score' : target_score,
            'baseline_response_time' : baseline_avg_response_time,
            'target_response_time' : target_avg_response_time,
            'GR_score' : GR_score,
            'GR_response_time' : GR_response_time,
            'status' : status
        })
    '''
        services level process
    '''
    baseline_standard_services = baseline_record['services']

    target_services_info = get_all_service_info(target_record['services'], baseline_standard_services)
    baseline_services_info = get_all_service_info(baseline_record['services'], baseline_standard_services)

    response_data_service_level = []
    for index, service_entry in enumerate(baseline_services_info):
        target_service = target_services_info[index]
        baseline_service = baseline_services_info[index]
        if target_service and baseline_service:
            for _, hot_spot in enumerate(baseline_service['hot_spot']):
                if target_service['hot_spot'][_]:
                    target_percentage = target_service['hot_spot'][_]['percentage']
                if baseline_service['hot_spot'][_]:
                    baseline_percentage = baseline_service['hot_spot'][_]['percentage']
                # calcu GR
                try:
                    if target_percentage and baseline_percentage:
                        GR_percentage = (target_percentage - baseline_percentage) / target_percentage
                    else:
                        GR_percentage = None
                except ZeroDivisionError,e :
                    GR_percentage = 0
                try:
                    target_service['hot_spot'][_]['GR'] = round(GR_percentage * 100, 2)
                except TypeError, e:
                    # hot spot exist in baseline, while not found in target service
                    # keep this element is None
                    pass
            # calcu response time GR
            try:
                if target_service['response_time'] and baseline_service['response_time']:
                    GR_response_time = (target_service['response_time'] - baseline_service['response_time']) / target_service['response_time']
                else:
                    GR_response_time = None
            except ZeroDivisionError,e :
                GR_response_time = 0

            response_data_service_level.append({
                'baseline_service' : baseline_service,
                'target_service' : target_service,
                'GR_response_time' : round(GR_response_time * 100, 2)
           })
        elif baseline_service and not target_service:
            response_data_service_level.append({
                'baseline_service' : baseline_service,
                'target_service' : None,
                'GR_response_time' : None
            })
        else:
            response_data_service_level.append({
                'baseline_service' : None,
                'target_service' : target_service,
                'GR_response_time' : None
            })
            logger.error("compare services error")
    '''
        hot spot diagram
    '''
    top_10_hot_spot = response_data_function_level[:10]
    return render_to_response('record_comparison.html', locals())

def edit_profile(request):
    if request.method == "POST":
        logger.info("EDIT PROFILE")
        user = User.objects.filter(username = request.user.username)[0]
        if request.POST['password1']:
            user.password = request.POST['password1']
        if request.POST['email']:
            email = request.POST['email']
            user.email = email
        if request.POST['firstname']:
            first_name = request.POST['firstname']
            user.first_name = request.POST['firstname']
        if request.POST['lastname']:
            last_name = request.POST['lastname']
            user.last_name = request.POST['lastname']
        user.save()
        username = request.user.username
        return render_to_response("user.html", locals())
    else:
        username = request.user.username
        user = User.objects.filter(username = username)[0]
        email = user.email
        first_name = user.first_name
        last_name = user.last_name
    return render_to_response("user.html", locals())
@login_required
def comparison_service_detail(request, service_name, target_date, baseline_date):
    """ service detail comparison
    Args:
        1) service_name : the name of the compared service
        2) target_date : target analysis record date
        3) baseline_date : baseline analysis record date
    Returns:

    Raises:
    """
    username = request.user.username
    target_path = os.path.join(settings.JSON_ROOT, request.user.username) + "/" + target_date + "/" + service_name + ".json"
    baseline_path = os.path.join(settings.JSON_ROOT, request.user.username) + "/" + baseline_date + "/" + service_name + ".json"
    # load target serivice and baseline service
    try:
        f = open(target_path, 'r')
        target_service = json.load(f)
    except Exception, e:
        logger.error(e)
        return HttpResponseRedirect('/error/500/')
    finally:
        f.close()

    try:
        f = open(baseline_path, 'r')
        baseline_service = json.load(f)
    except Exception, e:
        logger.error(e)
        return HttpResponseRedirect('/error/500/')
    finally:
        f.close()
    # start to comparsion
    compare_method_recursively(target_service, baseline_service)
    # save comparison result
    comparison_main_directory = os.path.join(settings.JSON_ROOT, request.user.username) + "/comparison"
    if not os.path.exists(comparison_main_directory):
        os.makedirs(comparison_main_directory)

    comparison_directory = comparison_main_directory + "/" + target_date + "_" + baseline_date
    if not os.path.exists(comparison_directory):
        os.makedirs(comparison_directory)

    result_path = comparison_main_directory + "/"  + "result.json"
    try:
        f = open(result_path, "w+")
        json.dump(target_service, f, indent = 2)
    except Exception, e:
        logger.error(e)
    finally:
        f.close()
    path = "/static/assets/data/" + request.user.username + "/comparison/result.json"
    return render_to_response("comparison_service_detail.html", locals())
# not in use now
def get_password(request):
    return render_to_response("get_password.html", locals())

def error(requset, type):
    if type == '400':
        return render_to_response("errors_no_file.html", locals())
    elif type == "500":
        return render_to_response("errors_500.html", locals())
    elif type == '401':
        return render_to_response("errors_file_invalid.html", locals())
    elif type == "comparison_error":
        return render_to_response("errors_comparison.html", locals())
    else:
        return render_to_response("errors_403.html",locals())

def save_as_csv(request):
    try:
        response = HttpResponse(content_type = "text/csv")
        response['Content-Disposition'] = 'attachment; filename="result.csv"'
        writer = csv.writer(response)
        if hasattr(request, 'session') and request.session.session_key:
            writer.writerow(['Function name', 'Score( Rms - Std )','Max(ms)', 'Avg(ms)', 'Min(ms)', 'Count'])
            record = restore_record(request.user.username)
            ranklist = record['rank_list']
            for row in ranklist:
                writer.writerow([row[0], row[1]['score'], row[1]['max'], row[1]['min'], row[1]['avg'], row[1]['cnt'] ])
    except Exception,e :
        logger.error(e)
    return response
def save_file_to_local(file, path = settings.MEDIA_ROOT):
    try:
        file_name = os.path.join(path, file.name)
        dest = open(file_name, 'w+')
        for chunk in file.chunks():
            dest.write(chunk)
        dest.close()
    except Exception,e:
        logger.error(e)
    finally:
        dest.close()

def get_file_size(file):
    size = os.stat(os.path.join(settings.MEDIA_ROOT, file)).st_size
    size = float("%0.2f" % (size * 1.0 / 1000 / 1000))
    return size

def check_validation(file):
    file_name = os.path.join(settings.MEDIA_ROOT, file)
    with open(file_name, 'r') as f:
        test_line = f.readline()
        r = regularExtrator()
        ret = r.extra(test_line)
        if ret == None:
            return False
        else:
            return True
def save_record(file_list, services, rank_list, total_size, elapsed, username, datetime_str):
    record = HistroyRecord()
    record.add_info("file_list", file_list)
    record.add_info("services", services)
    record.add_info("rank_list", rank_list)
    record.add_info("total_size", total_size)
    record.add_info("elapsed", elapsed)
    # save to database file
    record.save_record(username, datetime_str)
    # save to temp file
    record.save_record(username)

def restore_record(username, date = None):
    path_part = "temp"
    if date:
        path_part = date
    path = os.path.join(settings.JSON_ROOT, username) + "/" + path_part +"/record.json"
    with open(path, 'r') as f:
        record = json.load(f)
        return record

def shorten_function_name(rank_list):
    shorten_function_name_list = []
    for function_item in rank_list:
        function_name = function_item[0]
        if len(function_name) > 70:
            lst = function_name.split('.')
            lst[1] = "*"
            lst[2] = "*"
            lst[3] = "*"
            lst[4] = "*"
            function_item.append(('.').join(lst))
            shorten_function_name_list.append(('.').join(lst))
        else:
            function_item.append(function_name)
            shorten_function_name_list.append(function_name)
    return shorten_function_name_list
def shorten_function_name_by_method_name(method_name):
    if len(method_name) > 70:
        lst = method_name.split(".")
        lst[1] = "*"
        lst[2] = "*"
        lst[3] = "*"
        lst[4] = "*"
        return ('.').join(lst)
    return method_name

def format_service_name(service_name):
    """format service name
    Args:
        1)service_name : the service's name which need formatted

    Returns:
        1)formatted_service_name: an tuple contain the entity name and relavant pararmeters in service's name
    Raises:
        None
    """
    SEPERATE_CHAR = '['
    seperate_position = service_name.find('[')
    return (service_name[:seperate_position], service_name[seperate_position:])
def get_function_score(rank_list, method_name):
    '''
        @parameters
            1) rank_list : record['rank_list']
            2) method_name : specific method name
        @return
            1) score : relevant function score
    '''
    for function in rank_list:
        if function[0] == method_name:
            return function[1]['score']
    return None

def get_function_avg_response_time(rank_list, method_name):
    '''
        @parameters
            1) rank_list : record['rank_list']
            2) method_name : specific method name
        @return
            1) response time : relevant function response time

    '''
    for function in rank_list:
        if function[0] == method_name:
            return function[1]['avg']
    return None

def get_all_function_info(rank_list, target_function_list):
    all_scores = []
    all_response_time = []
    for function_item in target_function_list:
        all_scores.append(get_function_score(rank_list, function_item[0]))
        all_response_time.append(get_function_avg_response_time(rank_list, function_item[0]))
    return all_scores, all_response_time

def find_service(services, service_name):
    '''
        @parameters
            1) services : search services list
            2) service_name : specific service's name
        @return(if found, otherwise return None)
            1) return service object
    '''
    for service in services:
        if service['serviceId'] == service_name:
            return service
    return None
def find_hot_spot(service, hot_spot_name):
    '''
        @parameters
            1) service : search service object
            2) hot_spot_name : specific hot_spot's name
        @return(if found, otherwise return None)
            1) return hot_spot object
    '''
    for hot_spot in service['hot_spot']:
        if hot_spot['method_name'] == hot_spot_name:
            return hot_spot
    return None


def get_all_service_info(search_services, target_services):
    '''
        @parameters
            1) search_services :
            2) target_services :
        @return
            1) all services info and relavant hot spot method_name and percentage in service
    '''
    all_services_hot_spots = []
    for service in target_services:
        search_service = find_service(search_services, service['serviceId'])
        if search_service:
            # begin to find hot spot
            hot_spots = []
            for hot_spot in service['hot_spot']:
                search_hot_spot = find_hot_spot(search_service, hot_spot['method_name'])
                if search_hot_spot:
                    hot_spots.append({
                        'method_name' : shorten_function_name_by_method_name(search_hot_spot['method_name']),
                        'percentage' : round(search_hot_spot['percentage'], 2)
                    })
                else:
                    hot_spots.append(None)
            all_services_hot_spots.append({
                'service' : format_service_name(service['serviceId']),
                'response_time' : round(search_service['avg'], 2),
                'hot_spot' : hot_spots,
                'service_full' : service['serviceId']
            })
        else:
            # not found
            all_services_hot_spots.append(None)
    return all_services_hot_spots

def datetime_less(datetime_1, datetime_2):
    '''
        format: 10:07AM ON MARCH 12,2016
    '''
    year_1 = datetime_1.split(',')[-1]
    year_2 = datetime_2.split(',')[-1]
    month_1 = convert_literal_month_to_int(datetime_1[11:datetime_1.find(',') -3])
    month_2 = convert_literal_month_to_int(datetime_2[11:datetime_2.find(',') -3])
    day_1 = datetime_1[-7:-5]
    day_2 = datetime_2[-7:-5]
    hour_1 = datetime_1[:2]
    hour_2 = datetime_2[:2]
    minute_1 = datetime_1[3:5]
    minute_2 = datetime_2[3:5]
    if year_1 != year_2:
        return year_1 < year_2
    elif month_1 != month_2:
        return month_1 < month_2
    elif day_1 != day_2:
        return day_1 < day_2
    elif hour_1 != hour_2:
        return hour_1 < hour_2
    else:
        return minute_1 < minute_2



def convert_literal_month_to_int(literal_month):
    if literal_month == "January":
        return 1
    elif literal_month == "February":
        return 2
    elif literal_month == "March":
        return 3
    elif literal_month == "April":
        return 4
    elif literal_month == "May":
        return 5
    elif literal_month == "June":
        return 6
    elif literal_month == "July":
        return 7
    elif literal_month == "August":
        return 8
    elif literal_month == "September":
        return 9
    elif literal_month == "October":
        return 10
    elif literal_month == "November":
        return 11
    elif literal_month == "December":
        return 12
def get_lastest_date(date_list):
    position = None
    lastest_date = None
    for index, date in enumerate(date_list):
        if position is None:
            position = index
            lastest_date = date
        else:
            if datetime_less(lastest_date, date):
                position = index
                lastest_date = date
    return

def get_target_record(record_contents):
    '''
        @para : record_list
        @return : target_record, compare_record, target_position
    '''
    if datetime_less(record_contents[0]['date'], record_contents[1]['date']):
        position = 1
        position_compare = 0
    else:
        position = 0
        position_compare = 1
    return record_contents[position], record_contents[position_compare], position
def is_min_element_of_array(position, array):
    check_elem = array[position]
    for elem in array:
        if check_elem > elem:
            return False
    return True
def compare_method_recursively(target_service, baseline_service):
    """ compare method detail between target service and baseline service
        1) percentage
        2) avg selt time
    Args:
        1) target_service
        2) baseline_service
    Returns:

    Raises:

    Prerequisite:
        assume the two node in comparison is the same
    """
    target_percentage = target_service['percentage']
    baseline_percentage = baseline_service['percentage']
    target_avg = target_service['avg']
    baseline_avg = baseline_service['avg']
    # percentage
    try:
        if target_percentage == baseline_percentage:
            target_percentage_gr = 0
        else:
            target_percentage_gr =  1.0 * (target_percentage - baseline_percentage) / target_percentage
        # save to target_service
        delta_percentage = target_percentage - baseline_percentage
        target_service['percentage_gr'] = round(target_percentage_gr * 100, 2)
        target_service['percentage_delta'] = round(delta_percentage, 2)
    except Exception, e:
        logger.error(e)

    # avg self time

    try:
        if target_avg ==  baseline_avg:
            target_avg_gr = 0
        else:
            target_avg_gr = 1.0 * (target_avg - baseline_avg) / target_avg
        avg_delta = target_avg - baseline_avg
        target_service['avg_gr'] = round(target_avg_gr * 100, 2)
        target_service['avg_delta'] = round(avg_delta, 2)
    except Exception, e:
        logger.error(e)

    # process children

    if target_service.has_key('children'):
        for child in target_service['children']:
            b_find = False
            for _child in baseline_service['children']:
                if child['name'] == _child['name']:
                    compare_method_recursively(child, _child)
                    b_find = True
                    break
            if b_find  is False:
                pass


