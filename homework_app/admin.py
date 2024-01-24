from django.contrib import admin
# from .views import AddSchoolView

# class CustomAdminSite(admin.AdminSite):
#     def get_urls(self):
#         from django.urls import path
#         urls = super().get_urls()
#         custom_urls = [
#             path('add_school/', self.admin_view(AddSchoolView.as_view()), name='admin_add_school'),
#         ]
#         return custom_urls + urls

# admin_site = CustomAdminSite(name='customadmin')


# from django.contrib import admin
# from django.views.generic import View
# from django.shortcuts import render
# from django.contrib.admin.views.decorators import staff_member_required
# from django.utils.decorators import method_decorator
# from django.http import HttpResponse
# import csv

# @method_decorator(staff_member_required, name='dispatch')
# class AddSchoolView(View):
#     def get(self, request, *args, **kwargs):
#         return render(request, 'admin/add_school.html')

#     def post(self, request, *args, **kwargs):
#         # Handle file upload here
#         school_title = request.POST.get('school_title')
#         csv_file = request.FILES.get('file')

#         # Process the file and create users
#         if csv_file:
#             self.create_users_from_file(school_title, csv_file)
#             return HttpResponse(f'School Title: {school_title}, CSV File: {csv_file.name} processed successfully.')
#         else:
#             return HttpResponse('No CSV file provided.')

#     def create_users_from_file(self, school_title, csv_file):
#         reader = csv.DictReader(csv_file)

#         for row in reader:
#             email = row['email']
#             password = row['password']
#             # Create user based on the data
#             # Implement your logic here

# admin.site.register_view('add_school/', view=AddSchoolView.as_view(), name='admin_add_school')


# # create_users_from_file.short_description = "Create Users from File"

# # class CustomUserAdmin(admin.ModelAdmin):
# #     actions = [create_users_from_file]

#admin.register(CustomUser)??

