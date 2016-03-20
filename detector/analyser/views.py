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
# Create your views here.

logging.basicConfig(level = logging.DEBUG,
                    format = '%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                   )
logger = logging.getLogger("network")

def index(request):
    if hasattr(request, 'session') and request.session.session_key:
        if 'file' in request.session.keys():
            del request.session['file']

    return render_to_response("index.html", locals())

def debug(request):
    if request.method == "POST" and request.is_ajax():
        pass
    return HttpResponse(json.dumps({'status':200}))


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
                logger.info(datetime_str)
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
                    services.append({'serviceId': tree.serviceId, 'max': tree.root.maxTime , 'min': tree.root.minTime, 'avg':tree.root.executeTime / tree.root.cnt, 'cnt': tree.root.cnt, 'hot_spot': tree.get_hotspot()})

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
    username = request.user.username
    repostory = os.path.join(settings.JSON_ROOT, username)
    if os.path.exists(repostory):
        directory_name_list = [n for n in os.listdir(repostory) if os.path.isdir(os.path.join(repostory, n)) and n != "temp"]
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

def service_detail(request, id):
    if hasattr(request, 'session') and request.session.session_key:
        # get service info from temp directory
        file_name = request.user.username + "/temp/" + id + '.json'
        path = "/static/assets/data/" + file_name
        record = restore_record(request.user.username)
        services = record['services']
        for i in services:
            if i['serviceId'] == id:
                service = i
                break
        # get throughput from json file
        throughput_file = os.path.join(settings.JSON_ROOT, request.user.username) + "/temp/" + id + "_date.json"
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
        response_time_file = os.path.join(settings.JSON_ROOT, request.user.username) + "/temp/" + id + "_response.json"
        try:
            with open(response_time_file, "r") as f:
                all_response_time = json.load(f)
            all_response_time.sort(key=lambda x:x['occur_time'])
        except Exception,e:
            logger.error(e)

        return render_to_response("service_detail.html", locals())

@login_required
def function_detail(request, id):
    # get function related data
    record_file = os.path.join(settings.JSON_ROOT, request.user.username) + "/temp/record.json"
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
            related_services = function_data[1]['services']
            related_services_list = []
            count_id = 1
            for service_name, percentage in related_services.items():
                related_services_list.append({
                    'name' : service_name,
                    'percentage' : percentage * 100,
                    'id' : count_id
                })
                count_id += 1
            info['related_services'] = related_services_list
            return render_to_response("function_detail.html", locals())
        else:
            return HttpResponseRedirect("/error/500/")
    except Exception, e:
        logger.error(e)
        return HttpResponseRedirect("/error/500/")
@login_required
def record_detail(request, id):
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
        return render_to_response("result.html", locals())
    except Exception, e:
        logger.error(e)
        return HttpResponseRedirect('/error/500/')
@login_required
def make_comparison(request):
    if request.method == "POST" and request.is_ajax():
        all_record = []
        for key, value in request.POST.items():
            all_record.append({
                'file' : key,
                'date' : value
            })
        file_path = os.path.join(settings.JSON_ROOT, request.user.username) + "/temp/comparison.json"
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
    file_path = os.path.join(settings.JSON_ROOT, request.user.username) + "/temp/comparison.json"
    try:
        f = open(file_path, 'r')
        records = json.load(f)
    except Exception, e:
        logger.error(e)
        return HttpResponseRedirect('/error/500/')
    finally:
        f.close()

    record_contents = []
    lastest_date = None
    dates = []
    for record in records:
        file_path = os.path.join(settings.JSON_ROOT, request.user.username) + "/" + record['date'] + "/record.json"
        dates.append(record['date'])
        try:
            f = open(file_path, 'r')
            record_content = json.load(f)
            record_contents.append({
                'date': record['date'],
                'content': record_content
            })
        except Exception, e:
            logger.error(e)
            return HttpResponseRedirect('/error/500/')
        finally:
            f.close()
    lastest_date_position = get_lastest_date(dates)
    template_record = record_contents[0]['content']
    template = template_record['rank_list']
    top_five_template = template[:5]
    top_five_template_with_shorten_name = shorten_function_name(top_five_template)

    all_functions = []
    all_date = []
    for record_content in record_contents:
        all_scores = get_all_function_score(record_content['content']['rank_list'], template)
        all_date.append({
            'date': record_content['date'],
            'score': all_scores,
        })
    for function in template:
        scores = []
        for record_content in record_contents:
            rank_list = record_content['content']['rank_list']
            score = get_function_score(rank_list, function[0])
            scores.append(score)

        if is_min_element_of_array(lastest_date_position, scores):
            status = "Improved"
        else:
            status = "Not Improved"
        all_functions.append({
            'function_name' : shorten_function_name_by_method_name(function[0]),
            'score' : scores,
            'status': status
        })
    top_five_date = all_date[:5]
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
def error(requset, type):
    if type == '400':
        return render_to_response("errors_no_file.html", locals())
    elif type == "500":
        return render_to_response("errors_500.html", locals())
    elif type == '401':
        return render_to_response("errors_file_invalid.html", locals())
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

def restore_record(username):
    path = os.path.join(settings.JSON_ROOT, username) + "/temp/record.json"
    with open(path, 'r') as f:
        record = json.load(f)
        return record

def shorten_function_name(rank_list):
    for function_item in rank_list:
        function_name = function_item[0]
        if len(function_name) > 70:
            lst = function_name.split('.')
            lst[1] = "*"
            lst[2] = "*"
            lst[3] = "*"
            lst[4] = "*"
            function_item.append(('.').join(lst))
        else:
            function_item.append(function_name)
    return rank_list
def shorten_function_name_by_method_name(method_name):
    if len(method_name) > 70:
        lst = method_name.split(".")
        lst[1] = "*"
        lst[2] = "*"
        lst[3] = "*"
        lst[4] = "*"
        return ('.').join(lst)
    return method_name

def get_function_score(rank_list, method_name):
    for function in rank_list:
        if function[0] == method_name:
            return function[1]['score']
def get_all_function_score(rank_list, method_name_list):
    logger.info(method_name_list)
    all_score = []
    for method in method_name_list:
        all_score.append(get_function_score(rank_list, method[0]))
    return all_score

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
    return position
def is_min_element_of_array(position, array):
    check_elem = array[position]
    for elem in array:
        if check_elem > elem:
            return False
    return True
