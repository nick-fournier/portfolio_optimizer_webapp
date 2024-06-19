# portfolio_optimizer_webapp

This app provides a simple stock filter using Piotroski F-scores and performs mean-variance portfolio optimization.

Quick start
-----------

1. Add "portfolio_optimizer_webapp" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'portfolio_optimizer_webapp.webframe',
    ]

2. Include the portfolio_optimizer_webapp URLconf in your project urls.py like this:
    path('portfolio_optimizer_webapp/', include('portfolio_optimizer_webapp.webframe.urls')),

3. Run ``python manage.py migrate`` to create the polls models.

4. Start the development server with `python manage.py runserver` and visit http://127.0.0.1:8000/admin/.
