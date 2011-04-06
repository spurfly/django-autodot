Django autodot
=================

Turns django templates into doT templates in javascript.

Example::

	<% autodot user inline %>
	    <div>{{ user.name }} 
	            <% forjs phonetype, phonenumber in user.phonenumbers %> {# user.phonenumbers is a dict #}
	                    <div>{{ phonetype }}: {{ phonenumber }}</div>
	            <% endfor %>
	            Likes
	            <% autodot user.favoriteicecream as icecream %>
	                {{ icecream.flavor }} 
	            <% endautodot %>
	        <% ifjs user.friends %> has friends!
	            <% forjs simpleuser in user.friends %>
	                <% autodot simpleuser %>
	                    <div>{{ simpleuser.name }}</div>
	                <% endautodot %>
	            <% endfor %>
	        <% else %> has no friends. :(
	        <% endif %>
	    </div>
	<% endautodot %>
	.....
	{{ user_js }}
	{{ icecream_js }}
	{{ simpleuser_js }}

The above part of that would render as normal django, with ifjs working as if, forjs as for, and 
the autodot tag with an "as" as with. {{user_js}}

The {{ user_js }} would render as something like the following, but with newlines escaped:

	<script type="text/javascript">
	user_tmpl = doT.template("
		<div>{{=it.name }} 
	        {{ var icecream=it.favoriteicecream }}
	        {{ for (phonetype in user.phonenumbers) { var phonenumber =  it.user.phonenumbers[phonetype]; }}
	
	            <div>{{= it.user.phonenumbers.phonetype }}: {{=phonenumber }}</div>
	        {{ } }}
	            Likes
	            {{= icecream_tmpl(icecream) }}
	        {{ if (it.friends && !_.isEmpty(it.friends)) { }} has friends!
	            {{ var simpleuser; for (var i=0; i < it.friends.length; i++) { simpleuser = it.friends[i]; }}
	                {{ simpleuser_tmpl(simpleuser) }}
	            {{ }; }}
	        {{ } else { }} has no friends. :(
	        {{ }; }
	    </div>");
	
	test_user = user_tmpl({
	    name: "joe",
	    phonenumbers: {
	        'mobile': '555-555-5555',
	        'home': '555-555-5556'
	    },
	    friends: [{name: "sally"}],
	    favoriteicecream: {flavor: "chocolate}
	});
	</script>
	

Why?
********************************************

Short version: Nothing else did exactly what I needed.

Long version:

**PURE.js and Pyjamas javascript are too slow and bulky .**

**Because it's cool.**

**Automatic regeneration and cache-foreverable generated output**
  Statics are never stale and browsers can be told to cache the output forever.



Settings
********

Settings are currently borrowed as appropriate from Django Compressor. This
dependency will be resolved as a default-but-not-mandatory behavior later.

Django compressor has a number of settings that control it's behavior.
They've been given sensible defaults.

``COMPRESS``
------------

:Default: the opposite of ``DEBUG``

Boolean that decides if compression will happen.

``COMPRESS_URL``
----------------

:Default: ``MEDIA_URL``

Controls the URL that linked media will be read from and compressed media
will be written to.

``COMPRESS_ROOT``
-----------------

:Default: ``MEDIA_ROOT``

Controls the absolute file path that linked media will be read from and
compressed media will be written to.

``COMPRESS_OUTPUT_DIR``
-----------------------

:Default: ``'CACHE'``

Controls the directory inside `COMPRESS_ROOT` that compressed files will
be written to.

``COMPRESS_CSS_FILTERS``
------------------------

:Default: ``['compressor.filters.css_default.CssAbsoluteFilter']``

A list of filters that will be applied to CSS.

``COMPRESS_JS_FILTERS``
-----------------------

:Default: ``['compressor.filters.jsmin.JSMinFilter']``

A list of filters that will be applied to javascript.

``COMPRESS_STORAGE``
--------------------

:Default: ``'compressor.storage.CompressorFileStorage'``

The dotted path to a Django Storage backend to be used to save the
compressed files.

``COMPRESS_PARSER``
--------------------

:Default: ``'compressor.parser.BeautifulSoupParser'``

The backend to use when parsing the JavaScript or Stylesheet files.
The backends included in ``compressor``:

  - ``compressor.parser.BeautifulSoupParser``
  - ``compressor.parser.LxmlParser``

See `Dependencies`_ for more info about the packages you need for each parser.

``COMPRESS_CACHE_BACKEND``
--------------------------

:Default: ``"default"`` or ``CACHE_BACKEND``

The backend to use for caching, in case you want to use a different cache
backend for compressor.

If you have set the ``CACHES`` setting (new in Django 1.3),
``COMPRESS_CACHE_BACKEND`` defaults to ``"default"``, which is the alias for
the default cache backend. You can set it to a different alias that you have
configured in your ``CACHES`` setting.

If you have not set ``CACHES`` and are still using the old ``CACHE_BACKEND``
setting, ``COMPRESS_CACHE_BACKEND`` defaults to the ``CACHE_BACKEND`` setting.

``COMPRESS_REBUILD_TIMEOUT``
----------------------------

:Default: ``2592000`` (30 days in seconds)

The period of time after which the the compressed files are rebuilt even if
no file changes are detected.

``COMPRESS_MINT_DELAY``
------------------------

:Default: ``30`` (seconds)

The upper bound on how long any compression should take to run. Prevents
dog piling, should be a lot smaller than ``COMPRESS_REBUILD_TIMEOUT``.


``COMPRESS_MTIME_DELAY``
------------------------

:Default: ``None``

The amount of time (in seconds) to cache the result of the check of the
modification timestamp of a file. Disabled by default. Should be smaller
than ``COMPRESS_REBUILD_TIMEOUT`` and ``COMPRESS_MINT_DELAY``.


Dependencies
************

* BeautifulSoup_ (for the default ``compressor.parser.BeautifulSoupParser``)

::

    pip install BeautifulSoup

* lxml_ (for the optional ``compressor.parser.LxmlParser``, requires libxml2_)

::

    STATIC_DEPS=true pip install lxml

.. _BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/
.. _lxml: http://codespeak.net/lxml/
.. _libxml2: http://xmlsoft.org/
