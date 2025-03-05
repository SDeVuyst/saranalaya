from django.http import HttpResponseNotFound

class DomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0]
        
        if host == 'care-india.be':
            request.urlconf = 'admin_app.urls'
        elif host == 'vanakaam.be':
            request.urlconf = 'events.urls'
        else:
            # request.urlconf = 'admin_app.urls'
            return HttpResponseNotFound('Domain not recognized')
        
        response = self.get_response(request)
        return response