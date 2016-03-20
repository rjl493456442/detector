"""detector URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin
from analyser import views
urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', views.index),
    url(r'^upload/$', views.upload_file_handler),
    url(r'^remove/$', views.remove_file_handler),
    url(r'^remove_record/$', views.remove_record_handler),
    url(r'^execute/$', views.execute),
    url(r'^error/(?P<type>.*)/$', views.error),
    url(r'^result/$', views.show_result),
    url(r'^save_csv/$', views.save_as_csv),
    url(r'^services/(?P<id>.*)/$', views.service_detail),
    url(r'^function/(?P<id>.*)/$', views.function_detail),
    url(r'^debug/$', views.debug),
    url(r'^login/$', views.login),
    url(r'^logout/$', views.logout_user),
    url(r'^register/$', views.register),
    url(r'^dashboard/$', views.dashboard),
    url(r'^make_comparison/$', views.make_comparison),
    url(r'^comparison_result/$', views.comparison_result),
    url(r'^history/$', views.show_history),
    url(r'^profile/$', views.edit_profile),
    url(r'^record/(?P<id>.*)/$', views.record_detail),
]
