def custom_locale_negotiator(request):
    """ The :term:`custom locale negotiator`. Returns a locale name.
    - First, the negotiator looks for the ``_LOCALE_`` attribute of
      the request object (possibly set by a view or a listener for an
      :term:`event`).
    - Then it looks for the ``request.params['_LOCALE_']`` value.
    - Then it looks for the ``request.cookies['_LOCALE_']`` value.
    - Then it looks for the ``Accept-Language`` header value,
      which is set by the user in his/her browser configuration.
    - Finally, if the locale could not be determined via any of
      the previous checks, the negotiator returns the
      :term:`default locale name`.
    """

    name = "_LOCALE_"
    if request.params.get(name) is not None:
        return request.params.get(name)
    if request.cookies.get(name) is not None:
        return request.cookies.get(name)
    return request.accept_language.best_match(
        request.registry.settings['available_languages'].split(),
        request.registry.settings['default_locale_name'],
    )
