import os
import json
from django import template
from django.template import Context, Template, TemplateSyntaxError
from django.template.loader import render_to_string
from django.template.defaulttags import IfNode, WithNode, ForNode, do_if, do_for, do_with
from django.core.files.base import ContentFile

#avoidable but non-problematic dependency on django-compressor
from compressor.conf import settings
from compressor.utils import get_hexdigest, get_mtime, get_class

OUTPUT_FILE = 'file'
OUTPUT_INLINE = 'inline'

register = template.Library()

class AutodotContextMember(object):
    def __init__(self, name):
        self.name = name
        
    def __getitem__(self, key):
        return self.__getattr__(key)
    
    def __getattr__(self, key):
        return AuodotContextMember("%s.%s" % (self.name, key))
    
    def __str__(self):
        return "{{=%s}}" % self.name

@register.tag(name="autodot")
def autodot(parser, token):
    """
    <% autodot user %> - starts a template for a user object
    <% autodot user inline %> - ditto but script will be put in the html inline
    <% autodot some.variable[path] as user %> - like <% withjs some.variable[path] as user %><% autodot user %>
    <% autodot some.variable[path] as user inline %> - as expected
    """
    args = token.split_contents()
    
    if not len(args) in (2, 3, 4, 5):
        raise template.TemplateSyntaxError("%r tag requires one to four arguments." % args[0])
    
    if len(args) in (4, 5):
        if args[2] != "as":
            raise template.TemplateSyntaxError("%r tag with 3 or 4 arguments must be 'a as b'." % args[0])
        withsrc = args[1]
        args = args[:1] + args[3:]
    else:
        withsrc = None
        
    model_name = args[1]
    varsrc = parser.compile_filter(withsrc or model_name)
    if len(args) == 3:
        mode = args[2]
        if not mode in (OUTPUT_FILE, OUTPUT_INLINE):
            raise template.TemplateSyntaxError("%r's second argument must be '%s' or '%s'." % (args[0], OUTPUT_FILE, OUTPUT_INLINE))
    else:
        mode = OUTPUT_FILE
        
    nodelist = parser.parse(('endautodot',))
    parser.delete_first_token()
    return AutodotNode(nodelist, model_name, varsrc, mode, withsrc)

class AutodotNode(template.Node):
    extension = ".js"
    output_prefix = "autodot"
    template_name = "autodot/js.html"
    template_name_inline = "autodot/js_inline.html"
    
    def __init__(self, nodelist, model_name, varsrc, mode=OUTPUT_FILE, withsrc=None):
        self.nodelist = nodelist
        self.model_name = model_name
        self.mode = mode
        self.varsrc = varsrc
        self.withsrc = withsrc
        self.template = nodelist.render(Context({model_name: AutodotContextMember("it"),
                                         "AS_AUTODOT": True,
                                         }))
        self.js = """%s_tmpl = doT.template(%s);\n""" % (model_name, json.dumps(self.template))
        if self.mode == OUTPUT_FILE:
            self.filepath = None
            self.save_file()
        
    def save_file(self, content=None):
        usecontent = content or self.js
        filepath = self._new_filepath(content)
        if self.storage.exists(filepath):
            return False
        self.storage.save(filepath, ContentFile(usecontent.encode("utf-8")))
        return True
    
    @property
    def new_filepath(self):
        return self._new_filepath()
    
    def _new_filepath(self, content=None):
        if content or not self.filepath:
            usecontent = content or self.js
            filename = "".join([self._hash(usecontent), self.extension])
            filepath = os.path.join(
                settings.OUTPUT_DIR.strip(os.sep), self.output_prefix, filename)
            if not content:
                self.filepath = filepath
            return filepath
        else:
            return self.filepath
        
    @property
    def storage(self):
        from compressor.storage import default_storage
        return default_storage
    
    @property
    def hash(self):
        return self._hash()
    
    def _hash(self, content=None):
        if not content:
            content = self.js
        return get_hexdigest(content)[:12]
    
    @property
    def script_tag(self):
        return self._script_tag()
    
    def _script_tag(self, content=None):
        usecontent = content or self.js
        if self.mode == OUTPUT_INLINE:
            return render_to_string(self.template_name_inline, {'content': usecontent})
        else:
            return render_to_string(self.template_name, {'url': self.storage.url(self._new_filepath(content))})
            
    
    def render(self, context):
        if context.get("AS_AUTODOT", None):
            model_var = self.withsrc or self.model_name
            return "{{= %s_tmpl(%s) }}" % (self.model_name, model_var)
        else:
            if self.withsrc:
                val = self.varsrc.resolve(context)
                context.push()
                context[self.model_name] = val
                output = self.nodelist.render(context)
                context.pop()
            else:
                output = self.nodelist.render(context)
            context[self.model_name + "_js"] = self.script_tag
            return output
        

@register.tag(name="autodot_test")
def autodot_test(parser, token):
    thenode = autodot(parser, token)
    thenode.__class__ = AutodotTestNode
    return thenode

