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
        if 'services' in request.session.keys():
            del request.session['services']
        if 'rank_lst' in request.session.keys():
            del request.session['rank_lst']
        if 'process_file' in request.session.keys():
            del request.session['process_file']
        if 'total_size' in request.session.keys():
            del request.session['total_size']
        if 'elapsed' in request.session.keys():
            del request.session['elapsed']

    return render_to_response("index.html", locals())


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
        if 'file' in request.session['file']:
            for file_name in request.session['file']:
                if file_name != file:
                    file_lst.append(file_name)
            request.session['file'] = file_lst
            logger.info("remove session :" +  str(request.session['file']))
        return response
    else:
        return None

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
                services_tree, rank_lst = tool.run(valid_data, request.session.session_key)
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
                request.session['services_tree'] = services
                request.session['rank_lst'] = rank_lst
                request.session['elapsed'] =  elapsed
                request.session['process_file'] = process_file
                request.session['total_size'] = total_size
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
def show_result(request):
    if hasattr(request, 'session') and request.session.session_key:
        try:
            services = request.session['services_tree']
            rank_lst = request.session['rank_lst']
            elapsed = request.session['elapsed']
            process_file = request.session['process_file']
            total_size = request.session['total_size']
            return render_to_response("result.html", locals())
        except Exception,e:
            logger.error(e)
            return render_to_response("errors_500.html", locals())
    else:
        return render_to_response("errors_500.html", locals())

def service_detail(request, id):
    if hasattr(request, 'session') and request.session.session_key:
        sessionid = request.session.session_key
        file_name = sessionid + "/" + id + '.json'
        path = "/static/assets/data/" + file_name
        services = request.session['services_tree']
        for i in services:
            if i['serviceId'] == id:
                service = i
                break
        return render_to_response("service_detail.html", locals())

def test(request):
    return render_to_response("result.html", locals())
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
            ranklist = request.session['rank_lst']
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




