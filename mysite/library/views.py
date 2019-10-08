from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .library_spider import check_valid_cookie, LibrarySpider
from .models import CookieModel
import time

def log_in(request):
    if request.method == 'GET':
        return render(request,'library/log_in.html')
    elif request.method == 'POST':
        ssid = request.POST.get("ssid")
        print(ssid)
        return redirect(reverse('library:library'))
    

def library_form(request):
    object = get_object_or_404(CookieModel, ip=request.META.get("REMOTE_ADDR"))
    now_time = int(time.time())
    if now_time - object.last_time >= 1750:
        return redirect(reverse("library:log_in"))
    cookies = eval(object.cookies)
    if request.method == 'GET':
        # 感觉这里写的很不好，先实现了逻辑再说
        spider = LibrarySpider(cookies=cookies)
        seat_info = spider.seat_info
        del spider
        return render(request,'library/text.html', context={"seat_info": seat_info})
    elif request.method == 'POST':
       # print(request.POST.get('library'))
        building = request.POST.get("library")
        startMin = request.POST.get("startMin")
        endMin = request.POST.get("endMin")
        spider = LibrarySpider(cookies=cookies)
        spider.send_req_humanly(building, startMin, endMin)
        return HttpResponse(str(spider.seat_info))
# Create your views here.

@csrf_exempt
def ssid_check(request):
    if request.method != "POST":
        raise Http404
    else:
        ssid = str(request.POST.get("ssid"))
        cookies = {"JSESSIONID": ssid}
        result = check_valid_cookie(cookies)
        if result:
            if result == 2:
                return JsonResponse({"status": "2"})

            ip_addr = request.META.get("REMOTE_ADDR")
            object, created = CookieModel.objects.get_or_create(ip=ip_addr)
            object.last_time = int(time.time())
            object.cookies = str(cookies)
            object.save()

            return JsonResponse({"status": "1"})
        return JsonResponse({"status": "0"})