class AutodotTestNode(AutodotNode):
    #def __init__(self, nodelist, model_name, varsrc, mode=OUTPUT_FILE, withsrc=None):
    #    AutodotNode.__init__(self, nodelist, model_name, varsrc, mode, withsrc)
        
    def test_js(self, model_value):
        """
        Construct javascript which contains the of the model passed to Django, and
        sees if doT produces the same template output.
        """
        return """
        var autodot_testdata = %s,
            autodot_js_output = %s_tmpl(autodot_testdata),
            autodot_hash = "%s",
            autodot_django_output = $("#%s_test_containingdiv" + autodot_hash).html(),
            autodot_test_name = "%s";
        if (_.equals(template_js_output, template_django_output) {
            console.echo("Autodot template works: " + autodot_test_name + autodot_hash);
        } else {
            console.echo("Autodot template doesn't work: " + autodot_test_name + autodot_hash);
        }
        """ % (
               json.dumps(model_value),
               self.model_name, 
               self.hash,
               self.model_name,
               self.model_name,
               )
        
    def containing_div(self, contents):
        return """<div id="%s_test_containingdiv%s">%s</div>""" % (
                        self.model_name, self.hash, contents)
        
    def render(self, context):
        output = AutodotNode.render(self, context)
        if context.get("AS_AUTODOT", None):
            return output
        test_js = self.test_js(self.varsrc.resolve(context))
        if self.mode == OUTPUT_FILE:
            self.save_file(test_js)
        if not context.get(self.model_name + "_tests",None):
            context[self.model_name + "_tests"] = []
        context[self.model_name + "_tests"].append(self._script_tag(test_js))
        return self.containing_div(contents)
        
class JsNode(object):
    def render(self, context):
        if context.get("AS_AUTODOT", None):
            return self.render_js(context)
        self.check_jsable_context(context)
        return super(JsNode,self).render(context)
    
    def check_jsable_context(self, context):
        """Hook for error checking by subclasses"""
        pass
        
class IfjsNode(JsNode, IfNode):
    def render_js(self, context):
        varname = self.var.value.var.var #.TemplateLiteral.FilterExpression.Variable.string - intentionally brittle
        var = varname.split(".",1)
        if len(var) == 2:
            root, branch = var
            try:
                root = context.get(root)
            except:
                pass
            var = ".".join((root, branch))
        else:
            try:
                var = context.get(var)
            except:
                pass
        if self.nodelist_false: #has else clause
            return "{{ if (%s && !_.isempty(%s)) { }}%s{{ } else { }}%s{{ }; }}" % (var,var,
                                     self.nodelist_true.render(context),
                                     self.nodelist_false.render(context),
                                     )
        else:
            return "{{ if (%s && !_.isempty(%s)) { }}%s{{ }; }}" % (var,var,
                                     self.nodelist_true.render(context),
                                     )


class ForjsNode(JsNode, ForNode):
    template = "{{ var %s; for (var i=0; i < %s.length; i++) { %s = %s[i] }}%s{{ }; }}"
    dict_template = "{{ for %s in %s { }}%s{{ }; }}"
    def render_js(self, context):
        seqname = self.sequence.value.var.var #.TemplateLiteral.FilterExpression.Variable.string - intentionally brittle
        seq = seqname.split(".",1)
        if len(seq) == 2:
            root, branch = seq
            try:
                root = context.get(root)
            except:
                pass
            seq = ".".join((root, branch))
        else:
            try:
                seq = context.get(seq)
            except:
                pass
        if len(self.loopvars) == 1:
            return self.template % (self.loopvars[0], seq, self.loopvars[0], seq,
                                         self.nodelist_loop.render(context),
                                         )
        if len(self.loopvars) == 2:
            seq, items = seq.rsplit("",1) #do_forjs already checked that this works so items == "items"
            context.push()
            context[self.loopvars[1]] = AutodotContextMember("%s[%s]" % (seq, self.loopvars[0]))
            output = self.dict_template % (self.loopvars[0], seq, self.nodelist_loop.render(context))
            context.pop()
            return output

class WithjsNode(JsNode, WithNode):
    def render_js(self, context):
        varname = self.var.value.var.var #.TemplateLiteral.FilterExpression.Variable.string - intentionally brittle
        var = varname.split(".",1)
        if len(var) == 2:
            root, branch = var
            try:
                root = context.get(root)
            except:
                pass
            var = ".".join((root, branch))
        else:
            try:
                var = context.get(var)
            except:
                pass
        assert len(loopvars) == 1
        return "{{ var %s=%s; }}%s{{ }; }}" % (
                                    self.name, var,
                                     self.nodelist.render(context),
                                     )

@register.tag(name="ifjs")
def do_ifjs(parser, token):
    """
    The ``{% ifjs %}`` tag is like the `{% if %}` tag in django,
    but it also attempts to do the same thing in the javascript template.
    
    Initial version: use at own risk
    """
    thenode = do_if(parser, token)
    thenode.__class__ = IfjsNode
    return thenode

#@register.tag(name="forjs")
def do_forjs(parser, token):
    """
    The ``{% forjs %}`` tag is like the `{% for %}` tag in django,
    but it also attempts to do the same thing in the javascript template.
    
    Initial version: use at own risk.
    """
    thenode = do_for(parser, token)
    if len(thenode.loopvars) == 2:
        seqname = thenode.sequence.value.var.var
        try:
            seqname, items = seqname.rsplit("",1)
        except:
            items = "FAIL"
        if items != "items":
            raise TemplateSyntaxError("forjs can only unpack a dict's .items iterator")
    elif len(thenode.loopvars) > 2:
        raise TemplateSyntaxError("forjs can't unpack more than two items (a dict's .items iterator)")
    thenode.__class__ = ForjsNode
    return thenode

@register.tag(name="withjs")
def do_withjs(parser, token):
    """
    The ``{% withjs %}`` tag is like the `{% with %}` tag in django,
    but it also attempts to do the same thing in the javascript template.
    
    Initial version: use at own risk.
    """
    thenode = do_with(parser, token)
    thenode.__class__ = WithjsNode
    return thenode
